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
from gi.repository import Gdk

from enum import IntEnum

from .markdown_textview import MarkdownTextView

class BlockType(IntEnum):
    CODE = 0
    TEXT = 1

class Block(GObject.GObject):
    __gtype_name__ = 'Block'

    _block_type = None

    _content = ""
    _count = 0
    _output = ""
    _binded = False

    def __init__(self, _block_type):
        super().__init__()

        if isinstance(_block_type, BlockType):
            self._block_type = _block_type
        else:
            raise Exception("has to be BlockType")

    @GObject.Property(type=bool, default=False)
    def binded(self):
        return self._binded

    @binded.setter
    def binded(self, value):
        self._binded = value

    @GObject.Property(type=str)
    def content(self):
        return self._content

    @content.setter
    def content(self, value):
        self._content = value

    @GObject.Property(type=int)
    def count(self):
        return self._count

    @count.setter
    def count(self, value):
        self._count = value

    @GObject.Property(type=str)
    def block_type(self):
        return self._block_type

    @block_type.setter
    def block_type(self, value):
        self._block_type = value

    @GObject.Property(type=str)
    def output(self):
        return self._output

    @output.setter
    def output(self, value=""):
        self._output = value

    def set_content(self, value):
        self._content = value
        self.notify("content")

    def set_count(self, value):
        self._count = value
        self.notify("count")

    def set_output(self, value):
        self._output = value
        self.notify("output")

    def get_output(self):
        return self._output

    def set_binded(self, value):
        self._binded = value

@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/block.ui')
class UIBlock(Gtk.Box):
    __gtype_name__ = 'UIBlock'

    __gsignals__ = {
        'run': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    code_buffer = Gtk.Template.Child()
    output_terminal = Gtk.Template.Child()
    output_scrolled_window = Gtk.Template.Child()
    count_label = Gtk.Template.Child()
    markdown_text_view = Gtk.Template.Child()

    _count = 0

    _output = ""

    block = None

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

        self.output_terminal.set_color_background(Gdk.RGBA(alpha=1))

        self.code_buffer.connect("changed", lambda *args: self.notify("content"))
        self.markdown_text_view.get_buffer().connect("changed", lambda *args: self.notify("content"))

    def set_block(self, block):
        self.block = block

    def get_block(self):
        return self.block

    @GObject.Property(type=str)
    def content(self):
        start = self.code_buffer.get_start_iter()
        end = self.code_buffer.get_end_iter()
        return self.code_buffer.get_text(start, end, True)

    @content.setter
    def content(self, value):
        self.set_content(value)

    def set_content(value):
        self.code_buffer.set_text(value)

        self.notify("content")

    @GObject.Property(type=int)
    def count(self):
        return self._count

    @count.setter
    def count(self, value):
        self.set_count(value)

    def set_count(self, value):
        self._count = value
        self.count_label.set_label(str(self._count))

        self.notify("count")

    @GObject.Property(type=str)
    def output(self):
        return self._output

    @output.setter
    def output(self, value):
        self.set_output(value)

    def set_output(self, value=""):
        self._output = value
        if value == "":
            self.output_scrolled_window.set_visible(False)
            self.output_terminal.reset(True, True)
            return
        self.output_scrolled_window.set_visible(True)
        self.output_terminal.feed([ord(char) for char in value.replace("\n","\r\n")])

        self.notify("output")

    def update_style_scheme(self, *args):
        scheme_name = "Adwaita"
        if Adw.StyleManager.get_default().get_dark():
            scheme_name += "-dark"
        sm = GtkSource.StyleSchemeManager()
        scheme = sm.get_scheme(scheme_name)
        self.code_buffer.set_style_scheme(scheme)
