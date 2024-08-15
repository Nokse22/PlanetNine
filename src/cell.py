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

from .output import Output, OutputType

class CellType(IntEnum):
    CODE = 0
    TEXT = 1
    RAW = 2

class Cell(GObject.GObject):
    __gtype_name__ = 'Cell'

    __gsignals__ = {
        'output-added': (GObject.SignalFlags.RUN_FIRST, None, (GObject.GObject,)),
        'output-reset': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'execution-count-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    cell_type = GObject.Property(type=int, default=CellType.CODE)
    source = GObject.Property(type=str, default="")
    id = GObject.Property(type=str, default="")

    def __init__(self, _cell_type=CellType.CODE):
        super().__init__()

        self.source = ""
        self.cell_type = _cell_type
        self.id = ""

        # Only for Code cells
        self._execution_count = None
        self._outputs = Gio.ListStore()

    @GObject.Property(type=GObject.GObject)
    def outputs(self):
        return self._outputs

    @outputs.setter
    def outputs(self, values):
        self._outputs = values
        self.notify("outputs")

    @GObject.Property(type=int, default=0)
    def execution_count(self):
        return self._execution_count

    @execution_count.setter
    def execution_count(self, value):
        self._execution_count = value
        self.emit("execution-count-changed", value)

    def set_source(self, value):
        self.source = value

    def get_source(self,):
        return self.source

    def add_output(self, output):
        self._outputs.append(output)
        self.emit("output-added", output)

    def reset_output(self):
        self._outputs.remove_all()
        self.emit("output-reset")

    def get_cell_node(self):
        if self.cell_type == CellType.TEXT:
            cell_node = nbformat.v4.new_markdown_cell()
            return cell_node

        cell_node = nbformat.v4.new_code_cell()
        cell_node.source = self.source
        cell_node.execution_count = self.execution_count
        cell_node.id = self.id

        for output in self.outputs:
            output_node = output.get_output_node()
            cell_node.outputs.append(output_node)

        return cell_node
