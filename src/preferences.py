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

from gi.repository import Gtk, GObject, Adw
from gi.repository import Panel, GtkSource


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/preferences.ui')
class Preferences(Adw.PreferencesDialog):
    __gtype_name__ = 'Preferences'

    vim_switch = Gtk.Template.Child()
    # code_buffer = Gtk.Template.Child()
    # event_controller_key = Gtk.Template.Child()
    # command_label = Gtk.Template.Child()
    style_flow_box = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        self.style_manager = Adw.StyleManager.get_default()
        self.style_manager.connect("notify::dark", self.update_style_scheme)

        self.update_style_scheme()

    def update_style_scheme(self, *args):
        child = self.style_flow_box.get_last_child()
        while child:
            self.style_flow_box.remove(child)
            child = self.style_flow_box.get_last_child()

        sm = GtkSource.StyleSchemeManager()

        available_schemes = [
            ('Adwaita', 'Adwaita-dark'),
            ('classic', 'classic-dark'),
            ('cobalt-light', 'cobalt'),
            ('kate', 'kate-dark'),
            ('tango', 'oblivion'),
            ('solarized-light', 'solarized-dark')
        ]

        theme = 1 if Adw.StyleManager.get_default().get_dark() else 0

        for scheme_id in available_schemes:
            scheme = sm.get_scheme(scheme_id[theme])
            preview = GtkSource.StyleSchemePreview.new(scheme)
            preview.add_css_class("card")

            self.style_flow_box.append(preview)

        self.style_flow_box.select_child(
            self.style_flow_box.get_child_at_index(0)
        )
