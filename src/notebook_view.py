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

    __gsignals__ = {
        'kernel-info-changed': (GObject.SignalFlags.RUN_FIRST, None, (str,str,)),
    }

    cells_list_box = Gtk.Template.Child()
    list_drop_target = Gtk.Template.Child()

    queue = []

    cache_dir = os.environ["XDG_CACHE_HOME"]

    _kernel_name = ""
    _kernel_status = ""

    def __init__(self, _notebook_model=None):
        super().__init__()

        if _notebook_model:
            self.notebook_model = _notebook_model
        else:
            self.notebook_model = Notebook()

        self.cells_list_box.bind_model(
            self.notebook_model,
            self.create_widgets
        )

        self.list_drop_target.set_gtypes([Cell])
        self.list_drop_target.set_actions(Gdk.DragAction.MOVE)

        self.command_line = CommandLine()

        self.queue = []

        self.add_cell(Cell(CellType.CODE))

        self._kernel_name = ""

    @GObject.Property(type=str, default="")
    def kernel_name(self):
        return self._kernel_name

    @kernel_name.setter
    def kernel_name(self, value):
        self._kernel_name = value
        self.emit("kernel-info-changed", self._kernel_name, self._kernel_status)

    @GObject.Property(type=str, default="")
    def kernel_status(self):
        return self._kernel_status

    @kernel_status.setter
    def kernel_status(self, value):
        self._kernel_status = value
        self.emit("kernel-info-changed", self._kernel_name, self._kernel_status)

    def run_selected_cell(self):
        cell = self.get_selected_cell()

        if cell.cell_type == CellType.CODE:
            if self.queue == []:
                self.run_cell(cell)
            else:
                self.queue.append(cell)
        else:
            self.select_next_cell()

    def run_all_cells(self):
        first_code_cell = None

        for index, cell in enumerate(self.notebook_model):
            if not first_code_cell:
                if cell.cell_type == CellType.CODE:
                    first_code_cell = cell
                    continue
            if cell.cell_type == CellType.CODE:
                self.queue.append(cell)
        self.run_cell(first_code_cell)

    def run_cell(self, cell):
        found, position = self.notebook_model.find(cell)

        if found:
            # select cell
            pass

        if cell.source.startswith("%"):
            cell.reset_output()
            self.command_line.run_command(
                cell.source[1:].split(" "),
                self.run_command_callback,
                cell
            )
        elif self.notebook_model.jupyter_kernel:
            self.notebook_model.jupyter_kernel.run_code(
                cell.source,
                self.run_code_callback,
                cell
            )

    def run_command_callback(self, line, cell):
        output = Output(OutputType.STREAM)
        output.text = line + '\n'
        cell.add_output(output)

    def run_code_callback(self, msg, cell):
        msg_type = msg['header']['msg_type']
        content = msg['content']

        if msg_type == 'stream':
            output = Output(OutputType.STREAM)
            output.parse(content)
            cell.add_output(output)

            self._kernel_status = "busy"
            self.emit("kernel-info-changed", self._kernel_name, self._kernel_status)

        elif msg_type == 'execute_input':
            count = content['execution_count']
            cell.execution_count = int(count)
            cell.reset_output()

        elif msg_type == 'display_data':
            output = Output(OutputType.DISPLAY_DATA)
            output.parse(content)
            cell.add_output(output)

        elif msg_type == 'error':
            output = Output(OutputType.ERROR)
            output.parse(content)
            cell.add_output(output)

        elif msg_type == 'status':
            status = content['execution_state']

            self._kernel_status = status
            self.emit("kernel-info-changed", self._kernel_name, self._kernel_status)

            if status == "idle":
                if self.queue != []:
                    cell=self.queue.pop(0)
                    self.run_cell(cell)
                    found, position = self.notebook_model.find(cell)
                    if found:
                        self.set_selected_cell_index(position)
                else:
                    self.select_next_cell()

    def set_kernel(self, jupyter_kernel):
        self.notebook_model.jupyter_kernel = jupyter_kernel
        self.kernel_name = jupyter_kernel.name
        print("NAME: ", self.kernel_name, self.notebook_model.jupyter_kernel)

    def create_widgets(self, cell):
        cell = CellUI(cell)
        cell.connect("request-delete", self.on_cell_request_delete)
        return cell

    def on_cell_request_delete(self, cell_ui):
        found, position = self.notebook_model.find(cell_ui.cell)

        if found:
            self.notebook_model.remove(position)

    def add_cell(self, cell):
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
        cell = self.get_selected_cell()
        found, position = self.notebook_model.find(cell)
        if found and position != self.notebook_model.get_n_items() - 1:
            self.set_selected_cell_index(position + 1)

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

        cell_index = None
        for index, model_cell in enumerate(self.notebook_model):
            if cell == model_cell:
                cell_index = index

        if cell_index:
            self.notebook_model.remove(cell_index)

        if not target_row:
            self.notebook_model.append(cell)

        else:
            target_index = target_row.get_index()
            self.notebook_model.insert(target_index, cell)

    @Gtk.Template.Callback("on_drop_target_motion")
    def on_drop_target_motion(self, drop_target, x, y):
        target_row = self.cells_list_box.get_row_at_y(y)

        if target_row:
            self.cells_list_box.drag_highlight_row(target_row)

        vadjustment = self.get_vadjustment()

        visible_height = vadjustment.get_page_size()
        content_height = vadjustment.get_upper()

        current_scroll_position = vadjustment.get_value()

        margin = 50

        relative_y = y - current_scroll_position

        if relative_y < margin:
            delta = (margin - relative_y) / margin * 20
            new_value = max(current_scroll_position - delta, 0)
            vadjustment.set_value(new_value)
        elif relative_y > visible_height - margin:
            delta = (relative_y - (visible_height - margin)) / margin * 20
            new_value = min(current_scroll_position + delta, content_height - visible_height)
            vadjustment.set_value(new_value)

        return Gdk.DragAction.MOVE

    @Gtk.Template.Callback("on_drop_target_leave")
    def on_drop_target_leave(self, drop_target):
        self.cells_list_box.drag_unhighlight_row()


