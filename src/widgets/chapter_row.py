# chapter_row.py
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


class ChapterRow(Gtk.Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        box = Gtk.Box(
            spacing=6,
            margin_start=3,
            margin_end=10,
            # margin_top=6,
            # margin_bottom=6
        )

        self.expander = Gtk.TreeExpander.new()
        # self.expander.set_hide_expander(True)
        self.expander.set_indent_for_icon(False)

        self.label = Gtk.Label(
            xalign=0,
            ellipsize=3,
        )

        box.append(self.expander)
        box.append(self.label)

        self.set_child(box)

        self.action = ""
        self.target = None

    def set_text(self, text):
        self.label.set_text(text)

    def disconnect(self, *_args):
        pass
