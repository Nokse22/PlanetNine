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

from gi.repository import Gtk, Adw, Gio
from gi.repository import Panel, GtkSource
from gi.repository import Spelling

from ..widgets.json_viewer import JsonViewer


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/json_viewer_page.ui')
class JsonViewerPage(Panel.Widget):
    __gtype_name__ = 'JsonViewerPage'

    source_view = Gtk.Template.Child()
    code_buffer = Gtk.Template.Child()
    json_viewer_bin = Gtk.Template.Child()
    stack = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        self.connect("unrealize", self.__on_unrealized)

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

        # SET THE LANGUAGE STYLE SCHEME

        lm = GtkSource.LanguageManager()
        lang = lm.get_language("json")
        self.code_buffer.set_language(lang)
        self.code_buffer.set_highlight_syntax(True)

        sm = GtkSource.StyleSchemeManager()
        scheme = sm.get_scheme("Adwaita-dark")
        self.code_buffer.set_style_scheme(scheme)

        self.style_manager = Adw.StyleManager.get_default()
        self.style_manager.connect("notify::dark", self.update_style_scheme)
        self.update_style_scheme()

        # ENABLE SPELL CHECK

        checker = Spelling.Checker.get_default()
        adapter = Spelling.TextBufferAdapter.new(self.code_buffer, checker)
        extra_menu = adapter.get_menu_model()

        self.source_view.set_extra_menu(extra_menu)
        self.source_view.insert_action_group('spelling', adapter)

        adapter.set_enabled(True)

        # SETUP the page

        self.stack.connect("notify::visible-child-name", self.on_json_changed)

    def on_json_changed(self, *args):
        start = self.code_buffer.get_start_iter()
        end = self.code_buffer.get_end_iter()
        text = self.code_buffer.get_text(start, end, True)
        viewer = JsonViewer()
        viewer.parse_json_string(text)
        self.json_viewer_bin.set_child(viewer)

    def update_style_scheme(self, *args):
        scheme_name = "Adwaita"
        if Adw.StyleManager.get_default().get_dark():
            scheme_name += "-dark"
        sm = GtkSource.StyleSchemeManager()
        scheme = sm.get_scheme(scheme_name)
        self.code_buffer.set_style_scheme(scheme)

    def __on_unrealized(self, *args):
        self.disconnect_by_func(self.__on_unrealized)

        self.style_manager.disconnect_by_func(self.update_style_scheme)

        self.stack.disconnect_by_func(self.on_json_changed)

        print(f"Unrealize {self}")

    def __del__(self, *args):
        print(f"DELETING {self}")
