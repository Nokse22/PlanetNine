# json_viewer_page.py
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

from gi.repository import Gtk, Adw, Gio, GObject
from gi.repository import Panel, GtkSource
from gi.repository import Spelling

from ..others.save_delegate import GenericSaveDelegate
from ..others.style_manager import StyleManager

from ..widgets.json_viewer import JsonViewer

from ..interfaces.disconnectable import IDisconnectable

import os


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/json_viewer_page.ui')
class JsonViewerPage(Panel.Widget, IDisconnectable):
    __gtype_name__ = 'JsonViewerPage'

    path = GObject.Property(type=str, default="")

    source_view = Gtk.Template.Child()
    buffer = Gtk.Template.Child()
    json_viewer_bin = Gtk.Template.Child()
    stack = Gtk.Template.Child()

    def __init__(self, _path=None):
        super().__init__()

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

        # SET THE LANGUAGE STYLE SCHEME

        lm = GtkSource.LanguageManager()
        lang = lm.get_language("json")
        self.buffer.set_language(lang)
        self.buffer.set_highlight_syntax(True)

        self.style_manager = StyleManager()
        self.style_manager.connect("style-changed", self.update_style_scheme)
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

        # SETUP the page

        self.is_changed = True

        self.buffer.connect("changed", self.on_json_changed)

        self.stack.connect("notify::visible-child-name", self.on_page_changed)

    def on_json_changed(self, *args):
        self.is_changed = True
        self.set_modified(True)

    def on_page_changed(self, *args):
        if self.is_changed:
            start = self.buffer.get_start_iter()
            end = self.buffer.get_end_iter()
            text = self.buffer.get_text(start, end, True)
            viewer = JsonViewer()
            viewer.parse_json_string(text)
            self.json_viewer_bin.set_child(viewer)

            self.is_changed = False

    def update_style_scheme(self, *args):
        scheme = self.style_manager.get_current_scheme()
        self.buffer.set_style_scheme(scheme)

    #
    #   Implement Saveable Page Interface
    #

    def set_path(self, _path):
        self.path = _path
        self.set_title(
            os.path.basename(self.path) if self.path else "Untitled.json")

    def get_path(self):
        return self.path

    def get_content(self):
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        return self.buffer.get_text(start, end, True)

    #
    #   Implement Disconnectable Interface
    #

    def disconnect(self, *args):
        self.style_manager.disconnect_by_func(self.update_style_scheme)
        self.stack.disconnect_by_func(self.on_page_changed)
        self.buffer.disconnect_by_func(self.on_json_changed)

        self.save_delegate.disconnect_all()

        print(f"closing: {self}")

    def __del__(self, *args):
        print(f"DELETING {self}")
