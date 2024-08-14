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
from gi.repository import Vte
from gi.repository import Gdk

import subprocess
import re
import threading
import time
import os
from pprint import pprint

from .jupyter_server import JupyterServer
from .cell_ui import CellUI
from .cell import Cell, CellType
from .output import Output, OutputType
from .command_line import CommandLine

@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/window.ui')
class PlanetnineWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'PlanetnineWindow'

    toolbar_view = Gtk.Template.Child()
    terminal = Gtk.Template.Child()
    cells_list_box = Gtk.Template.Child()
    list_drop_target = Gtk.Template.Child()

    queue = []

    cache_dir = os.environ["XDG_CACHE_HOME"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.jupyter_server = JupyterServer()

        self.jupyter_server.connect("started", self.on_jupyter_server_started)
        self.jupyter_server.connect("new-line", self.on_jupyter_server_has_new_line)

        # self.jupyter_server.start()

        self.terminal.set_color_background(Gdk.RGBA(alpha=1))

        self.cells_model = Gio.ListStore()

        self.cells_list_box.bind_model(
            self.cells_model,
            self.create_widgets
        )

        self.list_drop_target.set_gtypes([Cell])
        self.list_drop_target.set_actions(Gdk.DragAction.MOVE)

        self.create_action('add-text-block', lambda *args: self.add_block(Cell(CellType.TEXT)))
        self.create_action('add-code-block', lambda *args: self.add_block(Cell(CellType.CODE)))

        self.add_block(Cell(CellType.CODE))

        self.command_line = CommandLine()

    def create_widgets(self, cell):
        return CellUI(cell)

    def add_block(self, cell):
        if self.cells_model.get_n_items() > 1:
            index = self.get_selected_cell_index()
            self.cells_model.insert(index + 1, cell)
        else:
            self.cells_model.append(cell)

        found, position = self.cells_model.find(cell)

        if found:
            self.set_selected_cell_index(position)

    def on_jupyter_server_started(self, server):
        server.get_kernel_specs(lambda suc, specs: pprint(specs))
        server.start_kernel_by_name("python3", lambda *args: print("kernel started"))

    def on_jupyter_server_has_new_line(self, server, line):
        self.terminal.feed([ord(char) for char in line + "\r\n"])

    def on_cell_request_delete(self, cell_iu, cell):
        found, position = self.cells_model.find(cell)

        if found:
            self.cells_model.remove(position)

    @Gtk.Template.Callback("on_run_button_clicked")
    def on_run_button_clicked(self, btn):
        cell = self.get_selected_cell()

        if cell.cell_type == CellType.CODE:
            if self.queue == []:
                self.run_cell(cell)
            else:
                self.queue.append(cell)
        else:
            self.select_next_cell()

    @Gtk.Template.Callback("on_stop_button_clicked")
    def on_stop_button_clicked(self, btn):
        print("STOP!")
        self.jupyter_server.start()

    @Gtk.Template.Callback("on_restart_button_clicked")
    def on_restart_button_clicked(self, btn):
        print("RESTART")
        self.jupyter_server.restart_kernel(2)

    @Gtk.Template.Callback("on_restart_and_run_button_clicked")
    def on_restart_and_run_button_clicked(self, btn):
        print("RESTART and run!")
        self.jupyter_server.restart_kernel(2)

        first_code_cell = None

        for index, cell in enumerate(self.cells_model):
            if not first_code_cell:
                if cell.cell_type == CellType.CODE:
                    first_code_cell = cell
                    continue
            if cell.cell_type == CellType.CODE:
                self.queue.append(cell)
        self.run_cell(first_code_cell)

    def get_selected_cell(self):
        cell_ui = self.cells_list_box.get_selected_row().get_child()
        return cell_ui.cell

    def run_cell(self, cell):
        found, position = self.cells_model.find(cell)

        if found:
            # select cell
            pass

        if cell.source.startswith("%"):
            self.command_line.run_command(
                cell.source[1:].split(" "),
                self.run_command_callback,
                args=[cell]
            )
        else:
            self.jupyter_server.run_code(
                cell.source,
                self.run_code_callback,
                finish_callback=self.run_code_finish,
                args=[cell]
            )

    def run_command_callback(self, line, cell):
        cell.add_stream(line + '\n')

    def run_code_callback(self, msg_type, content, cell):
        if msg_type == 'stream':
            output = Output(OutputType.STREAM)
            output.parse(content)
            cell.add_output(output)

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

    def run_code_finish(self, cell):
        if self.queue != []:
            cell=self.queue.pop(0)
            self.run_cell(cell)
        else:
            self.select_next_cell()

    def select_next_cell(self):
        pass

    def create_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        return action

    def get_selected_cell_index(self):
        selected_cell = self.cells_list_box.get_selected_row()

        self.cells_list_box.get_row_at_index
        for index in range(0, self.cells_model.get_n_items()):
            if self.cells_list_box.get_row_at_index(index) == selected_cell:
                return index

        return self.cells_model.get_n_items() - 1

    def set_selected_cell_index(self, index):
        self.cells_list_box.select_row(self.cells_list_box.get_row_at_index(index))

    @Gtk.Template.Callback("on_drop_target_drop")
    def on_drop_target_drop(self, drop_target, cell, x, y):
        target_row = self.cells_list_box.get_row_at_y(y)

        for index, model_cell in enumerate(self.cells_model):
            if cell == model_cell:
                cell_index = index

        if not target_row:
            self.cells_model.remove(cell_index)
            self.cells_model.append(cell)
            return

        target_index = target_row.get_index()

        self.cells_model.remove(cell_index)
        self.cells_model.insert(target_index, cell)

    @Gtk.Template.Callback("on_drop_target_motion")
    def on_drop_target_motion(self, drop_target, x, y):
        target_row = self.cells_list_box.get_row_at_y(y)

        if target_row:
            self.cells_list_box.drag_highlight_row(target_row)

        return Gdk.DragAction.MOVE

    @Gtk.Template.Callback("on_drop_target_leave")
    def on_drop_target_leave(self, drop_target):
        self.cells_list_box.drag_unhighlight_row()
