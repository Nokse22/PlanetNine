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

from ..widgets.geo_json_map import GeoJsonMap

from ..interfaces.disconnectable import IDisconnectable
from ..interfaces.language import ILanguage
from ..interfaces.saveable import ISaveable
from ..interfaces.cursor import ICursor
from ..interfaces.style_update import IStyleUpdate
from ..interfaces.searchable import ISearchable

import os
import asyncio


@Gtk.Template(
    resource_path='/io/github/nokse22/PlanetNine/gtk/geo_json_page.ui')
class GeoJsonPage(
        Panel.Widget, IDisconnectable, ILanguage, ISaveable, ICursor,
        IStyleUpdate, ISearchable):
    __gtype_name__ = 'GeoJsonPage'

    path = GObject.Property(type=str, default="")

    source_view = Gtk.Template.Child()
    buffer = Gtk.Template.Child()
    geo_json_bin = Gtk.Template.Child()
    stack = Gtk.Template.Child()

    def __init__(self, _file_path=None, **kwargs):
        super().__init__(**kwargs)
        ICursor.__init__(self)
        IStyleUpdate.__init__(self)
        ISaveable.__init__(self)
        ILanguage.__init__(self)
        ISearchable.__init__(self)
        IDisconnectable.__init__(self)

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

        # LOAD File

        asyncio.create_task(self.load_file(_file_path))

        # SETUP the page

        self.is_changed = True

        self.buffer.connect("changed", self.on_json_changed)

        self.stack.connect("notify::visible-child-name", self.on_page_changed)

    def on_json_changed(self, *_args):
        """Sets a flag to store that the json viewer must be updated"""

        self.is_changed = True

    def on_page_changed(self, *_args):
        """When the view switches to the json viewer, updates the json viewer
        if the buffer content have been changed"""

        if self.is_changed:
            start = self.buffer.get_start_iter()
            end = self.buffer.get_end_iter()
            text = self.buffer.get_text(start, end, True)

            geo_map = GeoJsonMap()
            geo_map.parse(text)

            self.geo_json_bin.set_child(geo_map)

            self.is_changed = False

    #
    #   Implement Disconnectable Interface
    #

    def disconnect(self, *_args):
        """Disconnect all signals"""

        IDisconnectable.disconnect(self)
        IStyleUpdate.disconnect(self)
        ICursor.disconnect(self)
        ISaveable.disconnect(self)

        self.stack.disconnect_by_func(self.on_page_changed)
        self.buffer.disconnect_by_func(self.on_json_changed)

        print(f"Disconnected:  {self}")

    def __del__(self, *_args):
        print(f"DELETING {self}")
