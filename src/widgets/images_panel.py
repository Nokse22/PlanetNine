# images_panel.py
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

from gi.repository import Gtk, Panel


@Gtk.Template(
    resource_path='/io/github/nokse22/PlanetNine/gtk/images_panel.ui')
class ImagesPanel(Panel.Widget):
    __gtype_name__ = 'ImagesPanel'

    main_picture = Gtk.Template.Child()
    listbox = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        # self.connect("unrealize", self.__on_unrealized)

    def __on_unrealized(self, *args):
        self.disconnect_by_func(self.__on_unrealized)

        print(f"Unrealize {self}")

    def __del__(self, *args):
        print(f"DELETING {self}")
