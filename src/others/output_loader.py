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

from gi.repository import GObject, Gtk, GLib, GdkPixbuf

from ..widgets.json_viewer import JsonViewer
from ..widgets.terminal_textview import TerminalTextView
from ..widgets. markdown_textview import MarkdownTextView

from ..models.output import OutputType, DataType

import hashlib
import base64
import os
import random


class OutputLoader(GObject.GObject):
    __gtype_name__ = "OutputLoader"

    cache_dir = os.environ["XDG_CACHE_HOME"]

    images_path = os.path.join(cache_dir, "g_images")
    html_path = os.path.join(cache_dir, "g_html")

    def __init__(self, _output_box):
        super().__init__()

        self.output_box = _output_box

    def add_output(self, output):
        self.output_box

        match output.output_type:
            case OutputType.STREAM:
                self.add_output_text(output.text)

            case OutputType.DISPLAY_DATA:
                match output.data_type:
                    case DataType.TEXT:
                        self.add_output_text(output.data_content)
                    case DataType.IMAGE_PNG:
                        self.add_output_image(output.data_content)
                    case DataType.HTML:
                        self.add_output_html(output.data_content)
                    case DataType.MARKDOWN:
                        self.add_output_markdown(output.data_content)
                    case DataType.JSON:
                        viewer = JsonViewer()
                        viewer.parse_json_string(output.data_content)
                        self.output_box.append(viewer)

            case OutputType.EXECUTE_RESULT:
                print(output.data_content)

            case OutputType.ERROR:
                self.add_output_text(output.traceback)

    def add_output_markdown(self, markdown_string):
        child = MarkdownTextView()
        child.set_editable(False)
        self.output_box.append(child)
        child.set_text(markdown_string)

    def add_output_html(self, html_string):
        sha256_hash = random.randint(0, 10000)
        html_page_path = os.path.join(self.html_path, f"{sha256_hash}.html")
        with open(html_page_path, 'w') as f:
            f.write(html_string)

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
        box.append(Gtk.Label(label="Open Generated HTML in Browser"))
        box.append(Gtk.Image(icon_name="right-symbolic"))
        button.set_child(box)
        self.output_box.append(button)

    def add_output_image(self, image_content):
        image_data = base64.b64decode(image_content)
        sha256_hash = hashlib.sha256(image_data).hexdigest()

        image_path = os.path.join(self.images_path, f"{sha256_hash}.png")
        with open(image_path, 'wb') as f:
            f.write(image_data)

        pixbuf = GdkPixbuf.Pixbuf.new_from_file(image_path)
        image = Gtk.Picture.new_for_pixbuf(pixbuf)
        if pixbuf.get_width() > 800:
            image.set_size_request(
                -1, pixbuf.get_height() * (700 / pixbuf.get_width()))
        else:
            image.set_size_request(
                -1, pixbuf.get_height())

        self.output_box.append(image)

    def add_output_text(self, text):
        child = self.output_box.get_last_child()
        if not isinstance(child, TerminalTextView):
            child = TerminalTextView()
            self.output_box.append(child)
        child.insert_with_escapes(text)
