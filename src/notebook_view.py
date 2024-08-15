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

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Gio
from gi.repository import GObject, WebKit
from gi.repository import GtkSource, GLib
from gi.repository import Gdk, GdkPixbuf, Pango

from pprint import pprint
from enum import IntEnum

import hashlib
import base64
import os

from .markdown_textview import MarkdownTextView
from .terminal_textview import TerminalTextView
from .cell import Cell, CellType
from .cell_ui import CellUI
from .output import Output, OutputType, DataType
from .notebook import Notebook
from .command_line import CommandLine

@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/notebook_view.ui')
class NotebookView(Gtk.ScrolledWindow):
    __gtype_name__ = 'NotebookView'

    # __gsignals__ = {
    #     'request-delete': (GObject.SignalFlags.RUN_FIRST, None, ()),
    # }

    cells_list_box = Gtk.Template.Child()
    list_drop_target = Gtk.Template.Child()

    queue = []

    cache_dir = os.environ["XDG_CACHE_HOME"]

    def __init__(self):
        super().__init__()

        self.notebook_model = Notebook()

        self.cells_list_box.bind_model(
            self.notebook_model,
            self.create_widgets
        )

        self.list_drop_target.set_gtypes([Cell])
        self.list_drop_target.set_actions(Gdk.DragAction.MOVE)

        self.command_line = CommandLine()

        self.add_block(Cell(CellType.CODE))

    def create_widgets(self, cell):
        return CellUI(cell)

    def add_block(self, cell):
        if self.notebook_model.get_n_items() > 1:
            index = self.get_selected_cell_index()
            self.notebook_model.insert(index + 1, cell)
        else:
            self.notebook_model.append(cell)

        found, position = self.notebook_model.find(cell)

        if found:
            self.set_selected_cell_index(position)

    def get_selected_cell(self):
        cell_ui = self.cells_list_box.get_selected_row().get_child()
        return cell_ui.cell

    def select_next_cell(self):
        pass

    def get_selected_cell_index(self):
        selected_cell = self.cells_list_box.get_selected_row()

        self.cells_list_box.get_row_at_index
        for index in range(0, self.notebook_model.get_n_items()):
            if self.cells_list_box.get_row_at_index(index) == selected_cell:
                return index

        return self.notebook_model.get_n_items() - 1

    def set_selected_cell_index(self, index):
        self.cells_list_box.select_row(self.cells_list_box.get_row_at_index(index))

    @Gtk.Template.Callback("on_drop_target_drop")
    def on_drop_target_drop(self, drop_target, cell, x, y):
        target_row = self.cells_list_box.get_row_at_y(y)

        for index, model_cell in enumerate(self.notebook_model):
            if cell == model_cell:
                cell_index = index

        if not target_row:
            self.notebook_model.remove(cell_index)
            self.notebook_model.append(cell)
            return

        target_index = target_row.get_index()

        self.notebook_model.remove(cell_index)
        self.notebook_model.insert(target_index, cell)

    @Gtk.Template.Callback("on_drop_target_motion")
    def on_drop_target_motion(self, drop_target, x, y):
        target_row = self.cells_list_box.get_row_at_y(y)

        if target_row:
            self.cells_list_box.drag_highlight_row(target_row)

        return Gdk.DragAction.MOVE

    @Gtk.Template.Callback("on_drop_target_leave")
    def on_drop_target_leave(self, drop_target):
        self.cells_list_box.drag_unhighlight_row()

