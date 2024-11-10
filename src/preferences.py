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

from gi.repository import Gtk, Adw, Gio, Xdp
from gi.repository import GtkSource

from .others.style_manager import StyleManager, ThemeSelector


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

    flow_box = Gtk.Template.Child()

    sandboxed_settings_group = Gtk.Template.Child()
    sandbox_server_switch = Gtk.Template.Child()
    jupyter_path_entry = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        self.prev_style_preview = None

        self.style_manager = StyleManager()

        self.flow_box.bind_model(
            self.style_manager.palettes,
            self.create_theme_selectors)

        self.flow_box.connect(
            "selected-children-changed", self.on_selected_style_changed)

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
            'selected-theme', self.style_manager,
            'selected', Gio.SettingsBindFlags.DEFAULT)

        self.settings.bind(
            'use-external-server', self.sandbox_server_switch,
            'active', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind(
            'jupyter-path', self.jupyter_path_entry,
            'text', Gio.SettingsBindFlags.DEFAULT)

        self.style_manager.selected = self.settings.get_string('selected-theme')
        self.flow_box.select_child(self.flow_box.get_child_at_index(0))

        self.portal = Xdp.Portal()

        if not self.portal.running_under_sandbox():
            self.sandboxed_settings_group.set_visible(False)
            self.sandbox_server_switch.set_active(False)

    def on_selected_style_changed(self, *_args):
        if self.prev_style_preview:
            self.prev_style_preview.set_selected(False)
        selected = self.flow_box.get_selected_children()[0].get_child()
        selected.set_selected(True)
        self.style_manager.palette = selected.palette
        self.prev_style_preview = selected

    def create_theme_selectors(self, palette):
        return ThemeSelector(palette)
