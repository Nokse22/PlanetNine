# window.py
#
# Copyright 2024 Nokse
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GObject, WebKit
from gi.repository import GtkSource
from gi.repository import Gdk, GdkPixbuf

import hashlib
import base64
import os
import sys

from .markdown_textview import MarkdownTextView
from .terminal_textview import TerminalTextView
from .output import OutputType, DataType


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/console_cell.ui')
class ConsoleCell(Gtk.Box):
    __gtype_name__ = 'ConsoleCell'

    source_view = Gtk.Template.Child()
    code_buffer = Gtk.Template.Child()
    output_scrolled_window = Gtk.Template.Child()
    count_label = Gtk.Template.Child()
    output_box = Gtk.Template.Child()
    right_click_menu = Gtk.Template.Child()
    click_gesture = Gtk.Template.Child()

    cache_dir = os.environ["XDG_CACHE_HOME"]

    def __init__(self, content):
        super().__init__()

        self.code_buffer.set_text(content)

        self.connect("unrealize", self.__on_unrealized)

        self.code_buffer.set_highlight_syntax(True)

        self.style_manager = Adw.StyleManager.get_default()
        self.style_manager.connect("notify::dark", self.update_style_scheme)
        self.update_style_scheme()

    def add_output(self, output):
        self.output_scrolled_window.set_visible(True)

        match output.output_type:
            case OutputType.STREAM:
                self.add_output_text(output.text)

            case OutputType.DISPLAY_DATA:
                match output.data_type:
                    case DataType.TEXT:
                        self.add_output_text(output.data_content)
                    case DataType.IMAGE:
                        self.add_output_image(output.data_content)
                    case DataType.HTML:
                        self.add_output_html(output.data_content)
                    case DataType.MARKDOWN:
                        self.add_output_markdown(output.data_content)

            case OutputType.EXECUTE_RESULT:
                print(output.data_content)

            case OutputType.ERROR:
                self.add_output_text(output.traceback)

    def reset_output(self):
        self.output_scrolled_window.set_visible(False)

        child = self.output_box.get_first_child()
        while child:
            self.output_box.remove(child)
            child = self.output_box.get_first_child()

    def add_output_markdown(self, markdown_string):
        child = MarkdownTextView()
        child.set_editable(False)
        self.output_box.append(child)
        child.set_text(markdown_string)

    def add_output_html(self, html_string):
        webview = WebKit.WebView()
        webview.load_html(html_string, None)
        self.output_box.append(webview)

    def add_output_image(self, image_content):
        image_data = base64.b64decode(image_content)
        sha256_hash = hashlib.sha256(image_data).hexdigest()

        image_path = os.path.join(self.cache_dir, f"{sha256_hash}.png")
        with open(image_path, 'wb') as f:
            f.write(image_data)

        pixbuf = GdkPixbuf.Pixbuf.new_from_file(image_path)
        image = Gtk.Picture.new_for_pixbuf(pixbuf)
        image.set_size_request(-1, pixbuf.get_height())

        self.output_scrolled_window.set_visible(True)
        self.output_box.append(image)

    def add_output_text(self, text):
        child = self.output_box.get_last_child()
        if not isinstance(child, TerminalTextView):
            child = TerminalTextView()
            self.output_box.append(child)
        child.insert_with_escapes(text)

    def update_style_scheme(self, *args):
        scheme_name = "Adwaita"
        if Adw.StyleManager.get_default().get_dark():
            scheme_name += "-dark"
        sm = GtkSource.StyleSchemeManager()
        scheme = sm.get_scheme(scheme_name)
        self.code_buffer.set_style_scheme(scheme)

    def set_language(self, lang_name):
        lm = GtkSource.LanguageManager()
        lang = lm.get_language(lang_name)
        self.code_buffer.set_language(lang)

    def __on_unrealized(self, *args):
        self.style_manager.disconnect_by_func(self.update_style_scheme)

        self.disconnect_by_func(self.__on_unrealized)

        print("unrealize: ", sys.getrefcount(self))

    def __del__(self, *args):
        print(f"DELETING {self}")
