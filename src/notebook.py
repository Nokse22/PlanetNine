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

from gi.repository import Gio
from gi.repository import GObject

import nbformat

from enum import IntEnum

from .cell import Cell, CellType
from .output import Output, OutputType

class Notebook(Gio.ListStore):
    __gtype_name__ = 'Notebook'

    name = GObject.Property(type=str, default="")
    jupyter_kernel = None

    def __init__(self, **kwargs):
        super().__init__()

        if 'name' in kwargs:
            self.name = kwargs['name']
        else:
            self.name = ""

        self.jupyter_kernel = None

    @classmethod
    def new_from_json(cls, notebook_node):
        instance = cls()

        instance.parse(notebook_node)

        return instance

    @GObject.Property(type=GObject.GObject)
    def cells(self):
        return self

    def parse(self, notebook_node):
        for json_cell in notebook_node['cells']:
            cell = Cell.new_from_json(json_cell)

            self.append(cell)

    def get_notebook_node(self):
        notebook_node = nbformat.v4.new_notebook()
        for cell in self.cells:
            cell_node = cell.get_cell_node()
            notebook_node.cells.append(cell_node)

        return notebook_node
