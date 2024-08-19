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
from gi.repository import Gdk
from gi.repository import Panel

import os
import nbformat
import logging
import asyncio
from pprint import pprint

from .async_helpers import dialog_choose_async

from .jupyter_server import JupyterServer
from .cell import Cell, CellType
from .command_line import CommandLine
from .notebook import Notebook
from .notebook_page import NotebookPage
from .browser_page import BrowserPage
from .kernel_manager_view import KernelManagerView
from .workspace_view import WorkspaceView
from .launcher import Launcher
from .console_page import ConsolePage
from .code_page import CodePage


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/window.ui')
class PlanetnineWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'PlanetnineWindow'

    terminal = Gtk.Template.Child()
    grid = Gtk.Template.Child()
    omni_bar = Gtk.Template.Child()
    kernel_status_menu = Gtk.Template.Child()
    select_kernel_dialog = Gtk.Template.Child()
    shutdown_kernel_dialog = Gtk.Template.Child()
    restart_kernel_dialog = Gtk.Template.Child()
    select_kernel_combo_row = Gtk.Template.Child()
    omni_label = Gtk.Template.Child()
    server_status_label = Gtk.Template.Child()
    start_sidebar_panel_frame = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        Gio.Subprocess.new(
            ['pylsp', '--tcp', '--host', '127.0.0.1', '--port', '2087'],
            Gio.SubprocessFlags.NONE
        )

        self.jupyter_server = JupyterServer()

        self.jupyter_server.connect("started", self.on_jupyter_server_started)
        self.jupyter_server.connect("new-line", self.on_jupyter_server_has_new_line)

        self.kernel_manager_view = KernelManagerView(
            self.jupyter_server.avalaible_kernels,
            self.jupyter_server.kernels
        )
        self.start_sidebar_panel_frame.add(self.kernel_manager_view)

        self.workspace_view = WorkspaceView()
        self.start_sidebar_panel_frame.add(self.workspace_view)

        self.jupyter_server.start()

        self.terminal.set_color_background(Gdk.RGBA(alpha=1))

        self.create_action(
            'add-text-cell',
            lambda *_: self.add_cell_to_selected_notebook(Cell(CellType.TEXT))
        )
        self.create_action(
            'add-code-cell',
            lambda *_: self.add_cell_to_selected_notebook(Cell(CellType.CODE))
        )
        self.create_action(
            'add-raw-cell',
            lambda *_: self.add_cell_to_selected_notebook(Cell(CellType.TEXT))
        )
        self.create_action_with_target(
            'new-notebook',
            GLib.VariantType.new("s"),
            self.on_new_notebook_action
        )

        self.create_action_with_target(
            'new-console',
            GLib.VariantType.new("s"),
            self.on_new_console_action
        )

        self.create_action_with_target(
            'new-code',
            GLib.VariantType.new("s"),
            self.on_new_code_action
        )

        self.create_action('run-selected-cell', self.run_selected_cell)

        self.create_action_with_target(
            'shutdown-kernel',
            GLib.VariantType.new("s"),
            self.shutdown_kernel_by_id
        )
        self.create_action_with_target(
            'interrupt-kernel',
            GLib.VariantType.new("s"),
            self.interrupt_kernel_by_id
        )
        self.create_action_with_target(
            'restart-kernel',
            GLib.VariantType.new("s"),
            self.restart_kernel_by_id
        )

        self.create_action('restart-kernel-and-run', self.restart_kernel_and_run)
        self.create_action('start-server', self.start_server)

        self.create_action('open-notebook', self.open_notebook)

        self.create_action('new-browser-page', self.open_browser_page)

        self.command_line = CommandLine()

        self.previously_presented_widget = None

        widget = Panel.Widget()
        self.grid.add(widget)
        widget.close()

    #
    #   NEW NOTEBOOK PAGE WITH KERNEL NAME
    #

    def on_new_notebook_action(self, action, variant):
        asyncio.create_task(self.__on_new_notebook_action(variant.get_string()))

    async def __on_new_notebook_action(self, kernel_name):
        notebook = Notebook(name="Untitled.ipynb")

        notebook_page = NotebookPage(notebook)
        notebook_page.connect("presented", self.on_widget_presented)
        self.grid.add(notebook_page)

        success, kernel = await self.jupyter_server.start_kernel_by_name(kernel_name)

        if success:
            notebook_page.set_kernel(kernel)

    #
    #   NEW CONSOLE PAGE WITH KERNEL NAME
    #

    def on_new_console_action(self, action, variant):
        asyncio.create_task(self.__on_new_console_action(variant.get_string()))

    async def __on_new_console_action(self, kernel_name):
        console = ConsolePage()

        self.grid.add(console)

        success, kernel = await self.jupyter_server.start_kernel_by_name(kernel_name)

        if success:
            console.set_kernel(kernel)

    #
    #   NEW CODE PAGE WITH KERNEL NAME
    #

    def on_new_code_action(self, action, variant):
        asyncio.create_task(self.__on_new_code_action(variant.get_string()))

    async def __on_new_code_action(self, kernel_name):
        code = CodePage()

        self.grid.add(code)

        success, kernel = await self.jupyter_server.start_kernel_by_name(kernel_name)

        if success:
            code.set_kernel(kernel)

    #
    #   START SERVER
    #

    def start_server(self, *args):
        self.jupyter_server.start()

    #
    #   SHUTDOWN KERNEL
    #

    def shutdown_kernel_by_id(self, action, variant):
        asyncio.create_task(self.__shutdown_kernel_by_id(variant.get_string()))

    async def __shutdown_kernel_by_id(self, kernel_id):
        choice = await dialog_choose_async(self, self.shutdown_kernel_dialog)

        if choice == 'shutdown':
            success = await self.jupyter_server.shutdown_kernel(kernel_id)
            if success:
                print("kernel has shut down")
            else:
                print("kernel has NOT shut down")

    #
    #   RESTART_KERNEL
    #

    def restart_kernel_by_id(self, action, variant):
        asyncio.create_task(self.__restart_kernel_by_id(variant.get_string()))

    async def __restart_kernel_by_id(self, kernel_id):
        choice = await dialog_choose_async(self, self.restart_kernel_dialog)

        if choice == 'restart':
            success = await self.jupyter_server.restart_kernel(kernel_id)
            if success:
                print("kernel has restarted")
            else:
                print("kernel has NOT restarted")

    #
    #   INTERRUPT KERNEL
    #

    def interrupt_kernel_by_id(self, action, variant):
        asyncio.create_task(self.__restart_kernel_by_id(variant.get_string()))

    def __interrupt_kernel_by_id(self, kernel_id):
        success = self.jupyter_server.interrupt_kernel(kernel_id)
        if success:
            print("kernel has been interrupted")
        else:
            print("kernel has NOT been interrupted")

    #
    #
    #

    def add_cell_to_selected_notebook(self, cell):
        notebook = self.get_selected_notebook()
        notebook.add_cell(cell)

    def run_selected_cell(self, *args):
        notebook = self.get_selected_notebook()
        notebook.run_selected_cell()

    def on_jupyter_server_started(self, server):
        self.server_status_label.set_label(_("Server Connected"))

    def on_jupyter_server_has_new_line(self, server, line):
        self.terminal.feed([ord(char) for char in line + "\r\n"])

    def restart_kernel_and_run(self, *args):
        notebook = self.get_selected_notebook()
        kernel_id = notebook.notebook_model.jupyter_kernel.kernel_id
        self.restart_kernel_by_id(
            kernel_id,
            lambda: notebook.run_all_cells()
        )

    def get_selected_notebook(self):
        try:
            return self.grid.get_most_recent_frame().get_visible_child()

        except Exception as e:
            logging.Logger.debug(f"{e}")

    def create_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        return action

    def create_action_with_target(self, name, target_type, callback):
        action = Gio.SimpleAction.new(name, target_type)
        action.connect("activate", callback)
        self.add_action(action)
        return action

    def open_browser_page(self, *args):
        page = BrowserPage()
        self.grid.add(page)

    def open_notebook(self, *args):
        file_filter = Gtk.FileFilter(name=_("All supported formats"))
        file_filter.add_pattern("*.ipynb")
        filter_list = Gio.ListStore.new(Gtk.FileFilter())
        filter_list.append(file_filter)

        dialog = Gtk.FileDialog(
            title=_("Open File"),
            filters=filter_list,
        )

        dialog.open(self, None, self.on_open_notebook_response)

    def on_open_notebook_response(self, dialog, response):
        file_path = dialog.open_finish(response)

        with open(file_path, 'r') as file:
            file_content = file.read()
            notebook_node = nbformat.reads(file_content, as_version=4)

            notebook = Notebook.new_from_json(notebook_node)
            notebook.name = os.path.basename(file_path)

            self.add_notebook_page(notebook, "python3")

    def add_notebook_page(self, notebook, kernel_name):
        widget = Panel.Widget(
            icon_name="python-symbolic",
            title=notebook.name
        )
        widget.connect("presented", self.on_widget_presented)
        save_delegate = Panel.SaveDelegate()
        widget.set_save_delegate(save_delegate)
        widget.set_child(NotebookPage(notebook))
        self.grid.add(widget)

    def on_widget_presented(self, widget):
        widget = widget.get_child()

        if isinstance(self.previously_presented_widget, NotebookPage):
            self.previously_presented_widget.disconnect_by_func(self.on_kernel_info_changed)

        if isinstance(widget, NotebookPage):
            widget.connect("kernel-info-changed", self.on_kernel_info_changed)
            self.set_kernel_info(widget.kernel_name, widget.kernel_status)

        self.previously_presented_widget = widget

    def on_kernel_info_changed(self, notebook_page, kernel_name, status):
        self.set_kernel_info(kernel_name, status)

    def set_kernel_info(self, kernel_name, status):
        self.kernel_status_menu.set_label(status)
        self.omni_label.set_label(kernel_name or "No Kernel")

    @Gtk.Template.Callback("on_create_frame")
    def on_create_frame(self, grid):
        new_frame = Panel.Frame()
        new_frame.set_placeholder(Launcher(self.jupyter_server.avalaible_kernels))
        tab_bar = Panel.FrameTabBar()
        new_frame.set_header(tab_bar)

        return new_frame

    @Gtk.Template.Callback("on_key_pressed")
    def on_key_pressed(self, controller, keyval, keycode, state):
        print(keyval, keycode, state)

