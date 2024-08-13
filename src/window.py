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
import hashlib
import base64

from .jupyter_server import JupyterServer
from .block import UIBlock, Block, CellType
from .command_line import CommandLine

@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/window.ui')
class PlanetnineWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'PlanetnineWindow'

    toolbar_view = Gtk.Template.Child()
    terminal = Gtk.Template.Child()
    list_view = Gtk.Template.Child()
    item_factory = Gtk.Template.Child()
    list_drop_target = Gtk.Template.Child()

    queue = []

    cache_dir = os.environ["XDG_CACHE_HOME"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.jupyter_server = JupyterServer()

        self.jupyter_server.connect("started", self.on_jupyter_server_started)
        self.jupyter_server.connect("new-line", self.on_jupyter_server_has_new_line)

        self.jupyter_server.start()

        self.terminal.set_color_background(Gdk.RGBA(alpha=1))

        self.blocks_model = Gio.ListStore()

        self.blocks_selection_model = Gtk.SingleSelection(
            model=self.blocks_model,
            can_unselect=False
        )

        self.list_view.set_model(self.blocks_selection_model)

        self.list_drop_target.set_gtypes([Block])
        self.list_drop_target.set_actions(Gdk.DragAction.MOVE)

        self.create_action('add-text-block', lambda *args: self.add_block(Block(CellType.TEXT)))
        self.create_action('add-code-block', lambda *args: self.add_block(Block(CellType.CODE)))

        self.blocks_model.append(Block(CellType.CODE))

        self.command_line = CommandLine()

    def add_block(self, cell):
        if self.blocks_model.get_n_items() == 0:
            self.blocks_model.append(cell)
        else:
            position = self.blocks_selection_model.get_selected() + 1
            self.blocks_model.insert(position, cell)

    def on_jupyter_server_started(self, server):
        server.get_kernel_specs()
        server.start_default_kernel()

    def on_jupyter_server_has_new_line(self, server, line):
        self.terminal.feed([ord(char) for char in line + "\r\n"])

    def on_cell_request_delete(self, cell_iu, cell):
        found, position = self.blocks_model.find(cell)

        if found:
            self.blocks_model.remove(position)

    @Gtk.Template.Callback("on_factory_bind")
    def on_factory_bind(self, factory, list_item):
        cell = list_item.get_item()

        ui_cell = list_item.get_child()
        if cell.get_block() is None:
            cell.set_block(ui_cell)
            ui_cell.connect("request-delete", self.on_cell_request_delete, cell)

    @Gtk.Template.Callback("on_factory_setup")
    def on_factory_setup(self, factory, list_item):
        code_block = UIBlock()
        list_item.set_focusable(False)
        list_item.set_child(code_block)

    @Gtk.Template.Callback("on_run_button_clicked")
    def on_run_button_clicked(self, btn):
        cell = self.blocks_selection_model.get_selected_item()

        if cell.block_type == CellType.CODE:
            if self.queue == []:
                self.run_cell(cell)
            else:
                self.queue.append(cell)
        else:
            self.select_next_cell()

    @Gtk.Template.Callback("on_stop_button_clicked")
    def on_stop_button_clicked(self, btn):
        print("STOP!")

    @Gtk.Template.Callback("on_restart_button_clicked")
    def on_restart_button_clicked(self, btn):
        print("RESTART")
        self.jupyter_server.restart_kernel(2)

    @Gtk.Template.Callback("on_restart_and_run_button_clicked")
    def on_restart_and_run_button_clicked(self, btn):
        print("RESTART and run!")
        self.jupyter_server.restart_kernel(2)

        first_code_cell = None

        for index, cell in enumerate(self.blocks_model):
            if not first_code_cell:
                if cell.block_type == CellType.CODE:
                    first_code_cell = cell
                    continue
            if cell.block_type == CellType.CODE:
                self.queue.append(cell)
        self.run_cell(first_code_cell)

    def run_cell(self, cell):
        found, position = self.blocks_model.find(cell)

        if found:
            self.blocks_selection_model.set_selected(position)

        if cell.content.startswith("%"):
            self.command_line.run_command(
                cell.content[1:].split(" "),
                callback=self.run_command_callback,
                args=[cell]
            )
        else:
            self.jupyter_server.run_code(
                cell.content,
                callback=self.run_code_callback,
                finish_callback=self.run_code_finish,
                args=[cell]
            )

    def run_command_callback(self, line, cell):
        cell.set_output(line + '\n')

    def run_code_callback(self, msg_type, content, cell):
        if msg_type == 'stream':
            text = content['text']
            cell.set_output(text)

        elif msg_type == 'execute_input':
            count = content['execution_count']
            cell.set_count(int(count))
            cell.reset_output()

        elif msg_type == 'display_data':
            data = content['data']["image/png"]

            image_data = base64.b64decode(data)
            sha256_hash = hashlib.sha256(image_data).hexdigest()

            image_path = os.path.join(self.cache_dir, f"{sha256_hash}.png")
            with open(image_path, 'wb') as f:
                f.write(image_data)

            cell.add_image(image_path)

        elif msg_type == 'error':
            cell.set_output("\n".join(content['traceback']))

    def run_code_finish(self, cell):
        if self.queue != []:
            cell=self.queue.pop(0)
            self.run_cell(cell)
        else:
            self.select_next_cell()

    def select_next_cell(self):
        index = self.blocks_selection_model.get_selected()
        if index != self.blocks_model.get_n_items() - 1:
            self.blocks_selection_model.set_selected(index + 1)

    def create_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        return action

    @Gtk.Template.Callback("on_drop_target_drop")
    def on_drop_target_drop(self, drop_target, value, x, y):
        print("DROP")
        print(value)

        target_row = self.list_view.get_row_at_y(y)
        target_index = target_row.get_index()

        print(target_row)
