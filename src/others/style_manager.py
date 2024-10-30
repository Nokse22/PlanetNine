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

from gi.repository import GObject, Gio, Adw, GtkSource, Gtk, Gdk

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

        self.name = palette.attrib["name"]
        self.display_name = palette.attrib

        self.dark_source_name = palette.find("source").get("dark")
        self.light_source_name = palette.find("source").get("light")

        color_file = palette.find("colors").get("name")
        palettes_data = (
            Gio.resources_lookup_data(
                f"/io/github/nokse22/PlanetNine/styles/palettes/{color_file}.palette",
                Gio.ResourceLookupFlags.NONE,
            ) .get_data() .decode("utf-8"))

        self.config_parser.read_string(palettes_data)

        self.light_palette = {}
        self.dark_palette = {}

        self.use_system_accent = self.config_parser.getboolean(
            "Palette", "UseSystemAccent", fallback=False
        )

        if self.config_parser.has_section("Light"):
            self.light_palette = self._load_palette("Light")

        if self.config_parser.has_section("Dark"):
            self.dark_palette = self._load_palette("Dark")

    def _load_palette(self, section):
        palette = {}
        for key, value in self.config_parser.items(section):
            palette[key] = value

        palette["titlebarbackground"] = palette.get(
            "titlebarbackground", palette.get("Background")
        )
        palette["titlebarforeground"] = palette.get(
            "titlebarforeground", palette.get("Foreground")
        )

        return palette


class ThemeSelector(Adw.Bin):
    __gtype_name__ = 'ThemeSelector'

    palette = GObject.Property(type=GObject.GObject)

    scheme_manager = GtkSource.StyleSchemeManager()
    scheme_manager.append_search_path(
        "resource:///io/github/nokse22/PlanetNine/styles/schemes/")

    def __init__(self, _palette):
        super().__init__()

        self.palette = _palette

        self.adw_style_manager = Adw.StyleManager.get_default()
        self.adw_style_manager.connect("notify::dark", self.set_preview_child)

        light_scheme = self.scheme_manager.get_scheme(
            self.palette.light_source_name)
        dark_scheme = self.scheme_manager.get_scheme(
            self.palette.dark_source_name)

        self.light_preview = GtkSource.StyleSchemePreview.new(light_scheme)
        self.dark_preview = GtkSource.StyleSchemePreview.new(dark_scheme)

        self.set_preview_child()

    def set_preview_child(self, *_args):
        if self.adw_style_manager.get_dark():
            self.set_child(self.dark_preview)
        else:
            self.set_child(self.light_preview)


class StyleManager(GObject.GObject):
    __gtype_name__ = "StyleManager"

    __gsignals__ = {
        "style-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    _instance = None
    _initialized = False

    _palettes = Gio.ListStore.new(Palette)

    _selected = "Adwaita"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StyleManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        if self._initialized:
            return

        self.adw_style_manager = Adw.StyleManager.get_default()
        self.adw_style_manager.connect("notify::dark", self.on_style_changed)
        self.adw_style_manager.connect("notify::accent-color", self.on_style_changed)

        self.style_scheme_manager = GtkSource.StyleSchemeManager()
        self.style_scheme_manager.append_search_path(
            "resource:///io/github/nokse22/PlanetNine/styles/schemes/"
        )

        palettes_data = (
            Gio.resources_lookup_data(
                "/io/github/nokse22/PlanetNine/styles/palettes.xml",
                Gio.ResourceLookupFlags.NONE,
            )
            .get_data()
            .decode("utf-8")
        )

        palettes = ET.fromstring(palettes_data)

        for palette in palettes:
            self._palettes.append(Palette(palette))

        StyleManager._initialized = True

        self.css_provider = Gtk.CssProvider()

    @GObject.Property(type=str, default="Adwaita")
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, _selected):
        if _selected != self._selected:
            self._selected = _selected
            self.notify("selected")
            self.emit("style-changed")
            self.update_style_scheme()

    @GObject.Property(type=GObject.GObject)
    def palette(self):
        for palette in self.palettes:
            print(palette.name)
            if palette.name == self.selected:
                return palette

    @palette.setter
    def palette(self, _palette):
        self.selected = _palette.name

    @GObject.Property(type=GObject.GObject)
    def palettes(self):
        return self._palettes

    def get_avalaible_palettes(self):
        """Returns the list of avalaible palettes"""

        return self._palettes

    def on_style_changed(self, *_args):
        """Run when the theme changes"""

        self.emit("style-changed")
        self.update_style_scheme()

    def get_dark(self):
        """Returns true if the current theme is dark"""

        return self.adw_style_manager.get_dark()

    def get_accent_color(self):
        """Returns the current accent color"""

        return self.adw_style_manager.get_accent_color_rgba().to_string()

    def get_current_scheme(self):
        """Returns the current GtkSource style scheme"""

        if self.adw_style_manager.get_dark():
            scheme = self.palette.dark_source_name
            return self.style_scheme_manager.get_scheme(scheme)
        else:
            scheme = self.palette.light_source_name
            return self.style_scheme_manager.get_scheme(scheme)

    def get_current_colors(self):
        """Returns the current list of colors"""

        if self.adw_style_manager.get_dark():
            return self.palette.dark_palette
        else:
            return self.palette.light_palette

    def update_style_scheme(self, *_args):
        """Updates the libadwaita colors"""

        Gtk.StyleContext.remove_provider_for_display(
            Gdk.Display.get_default(), self.css_provider
        )

        if "Adwaita" in self.palette.name:
            return

        colors = self.get_current_colors()

        primary = colors["background"]
        secondary = colors["foreground"]
        titlebar_fg = colors["titlebarforeground"]
        titlebar_bg = colors["titlebarbackground"]

        self.css_provider.load_from_string(
            f"""
        :root {{
            --primary-bg-color: {primary};
            --primary-fg-color: {secondary};
            --headerbar-bg-color: {primary};
            --headerbar-fg-color: {secondary};
            --headerbar-backdrop-color: mix(var(--headerbar-bg-color), var(--headerbar-bg-color), .5);
            --headerbar-shade-color: alpha(var(--primary-fg-color), 0.2);
            --window-bg-color: {primary};
            --window-fg-color: {secondary};
            --view-bg-color: color-mix(in srgb, {primary} 90%, {secondary} 10%);
            --view-fg-color: {secondary};
            --sidebar-bg-color: color-mix(in srgb, {primary} 95%, {secondary} 5%);
            --sidebar-fg-color: {secondary};
            --sidebar-backdrop-color: mix(var(--sidebar-bg-color), var(--window-bg-color), .5);
            --secondary-sidebar-bg-color: color-mix(in srgb, {primary} 98%, {secondary} 2%);
            --secondary-sidebar-fg-color: {secondary};
            --popover-bg-color: color-mix(in srgb, {primary} 95%, white 5%);
            --popover-fg-color: var(--window-fg-color);
            --dialog-bg-color: color-mix(in srgb, {primary} 95%, white 5%);
            --dialog-fg-color: var(--window-fg-color);
            --accent-bg-color: color-mix(in srgb, {secondary} 80%, {primary} 20%);
            --accent-fg-color: {primary};
            --accent-color: color-mix(in srgb, var(--accent-bg-color) 90%, {secondary} 10%);
            --dark-fill-bg-color: var(--headerbar-bg-color);
            --card-bg-color: {'alpha(white, .08)' if self.get_dark() else 'alpha(white, .8)'};
            --card-fg-color: var(--window-fg-color);
        }}
        """
        )

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
