# style_manager.py
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

from gi.repository import GObject, Gio

import xml.etree.ElementTree as ET
import configparser


class Palette(GObject.GObject):
    __gtype_name__ = "Palette"

    config_parser = configparser.ConfigParser()

    name = GObject.Property(type=str)
    display_name = GObject.Property(type=str)
    use_system_accent = GObject.Property(type=bool, default=False)

    # Names of GtkSource styles
    dark_source_name = GObject.Property(type=str)
    light_source_name = GObject.Property(type=str)

    light_palette = {}
    dark_palette = {}

    def __init__(self, palette):
        super().__init__()

        self.name = palette.attrib
        self.display_name = palette.attrib

        self.dark_source_name = palette.find('source').get('light')
        self.light_source_name = palette.find('source').get('dark')

        color_file = palette.find('colors').get('name')
        palettes_data = Gio.resources_lookup_data(
            f"/io/github/nokse22/PlanetNine/styles/palettes/{color_file}.palette",
            Gio.ResourceLookupFlags.NONE).get_data().decode('utf-8')

        self.config_parser.read_string(palettes_data)

        self.light_palette = {}
        self.dark_palette = {}

        self.use_system_accent = self.config_parser.getboolean(
            "Palette", "UseSystemAccent", fallback=False)

        if self.config_parser.has_section("Light"):
            self.light_palette = self._load_palette("Light")

        if self.config_parser.has_section("Dark"):
            self.dark_palette = self._load_palette("Dark")

    def _load_palette(self, section):
        palette = {}
        for key, value in self.config_parser.items(section):
            palette[key] = value

        # palette["titlebarbackground"] = palette.get(
        #     "titlebarbackground", palette.get("Background"))
        # palette["titlebarforeground"] = palette.get(
        #     "titlebarforeground", palette.get("Foreground"))

        return palette


class StyleManager(GObject.GObject):
    __gtype_name__ = "StyleManager"

    def __init__(self):
        super().__init__()

        self._palettes = Gio.ListStore.new(Palette)

        self._selected = 9

        palettes_data = Gio.resources_lookup_data(
            "/io/github/nokse22/PlanetNine/styles/palettes/palettes.xml",
            Gio.ResourceLookupFlags.NONE).get_data().decode('utf-8')

        palettes = ET.fromstring(palettes_data)

        for palette in palettes:
            self._palettes.append(Palette(palette))

        print(self._palettes)

    @GObject.Property(type=int)
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, _selected):
        print(_selected)
        self._selected = _selected
        self.notify("selected")

    @GObject.Property(type=GObject.GObject)
    def palette(self):
        return self._palettes[self._selected]

    @GObject.Property(type=GObject.GObject)
    def palettes(self):
        return self._palettes

    def get_avalaible_palettes(self):
        return self._palettes
