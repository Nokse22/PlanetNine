# launcher.py
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

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import GLib

@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/launcher.ui')
class Launcher(Adw.Bin):
    __gtype_name__ = 'Launcher'

    notebook_listbox = Gtk.Template.Child()
    console_listbox = Gtk.Template.Child()

    def __init__(self, avalaible_kernels):
        super().__init__()

        self.notebook_listbox.bind_model(
            avalaible_kernels,
            self.create_notebook_widgets
        )

        self.console_listbox.bind_model(
            avalaible_kernels,
            self.create_console_widgets
        )

    def create_notebook_widgets(self, item):
        button_row = Adw.ButtonRow(
            title=item.display_name,
            end_icon_name="right-symbolic",
            action_name="win.new-notebook-name",
            action_target=GLib.Variant("s", item.name)
        )
        return button_row

    def create_console_widgets(self, item):
        button_row = Adw.ButtonRow(
            title=item.display_name,
            end_icon_name="right-symbolic",
            action_name="win.new-console-name",
            action_target=GLib.Variant("s", item.name)
        )
        return button_row
