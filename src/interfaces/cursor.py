# cursor.py
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

from gi.repository import GObject, Gtk
from .interface import Interface


class ICursor(GObject.GObject, Interface):
    __gtype_name__ = 'ICursor'

    # gsignals = {
    #     'cursor-moved': (
    #         GObject.SignalFlags.RUN_FIRST,
    #         None,
    #         (Gtk.TextBuffer, int)
    #     )
    # }

    def __init__(cls, **kwargs):
        super().__init__()
        print("Adding signal for ", cls)
        GObject.signal_new(
            'cursor-moved',
            cls,
            GObject.SignalFlags.RUN_FIRST,
            None,
            (Gtk.TextBuffer, int)
        )

    def move_cursor(self):
        pass
