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


class ICursor(GObject.GObject):
    __gtype_name__ = 'ICursor'

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.cursor_moved = GObject.Signal(
            'cursor-moved',
            arg_types=([Gtk.TextBuffer, int])
        )

    def move_cursor(self):
        raise NotImplementedError
