# console_cell.py
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

from gi.repository import Gtk
from gi.repository import GtkSource

import os
import sys

from ..others.output_loader import OutputLoader
from ..others.style_manager import StyleManager


@Gtk.Template(
    resource_path='/io/github/nokse22/PlanetNine/gtk/console_cell.ui')
class ConsoleCell(Gtk.Box):
    __gtype_name__ = 'ConsoleCell'

    source_view = Gtk.Template.Child()
    code_buffer = Gtk.Template.Child()
    output_scrolled_window = Gtk.Template.Child()
    output_box = Gtk.Template.Child()

    cache_dir = os.environ["XDG_CACHE_HOME"]

    def __init__(self, content):
        super().__init__()

        self.code_buffer.set_text(content)

        self.code_buffer.set_highlight_syntax(True)

        self.output_loader = OutputLoader(self.output_box)

        self.style_manager = StyleManager()
        self.style_manager.connect("style-changed", self.update_style_scheme)
        self.update_style_scheme()

    def add_output(self, output):
        self.output_scrolled_window.set_visible(True)
        self.output_loader.add_output(output)

    def update_style_scheme(self, *args):
        scheme = self.style_manager.get_current_scheme()
        self.code_buffer.set_style_scheme(scheme)

    def set_language(self, lang_name):
        lm = GtkSource.LanguageManager()
        lang = lm.get_language(lang_name)
        self.code_buffer.set_language(lang)

    def disconnect(self, *args):
        self.style_manager.disconnect_by_func(self.update_style_scheme)

        print("unrealize: ", sys.getrefcount(self))

    def __del__(self, *args):
        print(f"DELETING {self}")
