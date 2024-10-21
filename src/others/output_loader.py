# output_loader.py
#
# Copyright 2024 Nokse22
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import GObject, Gtk, GLib, GdkPixbuf, Gio

from ..widgets.json_viewer import JsonViewer
from ..widgets.terminal_textview import TerminalTextView
from ..widgets. markdown_textview import MarkdownTextView

from ..models.output import OutputType, DataType

from gettext import gettext as _

import hashlib
import base64
import os
import random
import re
import asyncio


class OutputLoader(GObject.GObject):
    __gtype_name__ = "OutputLoader"

    cache_dir = os.environ["XDG_CACHE_HOME"]

    images_path = os.path.join(cache_dir, "g_images")
    html_path = os.path.join(cache_dir, "g_html")

    def __init__(self, _output_box):
        super().__init__()

        self.output_box = _output_box

    def add_output(self, output):
        match output.output_type:
            case OutputType.STREAM:
                self.add_output_text(output.text)

            case OutputType.DISPLAY_DATA | OutputType.EXECUTE_RESULT:
                match output.data_type:
                    case DataType.TEXT:
                        self.add_output_text(output.data_content)
                    case DataType.IMAGE_PNG:
                        asyncio.create_task(
                            self.add_output_png_image(output.data_content))
                    case DataType.IMAGE_SVG:
                        asyncio.create_task(
                            self.add_output_svg_image(output.data_content))
                    case DataType.HTML:
                        asyncio.create_task(
                            self.add_output_html(
                                output.data_content,
                                output.plain_content))
                    case DataType.MARKDOWN:
                        self.add_output_markdown(output.data_content)
                    case DataType.JSON:
                        viewer = JsonViewer()
                        viewer.add_css_class("output")
                        viewer.parse_json_string(output.data_content)
                        self.output_box.append(viewer)

            case OutputType.ERROR:
                self.add_output_text(output.traceback)

    def add_output_markdown(self, markdown_string):
        child = MarkdownTextView()
        child.set_editable(False)
        self.output_box.append(child)
        child.set_text(markdown_string)

    async def add_output_html(self, html_string, what):
        sha256_hash = random.randint(0, 1000000)
        html_page_path = os.path.join(self.html_path, f"{sha256_hash}.html")

        await self.save_file_async(html_string, html_page_path)

        match = re.search(r'\.(\w+)(?:\s|\>)', what)
        if match:
            html_name = match.group(1)
        else:
            html_name = _("HTML")

        box = Gtk.Box(
            spacing=12,
            margin_top=6,
            margin_bottom=6,
            halign=Gtk.Align.CENTER)
        button = Gtk.Button(
            css_classes=["html-button"],
            action_name="win.new-browser-page",
            action_target=GLib.Variant('s', "file://" + html_page_path))
        box.append(Gtk.Image(icon_name="earth-symbolic"))
        box.append(Gtk.Label(label="Open {} in Browser".format(html_name)))
        box.append(Gtk.Image(icon_name="right-symbolic"))
        button.set_child(box)
        self.output_box.append(button)

    async def add_output_png_image(self, image_content):
        image_data = base64.b64decode(image_content)
        sha256_hash = hashlib.sha256(image_data).hexdigest()

        image_path = os.path.join(self.images_path, f"{sha256_hash}.png")
        await self.save_file_async(image_data, image_path)

        self.add_output_image(image_path)

    async def add_output_svg_image(self, svg_string):
        sha256_hash = await self.compute_hash(svg_string)

        svg_path = os.path.join(self.images_path, f"{sha256_hash}.svg")

        await self.save_file_async(svg_string, svg_path)

        self.add_output_image(svg_path)

    def add_output_image(self, image_path):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(image_path)
        picture = Gtk.Picture.new_for_pixbuf(pixbuf)
        if pixbuf.get_width() > 800:
            picture.set_size_request(
                -1, pixbuf.get_height() * (700 / pixbuf.get_width()))
        else:
            picture.set_size_request(
                -1, pixbuf.get_height())

        self.output_box.append(picture)

    def add_output_text(self, text):
        child = self.output_box.get_last_child()
        if not isinstance(child, TerminalTextView):
            child = TerminalTextView()
            self.output_box.append(child)
        child.insert_with_escapes(text)

    async def save_file_async(self, content: bytes, file_path: str):
        file = Gio.File.new_for_path(file_path)
        output_stream = await file.replace_async(
            None, False, Gio.FileCreateFlags.NONE, GLib.PRIORITY_DEFAULT, None
        )
        if isinstance(content, str):
            content = content.encode('utf-8')
        await output_stream.write_bytes_async(
            GLib.Bytes.new(content),
            io_priority=GLib.PRIORITY_DEFAULT,
            cancellable=None
        )
        await output_stream.close_async(
            io_priority=GLib.PRIORITY_DEFAULT,
            cancellable=None
        )

    async def compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
