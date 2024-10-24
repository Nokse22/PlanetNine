# preferences.py
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

from gi.repository import Gtk, GObject, Adw, Gio, Gdk, Graphene
from gi.repository import Panel, GtkSource

from .others.style_manager import StyleManager


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/preferences.ui')
class Preferences(Adw.PreferencesDialog):
    __gtype_name__ = 'Preferences'

    code_vim_switch = Gtk.Template.Child()
    code_line_number_switch = Gtk.Template.Child()
    code_highlight_row_switch = Gtk.Template.Child()
    code_wrap_switch = Gtk.Template.Child()
    code_highligh_brakets_switch = Gtk.Template.Child()

    notebook_line_number_switch = Gtk.Template.Child()

    start_switch = Gtk.Template.Child()
    shutdown_kernels_switch = Gtk.Template.Child()

    grid_view = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        self.prev_style_preview = None

        self.scheme_manager = GtkSource.StyleSchemeManager()
        self.scheme_manager.append_search_path(
            "resource:///io/github/nokse22/PlanetNine/styles/schemes/")

        self.style_manager = StyleManager()

        self.selection_model = Gtk.SingleSelection(
            model=self.style_manager.palettes)
        self.grid_view.set_model(self.selection_model)

        self.selection_model.connect(
            "notify::selected", self.on_selected_style_changed)

        # Bind settings to widgets

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

        self.settings.bind(
            'notebook-line-number', self.notebook_line_number_switch,
            'active', Gio.SettingsBindFlags.DEFAULT)

        self.settings.bind(
            'code-vim', self.code_vim_switch,
            'active', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind(
            'code-line-number', self.code_line_number_switch,
            'active', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind(
            'code-highlight-row', self.code_highlight_row_switch,
            'active', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind(
            'code-highlight-brackets', self.code_highligh_brakets_switch,
            'active', Gio.SettingsBindFlags.DEFAULT)

        self.settings.bind(
            'start-server-immediately', self.start_switch,
            'active', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind(
            'auto-shutdown-kernel', self.shutdown_kernels_switch,
            'active', Gio.SettingsBindFlags.DEFAULT)

        self.settings.bind(
            'selected-theme-n', self.style_manager,
            'selected', Gio.SettingsBindFlags.DEFAULT)

        self.style_manager.selected = self.settings.get_int('selected-theme-n')
        self.selection_model.set_selected(self.settings.get_int('selected-theme-n'))

    def on_selected_style_changed(self, *args):
        self.style_manager.selected = self.selection_model.get_selected()

    @Gtk.Template.Callback("on_grid_view_setup")
    def on_grid_view_setup(self, _factory, list_item):
        list_item.set_child(Gtk.Box(
            halign=Gtk.Align.CENTER,
            overflow=Gtk.Overflow.HIDDEN
        ))

    @Gtk.Template.Callback("on_grid_view_bind")
    def on_grid_view_bind(self, _factory, list_item):
        widget = list_item.get_child()
        palette = list_item.get_item()

        scheme = self.scheme_manager.get_scheme(palette.light_source_name)
        light_preview = GtkSource.StyleSchemePreview.new(scheme)

        scheme = self.scheme_manager.get_scheme(palette.dark_source_name)
        dark_preview = GtkSource.StyleSchemePreview.new(scheme)

        widget.append(light_preview)
        widget.append(dark_preview)
        widget.add_css_class("card")
