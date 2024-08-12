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
from gi.repository import GObject
from gi.repository import GtkSource
from gi.repository import Gdk, GdkPixbuf

from enum import IntEnum

from .markdown_textview import MarkdownTextView

class BlockType(IntEnum):
    CODE = 0
    TEXT = 1

class Block(GObject.GObject):
    __gtype_name__ = 'Block'

    _block_type = None

    _block = None

    _images = []

    def __init__(self, _block_type):
        super().__init__()

        if isinstance(_block_type, BlockType):
            self._block_type = _block_type
        else:
            raise Exception("has to be BlockType")

    @GObject.Property(type=int)
    def block_type(self):
        return self._block_type

    @GObject.Property(type=str)
    def content(self):
        return self._block.get_content()

    def set_block(self, block):
        self._block = block
        self._block.set_block_type(self._block_type)

    def get_block(self):
        return self._block

    def set_content(value):
        self._block.set_content(value)

    def set_count(self, value):
        self._block.set_count(value)

    def set_output(self, value):
        self._block.set_output(value)

    def add_image(self, image_path):
        self._images.append(image_path)
        self._block.add_image(image_path)

    def reset_output(self):
        self._block.reset_output()
        self._images=[]

@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/block.ui')
class UIBlock(Gtk.Box):
    __gtype_name__ = 'UIBlock'

    __gsignals__ = {
        'run': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    code_buffer = Gtk.Template.Child()
    output_scrolled_window = Gtk.Template.Child()
    count_label = Gtk.Template.Child()
    markdown_text_view = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    output_box = Gtk.Template.Child()

    _count = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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

        # self.output_terminal.set_color_background(Gdk.RGBA(alpha=1))

        self.text_buffer = self.markdown_text_view.get_buffer()

    def set_content(self, value):
        if self.block_type == BlockType.TEXT:
            self.text_buffer.set_text(value)

        elif self.block_type == BlockType.CODE:
            self.code_buffer.set_text(value)

    def get_content(self):
        if self.block_type == BlockType.TEXT:
            start = self.text_buffer.get_start_iter()
            end = self.text_buffer.get_end_iter()
            return self.text_buffer.get_text(start, end, True)

        elif self.block_type == BlockType.CODE:
            start = self.code_buffer.get_start_iter()
            end = self.code_buffer.get_end_iter()
            return self.code_buffer.get_text(start, end, True)

    def set_count(self, value):
        self.count_label.set_label(str(value))

    def set_output(self, value=""):
        if value == "":
            self.output_scrolled_window.set_visible(False)
            # self.output_terminal.reset(True, True)
            return
        self.output_scrolled_window.set_visible(True)
        child = self.output_box.get_last_child()
        if isinstance(child, Gtk.TextView):
            child.get_buffer().set_text(value)
        else:
            child = self.get_new_output_text_view()
            self.output_box.append(child)

            child.get_buffer().set_text(value)

    def set_block_type(self, block_type):
        self.block_type = block_type
        if block_type == BlockType.TEXT:
            self.stack.set_visible_child_name("text")
            self.count_label.set_visible(False)
        elif block_type == BlockType.CODE:
            self.stack.set_visible_child_name("code")
            self.count_label.set_visible(True)

    def reset_output(self):
        self.output_scrolled_window.set_visible(False)

        child = self.output_box.get_first_child()
        while child:
            self.output_box.remove(child)
            child = self.output_box.get_first_child()

    def add_image(self, image_path):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(image_path)
        image_height = pixbuf.get_height()

        image = Gtk.Picture()

        image.set_filename(image_path)
        image.set_size_request(-1, image_height)

        self.output_scrolled_window.set_visible(True)
        self.output_box.append(image)

    def update_style_scheme(self, *args):
        scheme_name = "Adwaita"
        if Adw.StyleManager.get_default().get_dark():
            scheme_name += "-dark"
        sm = GtkSource.StyleSchemeManager()
        scheme = sm.get_scheme(scheme_name)
        self.code_buffer.set_style_scheme(scheme)

    @Gtk.Template.Callback("on_drag_source_prepare")
    def on_drag_source_prepare(self, source, x, y):
        global drag_x, drag_y
        drag_x = x
        drag_y = y

        box = Gtk.Box()

        value = GObject.Value()
        value.init(Gtk.Box)
        value.set_object(box)

        return Gdk.ContentProvider.new_for_value(value)

    @Gtk.Template.Callback("on_drag_source_begin")
    def on_drag_source_begin(self, source, drag):
        print("begin")
        drag_widget = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL
        )

        drag_widget.append(
            Gtk.Label(
                label=self.count_label.get_label(),
                css_classes=["title-4", "dim-label"]
            )
        )

        drag_widget.append(
            Gtk.Frame(
                label="something...",
            )
        )

        icon = Gtk.DragIcon.get_for_drag(drag)
        icon.set_child(drag_widget)

        drag.set_hotspot(drag_x, drag_y)

    @Gtk.Template.Callback("on_drag_source_end")
    def on_drag_source_end(self, source, drag, delete_data):
        print(source)

    def get_new_output_text_view(self):
        text_view = Gtk.TextView(
            css_classes=["output-text-view"],
            editable=False,
            monospace=True,
            wrap_mode=Gtk.WrapMode.CHAR,
            input_purpose=Gtk.InputPurpose.TERMINAL,
            cursor_visible=False
        )
        return text_view
