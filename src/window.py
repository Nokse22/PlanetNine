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

from .jupyter_server import JupyterServer
from .block import UIBlock, Block, BlockType

@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/window.ui')
class PlanetnineWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'PlanetnineWindow'

    toolbar_view = Gtk.Template.Child()
    terminal = Gtk.Template.Child()
    list_view = Gtk.Template.Child()
    item_factory = Gtk.Template.Child()

    queue = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.jupyter_server = JupyterServer()

        self.jupyter_server.connect("started", self.on_jupyter_server_started)
        self.jupyter_server.connect("new-line", self.on_jupyter_server_has_new_line)

        self.jupyter_server.start()

        self.terminal.set_color_background(Gdk.RGBA(alpha=1))

        self.blocks_model = Gio.ListStore()

        self.blocks_selection_model = Gtk.SingleSelection(model=self.blocks_model)

        self.list_view.set_model(self.blocks_selection_model)

        self.blocks_model.append(Block(BlockType.CODE))

    def on_jupyter_server_started(self, server):
        server.get_kernel_specs()
        server.start_default_kernel()

    def on_jupyter_server_has_new_line(self, server, line):
        self.terminal.feed([ord(char) for char in line + "\r\n"])

    @Gtk.Template.Callback("on_add_button_clicked")
    def on_add_button_clicked(self, btn):
        block = Block(BlockType.CODE)
        self.blocks_model.append(block)

    @Gtk.Template.Callback("on_factory_bind")
    def on_factory_bind(self, factory, list_item):
        block = list_item.get_item()

        ui_block = list_item.get_child()
        if ui_block.get_block() is None:
            ui_block.set_block(block)

        # if block.block_type == BlockType.CODE and not block.binded:
        #     code_block = list_item.get_child()
        #     block.bind_property("content", code_block, "content", 1)
        #     block.bind_property("output", code_block, "output", 1)
        #     block.bind_property("count", code_block, "count", 1)
        #     block.set_binded(True)

    @Gtk.Template.Callback("on_factory_setup")
    def on_factory_setup(self, factory, list_item):
        code_block = UIBlock()
        list_item.set_focusable(False)
        list_item.set_child(code_block)

    @Gtk.Template.Callback("on_run_button_clicked")
    def on_run_button_clicked(self, btn):
        block = self.blocks_selection_model.get_selected_item()

        if block.block_type == BlockType.CODE:
            if self.queue == []:
                self.jupyter_server.run_code(
                    code=block.content,
                    block=block,
                    callback=self.run_code_callback,
                    finish_callback=self.run_code_finish
                )
            else:
                self.queue.append(block)

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
        for index, block in enumerate(self.blocks_model):
            self.queue.append(block)
        block = self.blocks_model.get_item(0)
        self.jupyter_server.run_code(
            code=block.content,
            block=block,
            callback=self.run_code_callback,
            finish_callback=self.run_code_finish
        )

    def run_code_callback(self, msg_type, stream_content, block):
        if msg_type == 'stream':
            text = stream_content['text']
            block.set_output(text)

        elif msg_type == 'execute_input':
            count = stream_content['execution_count']
            block.set_count(int(count))
            block.set_output("")

        elif msg_type == 'error':
            block.set_output("\n".join(stream_content['traceback']))

    def run_code_finish(self, block):
        if self.queue != []:
            block=self.queue.pop(0)
            self.jupyter_server.run_code(
                code=block.content,
                block=block,
                callback=self.run_code_callback,
                finish_callback=self.run_code_finish
            )
