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
from ..interfaces.language import ILanguage
from ..interfaces.saveable import ISaveable
from ..interfaces.cursor import ICursor
from ..interfaces.style_update import IStyleUpdate

import os


@Gtk.Template(
    resource_path='/io/github/nokse22/PlanetNine/gtk/json_viewer_page.ui')
class JsonViewerPage(
        Panel.Widget, IDisconnectable, ILanguage, ISaveable, ICursor,
        IStyleUpdate):
    __gtype_name__ = 'JsonViewerPage'

    path = GObject.Property(type=str, default="")

    source_view = Gtk.Template.Child()
    buffer = Gtk.Template.Child()
    json_viewer_bin = Gtk.Template.Child()
    stack = Gtk.Template.Child()

    def __init__(self, _path=None, **kwargs):
        super().__init__(**kwargs)
        ICursor.__init__(self, **kwargs)
        IStyleUpdate.__init__(self, **kwargs)
        ISaveable.__init__(self, **kwargs)

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

        # SET THE LANGUAGE and STYLE SCHEME

        self.set_language("json")

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

    def on_page_changed(self, *args):
        if self.is_changed:
            start = self.buffer.get_start_iter()
            end = self.buffer.get_end_iter()
            text = self.buffer.get_text(start, end, True)
            viewer = JsonViewer()
            viewer.parse_json_string(text)
            self.json_viewer_bin.set_child(viewer)

            self.is_changed = False

    #
    #   Implement Disconnectable Interface
    #

    def disconnect(self, *args):
        self.style_manager.disconnect_by_func(self.update_style_scheme)
        self.stack.disconnect_by_func(self.on_page_changed)
        self.buffer.disconnect_by_func(self.on_json_changed)
        self.buffer.disconnect_by_func(self.on_text_changed)
        self.buffer.disconnect_by_func(self.on_cursor_position_changed)

        self.save_delegate.disconnect_all()

        print(f"Disconnected:  {self}")

    def __del__(self, *args):
        print(f"DELETING {self}")
