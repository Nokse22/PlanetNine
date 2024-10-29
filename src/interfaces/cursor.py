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


# The ICursor interface is used for any page that has a TextView or SourceView
#       to show the cursor position in the UI and also go to a position
class ICursor:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.cursor_moved = GObject.Signal(
            "cursor-moved", arg_types=([Gtk.TextBuffer, int])
        )

    def __init__(self, override=False):
        if not override:
            self.buffer.connect(
                "notify::cursor-position",
                self.on_cursor_position_changed)

    def on_cursor_position_changed(self, *_args):
        """Emits the signal cursor-moved when the cursor is moved"""
        self.emit("cursor-moved", self.buffer, 0)

    def get_cursor_position(self):
        """To retrive the buffer and cell where is the cursor

        :returns: the buffere and cell where is the cursor
        :rtype: GtkSourceBuffer, int
        """
        return self.buffer, 0

    def move_cursor(self, line, column, index=0):
        """To request the cursor to be moved to a position

        :param int line: The line where to move the cursor
        :param int column: The column where to move the cursor
        :param int index: The cell where to move the cursor
        """
        succ, cursor_iter = self.buffer.get_iter_at_line_offset(line, column)
        if succ:
            self.buffer.place_cursor(cursor_iter)
