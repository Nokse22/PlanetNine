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

from ..interfaces.saveable import ISaveable
from ..interfaces.disconnectable import IDisconnectable
from ..interfaces.cursor import ICursor
from ..interfaces.language import ILanguage

import os

GObject.type_register(GtkSource.Map)
GObject.type_register(GtkSource.VimIMContext)


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/text_page.ui')
class TextPage(Panel.Widget, ISaveable, IDisconnectable, ICursor, ILanguage):
    __gtype_name__ = 'TextPage'

    path = GObject.Property(type=str, default="")

    source_view = Gtk.Template.Child()
    buffer = Gtk.Template.Child()

    def __init__(self, _path=None):
        super().__init__()

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

        # SET THE LANGUAGE

        self.language = ""

        self.language_manager = GtkSource.LanguageManager()

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

        self.buffer.connect(
            "changed", self.on_text_changed)
        self.buffer.connect(
            "notify::cursor-position", self.on_cursor_position_changed)

    def set_path(self, _path):
        self.path = _path
        self.set_title(
            os.path.basename(self.path) if self.path else "Untitled")

    def get_path(self):
        return self.path

    def get_content(self):
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        return self.buffer.get_text(start, end, True)

    #
    #
    #

    def on_text_changed(self, *args):
        self.set_modified(True)

    def update_style_scheme(self, *args):
        scheme_name = "Adwaita"
        if Adw.StyleManager.get_default().get_dark():
            scheme_name += "-dark"
        sm = GtkSource.StyleSchemeManager()
        scheme = sm.get_scheme(scheme_name)
        self.buffer.set_style_scheme(scheme)

    #
    #   Implement Language Interface
    #

    def set_language(self, _language):
        self.language = _language
        lang = self.language_manager.get_language(self.language)
        self.code_buffer.set_language(lang)
        self.code_buffer.set_highlight_syntax(True)

    #
    #   Implement Cursor Interface
    #

    def on_cursor_position_changed(self, *args):
        self.emit("cursor-moved", self.buffer, 0)

    #
    #   Implement Disconnectable Interface
    #

    def disconnect(self, *args):
        self.style_manager.disconnect_by_func(self.update_style_scheme)
        self.buffer.disconnect_by_func(self.on_text_changed)
        self.buffer.disconnect_by_func(self.on_cursor_position_changed)

        self.save_delegate.disconnect_all()

        print(f"Unrealize: {self}")

    def __del__(self, *args):
        print(f"DELETING {self}")
