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
from ..interfaces.style_update import IStyleUpdate
from ..interfaces.language import ILanguage


@Gtk.Template(
    resource_path='/io/github/nokse22/PlanetNine/gtk/console_cell.ui')
class ConsoleCell(Gtk.Box, IStyleUpdate, ILanguage):
    __gtype_name__ = 'ConsoleCell'

    source_view = Gtk.Template.Child()
    buffer = Gtk.Template.Child()
    output_scrolled_window = Gtk.Template.Child()
    output_box = Gtk.Template.Child()

    cache_dir = os.environ["XDG_CACHE_HOME"]

    def __init__(self, content, **kwargs):
        super().__init__(**kwargs)
        IStyleUpdate.__init__(self, **kwargs)
        ILanguage.__init__(self, **kwargs)

        self.buffer.set_text(content)

        self.buffer.set_highlight_syntax(True)

        self.output_loader = OutputLoader(self.output_box)

    def add_output(self, output):
        self.output_scrolled_window.set_visible(True)
        self.output_loader.add_output(output)

    def disconnect(self, *args):
        self.style_manager.disconnect_by_func(self.update_style_scheme)

        print("unrealize: ", sys.getrefcount(self))

    def __del__(self, *args):
        print(f"DELETING {self}")
