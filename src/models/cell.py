# cell.py
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
import uuid

from enum import IntEnum

from .output import Output, OutputType


class CellType(IntEnum):
    CODE = 0
    TEXT = 1
    RAW = 2


# This object holds the content and output of a notebook cell
class Cell(GObject.GObject):
    __gtype_name__ = 'Cell'

    __gsignals__ = {
        'output-added': (
            GObject.SignalFlags.RUN_FIRST, None, (GObject.GObject,)),
        'output-updated': (
            GObject.SignalFlags.RUN_FIRST, None, (GObject.GObject,)),
        'output-reset': (
            GObject.SignalFlags.RUN_FIRST, None, ()),
        'execution-count-changed': (
            GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    cell_type = GObject.Property(type=int, default=CellType.CODE)
    source = GObject.Property(type=str, default="")
    id = GObject.Property(type=str, default="")
    executing = GObject.Property(type=bool, default=False)

    def __init__(self, _cell_type=CellType.CODE):
        super().__init__()

        self.source = ""
        self.cell_type = _cell_type
        self.id = ""

        # Only for Code cells
        self._execution_count = None
        self._outputs = Gio.ListStore()
        self.executing = False

    @classmethod
    def new_from_json(cls, json_cell):
        """Initialize a new Cell from a json representation of the cell"""

        instance = cls()

        instance.parse(json_cell)

        return instance

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
        """Sets the source (content) of the cell

        :param str value: The new content
        """

        self.source = value

    def get_source(self):
        """Gets the source (content) of the cell

        :returns: The content of the cell
        :rtypes: str
        """

        return self.source

    def add_output(self, output):
        """Adds an output to the cell

        :param Output output: A new output
        """

        self._outputs.append(output)
        self.emit("output-added", output)

    def update_output(self, content):
        """Updates an output

        :param str content:
        """

        display_id = content['transient']['display_id']
        for index, output in enumerate(self._outputs):
            if output.display_id == display_id:
                output = Output(OutputType.DISPLAY_DATA)
                output.parse(content)
                self._outputs.remove(index)
                self._outputs.insert(index, output)
                self.emit("output-updated", output)

    def reset_output(self):
        """Resets all the outputs"""

        self._outputs.remove_all()
        self.execution_count = 0
        self.emit("output-reset")

    def get_cell_node(self):
        """Get the type of cell

        :returns: The type of cell
        :rtypes: CellType
        """

        if self.cell_type == CellType.TEXT:
            cell_node = nbformat.v4.new_markdown_cell()
            cell_node.source = self.source
            cell_node.id = self.id
            return cell_node

        cell_node = nbformat.v4.new_code_cell()
        cell_node.source = self.source
        cell_node.execution_count = self.execution_count
        cell_node.id = self.id

        for output in self.outputs:
            output_node = output.get_output_node()
            cell_node.outputs.append(output_node)

        return cell_node

    def parse(self, json_cell):
        """Sets its content from a json string containing the data

        :param str json_cell: The json representation of the cell
        """

        if json_cell['cell_type'] == "code":
            self.cell_type = CellType.CODE
        else:
            self.cell_type = CellType.TEXT
        self.source = ''.join(json_cell['source'])
        self.id = json_cell['id']
        if self.id is None or self.id == "":
            self.id = str(uuid.uuid4())

        if self.cell_type == CellType.CODE:
            self.execution_count = json_cell['execution_count'] or 0
            for json_output in json_cell['outputs']:
                match json_output['output_type']:
                    case 'stream':
                        output = Output(OutputType.STREAM)
                        output.text = ''.join(json_output['text'])
                    case 'display_data':
                        output = Output(OutputType.DISPLAY_DATA)
                        output.parse(json_output)
                    case 'execute_result':
                        output = Output(OutputType.EXECUTE_RESULT)
                        output.parse(json_output)
                        self.execution_count = json_output['execution_count']
                    case 'error':
                        output = Output(OutputType.ERROR)
                # output.metadata = json_output['metadata']
                self.add_output(output)

    def copy(self):
        """Copies the cell

        :returns: A new cell copy
        :rtypes: Cell
        """
        cell_node = self.get_cell_node()
        return Cell.new_from_json(cell_node)
