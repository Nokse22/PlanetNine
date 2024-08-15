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
from gi.repository import GLib
from gi.repository import Gio
from gi.repository import GObject, WebKit
from gi.repository import GtkSource, GLib
from gi.repository import Gdk, GdkPixbuf, Pango

from pprint import pprint
from enum import IntEnum

import hashlib
import base64
import os
import copy

from .markdown_textview import MarkdownTextView
from .terminal_textview import TerminalTextView
from .cell import Cell, CellType
from .output import Output, OutputType, DataType

@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/cell.ui')
class CellUI(Gtk.Box):
    __gtype_name__ = 'CellUI'

    __gsignals__ = {
        'request-delete': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    code_buffer = Gtk.Template.Child()
    output_scrolled_window = Gtk.Template.Child()
    count_label = Gtk.Template.Child()
    markdown_text_view = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    output_box = Gtk.Template.Child()
    right_click_menu = Gtk.Template.Child()
    drag_source = Gtk.Template.Child()

    cell = None

    _cell_type = CellType.CODE

    cache_dir = os.environ["XDG_CACHE_HOME"]

    def __init__(self, cell):
        super().__init__()

        self.cell = cell

        lm = GtkSource.LanguageManager()
        lang = lm.get_language("python")
        self.code_buffer.set_language(lang)
        self.code_buffer.set_highlight_syntax(True)

        sm = GtkSource.StyleSchemeManager()
        scheme = sm.get_scheme("Adwaita-dark")
        self.code_buffer.set_style_scheme(scheme)

        style_manager = Adw.StyleManager.get_default()
        style_manager.connect("notify::dark", self.update_style_scheme)
        self.update_style_scheme()

        self.text_buffer = self.markdown_text_view.get_buffer()

        self.drag_source.set_actions(Gdk.DragAction.MOVE)

        self.cell_type = self.cell.cell_type
        self.set_content(self.cell.source)
        for output in self.cell.outputs:
            self.add_output(output)
        self.set_execution_count(self.cell.execution_count)

        self.action_group = Gio.SimpleActionGroup()

        self.create_action('delete', lambda *args: self.emit("request-delete"))
        self.create_action('change_type', self.on_change_type)
        self.create_action('toggle_output_expand', self.on_toggle_output_expand)

        self.insert_action_group("cell", self.action_group)

        self.bind_property("source", self.cell, "source")
        self.bind_property("cell_type", self.cell, "cell_type")
        self.cell.connect("notify::outputs", lambda *args: print("outputs changed"))
        self.cell.connect("execution-count-changed", self.on_execution_count_changed)
        self.cell.connect("output-added", self.on_add_output)
        self.cell.connect("output-reset", self.on_reset_output)

    @GObject.Property(type=str, default="")
    def source(self):
        return self.get_content()

    @source.setter
    def source(self, value):
        self.set_content(value)

    @GObject.Property(type=int, default=0)
    def cell_type(self):
        return self._cell_type

    @cell_type.setter
    def cell_type(self, value):
        content = self.get_content()

        if value == CellType.TEXT:
            self.stack.set_visible_child_name("text")
            self.count_label.set_visible(False)
            self.output_scrolled_window.set_visible(False)
        elif value == CellType.CODE:
            self.stack.set_visible_child_name("code")
            self.count_label.set_visible(True)

        self._cell_type = value

        self.set_content(content)

    def set_content(self, value):
        if self._cell_type == CellType.TEXT:
            self.text_buffer.set_text(value)

        elif self._cell_type == CellType.CODE:
            self.code_buffer.set_text(value)

    def get_content(self):
        if self.cell.cell_type == CellType.TEXT:
            start = self.text_buffer.get_start_iter()
            end = self.text_buffer.get_end_iter()
            return self.text_buffer.get_text(start, end, True)

        elif self.cell.cell_type == CellType.CODE:
            start = self.code_buffer.get_start_iter()
            end = self.code_buffer.get_end_iter()
            return self.code_buffer.get_text(start, end, True)

    def set_execution_count(self, value):
        self.count_label.set_label(str(value or 0))

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

    @Gtk.Template.Callback("on_click_released")
    def on_click_released(self, gesture, n_press, click_x, click_y):
        if n_press != 1:
            return

        widget = gesture.get_widget()
        popover = Gtk.PopoverMenu(
            menu_model=self.right_click_menu,
            has_arrow=False,
            halign=1,
        )
        position = Gdk.Rectangle()
        position.x = click_x
        position.y = click_y
        popover.set_parent(widget)
        popover.set_pointing_to(position)
        popover.popup()

        return True

    def on_toggle_output_expand(self, *args):
        _, vscrollbar_policy = self.output_scrolled_window.get_policy()

        if vscrollbar_policy == Gtk.PolicyType.AUTOMATIC:
            self.output_scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        else:
            self.output_scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    def on_change_type(self, *args):
        if self.cell_type == CellType.TEXT:
            self.cell_type = CellType.CODE
        elif self.cell_type == CellType.CODE:
            self.cell_type = CellType.TEXT

    def create_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.action_group.add_action(action)
        return action

    @Gtk.Template.Callback("on_source_changed")
    def on_source_changed(self, buffer, *args):
        self.notify("source")

    @Gtk.Template.Callback("on_drag_source_prepare")
    def on_drag_source_prepare(self, source, x, y):
        value = GObject.Value()
        value.init(Cell)
        value.set_object(self.cell.copy())

        return Gdk.ContentProvider.new_for_value(value)

    @Gtk.Template.Callback("on_drag_source_begin")
    def on_drag_source_begin(self, source, drag):
        builder = Gtk.Builder.new_from_resource('/io/github/nokse22/PlanetNine/gtk/cell_drag.ui')
        drag_widget = builder.get_object('drag_widget')

        builder.get_object('count').set_label(self.count_label.get_label())
        builder.get_object('code').set_label(self.get_content()[:20] + '...')

        icon = Gtk.DragIcon.get_for_drag(drag)
        icon.set_child(drag_widget)

        drag.set_hotspot(0, 0)

    @Gtk.Template.Callback("on_drag_source_end")
    def on_drag_source_end(self, source, drag, delete_data):
        print("how do i delete", source, drag, delete_data)
        self.emit("request-delete")

    def on_reset_output(self, cell):
        self.reset_output()

    def on_execution_count_changed(self, cell, value):
        self.set_execution_count(value)

    def on_add_output(self, cell, output):
        self.add_output(output)
