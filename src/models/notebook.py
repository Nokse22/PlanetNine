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


class Notebook(Gio.ListStore):
    __gtype_name__ = 'Notebook'

    title = GObject.Property(type=str, default="Untitled.ipynb")
    jupyter_kernel = None
    metadata = None

    def __init__(self, _path=None):
        super().__init__()

        self.set_path(_path)

        self.jupyter_kernel = None

        self.metadata = None

    @classmethod
    def new_from_file(cls, notebook_path):
        instance = cls(notebook_path)

        with open(notebook_path, 'r') as file:
            file_content = file.read()
            notebook_node = nbformat.reads(file_content, as_version=4)

        instance.parse(notebook_node)

        return instance

    @GObject.Property(type=GObject.GObject)
    def cells(self):
        return self

    @GObject.Property(type=GObject.GObject)
    def variables(self):
        return self._variables

    def set_path(self, _path):
        self.path = _path
        self.title = os.path.basename(self.path) if self.path else "Notebook.ipynb"

    def parse(self, notebook_node):
        for json_cell in notebook_node['cells']:
            cell = Cell.new_from_json(json_cell)

            self.append(cell)

        self.metadata = notebook_node.metadata

    def get_notebook_node(self):
        notebook_node = nbformat.v4.new_notebook()

        for cell in self.cells:
            cell_node = cell.get_cell_node()
            notebook_node.cells.append(cell_node)

        if self.metadata:
            notebook_node.metadata = self.metadata

        return notebook_node
