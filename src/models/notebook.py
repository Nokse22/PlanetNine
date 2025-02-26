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
import os

from .cell import Cell


# This object represent the content of a Notebook and holds all the cells
class Notebook(Gio.ListStore):
    __gtype_name__ = 'Notebook'

    title = GObject.Property(type=str, default="Untitled.ipynb")
    metadata = None

    def __init__(self, _path=None):
        super().__init__()

        self.set_path(_path)

        self.metadata = None

    @GObject.Property(type=GObject.GObject)
    def cells(self):
        return self

    @GObject.Property(type=GObject.GObject)
    def variables(self):
        return self._variables

    def set_path(self, _path):
        """Set the path where the notebook is saved

        :param str _path: The path to the file
        """
        self.path = _path
        self.title = os.path.basename(
            self.path) if self.path else "Notebook.ipynb"

    def get_path(self):
        return self.path

    def parse(self, notebook_node):
        """Parses the notebook from its json representation

        :param: The notebook node to parse
        """
        for json_cell in notebook_node.get('cells'):
            cell = Cell.new_from_json(json_cell)

            self.append(cell)

        self.metadata = notebook_node.get("metadata")

    def get_notebook_node(self):
        """Gets the notebook as a json

        :returns: The notebook node
        """
        notebook_node = nbformat.v4.new_notebook()

        for cell in self.cells:
            cell_node = cell.get_cell_node()
            notebook_node.cells.append(cell_node)

        if self.metadata:
            notebook_node.metadata = self.metadata

        return notebook_node
