# text_page.py
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

from gi.repository import Gtk, GObject, Adw, Gio
from gi.repository import Panel, GtkSource
from gi.repository import Spelling

from ..others.save_delegate import GenericSaveDelegate

from ..utils.converters import get_language_highlight_name

import os

GObject.type_register(GtkSource.Map)
GObject.type_register(GtkSource.VimIMContext)


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/text_page.ui')
class TextPage(Panel.Widget):
    __gtype_name__ = 'TextPage'

    __gsignals__ = {
        'cursor-moved':
            (GObject.SignalFlags.RUN_FIRST, None, (Gtk.TextBuffer, int))
    }

    path = GObject.Property(type=str, default="")

    source_view = Gtk.Template.Child()
    buffer = Gtk.Template.Child()

    def __init__(self, _path=None):
        super().__init__()

        self.connect("unrealize", self.__on_unrealized)

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

        # SET THE LANGUAGE

        # lm = GtkSource.LanguageManager()
        # lang = lm.get_language("python3")
        # self.code_buffer.set_language(lang)
        # self.code_buffer.set_highlight_syntax(True)

        # SET STYLE SCHEME

        self.style_manager = Adw.StyleManager.get_default()
        self.style_manager.connect("notify::dark", self.update_style_scheme)
        self.update_style_scheme()

        # ENABLE SPELL CHECK

        checker = Spelling.Checker.get_default()
        adapter = Spelling.TextBufferAdapter.new(self.buffer, checker)
        extra_menu = adapter.get_menu_model()

        self.source_view.set_extra_menu(extra_menu)
        self.source_view.insert_action_group('spelling', adapter)

        adapter.set_enabled(True)

        # ADD SAVE DELEGATE

        self.save_delegate = GenericSaveDelegate(self)
        self.set_save_delegate(self.save_delegate)

        if not _path:
            self.save_delegate.set_is_draft(True)

        # LOAD File

        if _path:
            with open(_path, 'r') as file:
                content = file.read()

            self.buffer.set_text(content)

            self.set_path(_path)

        # CONNECT

        self.buffer.connect("changed", self.on_text_changed)
        self.buffer.connect(
            "notify::cursor-position", self.on_cursor_position_changed)

    def on_text_changed(self, *args):
        self.set_modified(True)

    def on_cursor_position_changed(self, *args):
        self.emit("cursor-moved", self.buffer, 0)

    def set_path(self, _path):
        self.path = _path
        self.set_title(
            os.path.basename(self.path) if self.path else "Untitled")

    def get_content(self):
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        return self.buffer.get_text(start, end, True)

    def update_style_scheme(self, *args):
        scheme_name = "Adwaita"
        if Adw.StyleManager.get_default().get_dark():
            scheme_name += "-dark"
        sm = GtkSource.StyleSchemeManager()
        scheme = sm.get_scheme(scheme_name)
        self.buffer.set_style_scheme(scheme)

    def __on_unrealized(self, *args):
        self.disconnect_by_func(self.__on_unrealized)

        self.style_manager.disconnect_by_func(self.update_style_scheme)
        self.buffer.disconnect_by_func(self.on_text_changed)

        print(f"Unrealize: {self}")

    def __del__(self, *args):
        print(f"DELETING {self}")
