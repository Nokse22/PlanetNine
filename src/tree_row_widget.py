# window.py
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

from gi.repository import Gtk, Adw, Gio, GObject
from enum import IntEnum

import os


class NodeType(IntEnum):
    ROOT = 0
    FILE = 1
    FOLDER = 2


class TreeNode(GObject.Object):
    def __init__(self, node_path, node_type, children=None):
        super().__init__()
        self.node_path = node_path
        self.node_type = node_type
        self.children = children or []

        self.display_name = os.path.basename(self.node_path)


class TreeWidget(Adw.Bin):
    def __init__(self):
        super().__init__()

        box = Gtk.Box(
            spacing=6,
            margin_start=3,
            margin_end=10,
            margin_top=6,
            margin_bottom=6
        )

        self.expander = Gtk.TreeExpander.new()
        # self.expander.set_hide_expander(True)
        self.expander.set_indent_for_icon(False)

        self.label = Gtk.Label(
            xalign=0,
            ellipsize=3,
        )

        self.image = Gtk.Image(icon_name="python-symbolic", margin_end=6)

        self.menu_model = Gio.Menu()

        box.append(self.expander)
        box.append(self.image)
        box.append(self.label)

        self.click_controller = Gtk.GestureClick(button=0)
        self.click_controller.connect("released", self.on_click_released)
        self.add_controller(self.click_controller)

        self.set_child(box)

    def set_text(self, text):
        self.label.set_text(text)

    def set_icon_name(self, icon_name):
        self.image.set_from_icon_name(icon_name)

    def set_menu_model(self, model):
        self.menu_model = model

    def on_click_released(self, gesture, n_press, click_x, click_y):
        if gesture.get_current_button() == 3:
            if n_press != 1:
                return

            widget = gesture.get_widget()
            popover = Gtk.PopoverMenu(position=1, menu_model=self.menu_model)
            popover.set_parent(widget)
            popover.popup()

            return True
        elif gesture.get_current_button() == 1:
            list_row = self.expander.get_list_row()
            list_row.set_expanded(not list_row.get_expanded())

    def expand(self):
        list_row = self.expander.get_list_row()
        list_row.set_expanded(True)

    def collapse(self):
        list_row = self.expander.get_list_row()
        list_row.set_expanded(False)
