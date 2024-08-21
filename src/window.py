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
from .jupyter_kernel import JupyterKernel, JupyterKernelInfo
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

        root_model = Gio.ListStore()
        root_model.append(self.jupyter_server.avalaible_kernels)
        root_model.append(self.jupyter_server.kernels)

        self.all_kernels = Gtk.TreeListModel.new(root_model, False, True, self.create_sub_models)

        self.select_kernel_combo_row.set_model(self.all_kernels)

        self.jupyter_server.start()

        self.terminal.set_color_background(Gdk.RGBA(alpha=1))

        #
        #   NEW CELL ON VISIBLE NOTEBOOK
        #

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

        #
        #   NEW NOTEBOOK/CONSOLE/CODE WITH NEW KERNEL BY NAME
        #
        #   if name is empty it will start the default kernel
        #

        self.create_action_with_target(
            'new-notebook-name',
            GLib.VariantType.new("s"),
            self.on_new_notebook_action
        )

        self.create_action_with_target(
            'new-console-name',
            GLib.VariantType.new("s"),
            self.on_new_console_action
        )

        self.create_action_with_target(
            'new-code-name',
            GLib.VariantType.new("s"),
            self.on_new_code_action
        )

        #
        #   NEW NOTEBOOK/CONSOLE/CODE WITH EXISTING KERNEL BY ID
        #

        self.create_action_with_target(
            'new-notebook-id',
            GLib.VariantType.new("s"),
            self.on_new_notebook_action
        )

        self.create_action_with_target(
            'new-console-id',
            GLib.VariantType.new("s"),
            self.on_new_console_action
        )

        self.create_action_with_target(
            'new-code-id',
            GLib.VariantType.new("s"),
            self.on_new_code_action
        )

        #
        #   OPERATION ON RUNNING KERNEL
        #

        self.create_action_with_target(
            'shutdown-kernel-id',
            GLib.VariantType.new("s"),
            self.shutdown_kernel_by_id
        )
        self.create_action_with_target(
            'interrupt-kernel-id',
            GLib.VariantType.new("s"),
            self.interrupt_kernel_by_id
        )
        self.create_action_with_target(
            'restart-kernel-id',
            GLib.VariantType.new("s"),
            self.restart_kernel_by_id
        )

        #
        #   ACTIONS FOR THE VIEWED NOTEBOOK/CODE/CONSOLE
        #

        self.create_action('run-selected-cell', self.run_selected_cell)
        self.create_action('restart-kernel-and-run', self.restart_kernel_and_run)
        self.create_action('start-server-visible', self.start_server)
        self.create_action('change-kernel', self.change_kernel)
        self.create_action('restart-kernel-visible', self.restart_kernel)

        #
        #   OTHER ACTIONS
        #

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

    def change_kernel(self, action, target):
        notebook = self.get_selected_notebook()
        asyncio.create_task(self.__change_kernel(notebook))

    async def __change_kernel(self, notebook):
        self.select_kernel_combo_row.set_selected(1) # 2 + len of avalab kernels + pos in kernels

        choice = await dialog_choose_async(self, self.select_kernel_dialog)

        kernel = self.select_kernel_combo_row.get_selected_item().get_item()
        print(kernel, choice)

        if choice == 'select':
            if isinstance(kernel, JupyterKernelInfo):
                success, new_kernel = await self.jupyter_server.start_kernel_by_name(kernel.name)
                if success:
                    print("kernel has restarted")
                    notebook.set_kernel(new_kernel)
                else:
                    print("kernel has NOT restarted")
            elif isinstance(kernel, JupyterKernel):
                notebook.set_kernel(kernel)
                print("kernel changed")

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

    def restart_kernel(self, *args):
        notebook = self.get_selected_notebook()
        if notebook:
            kernel_id = notebook.notebook_model.jupyter_kernel.kernel_id
            self.restart_kernel_by_id(
                kernel_id,
                lambda: notebook.run_all_cells()
            )

    def restart_kernel_and_run(self, *args):
        notebook = self.get_selected_notebook()
        if notebook:
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

    #
    #
    #

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
        asyncio.create_task(self.__open_notebook_file())

    async def __open_notebook_file(self):
        file_filter = Gtk.FileFilter(name=_("All supported formats"))
        file_filter.add_pattern("*.ipynb")
        filter_list = Gio.ListStore.new(Gtk.FileFilter())
        filter_list.append(file_filter)

        dialog = Gtk.FileDialog(
            title=_("Open File"),
            filters=filter_list,
        )

        file_path = await dialog.open(self)

        with open(file_path, 'r') as file:
            file_content = file.read()
            notebook_node = nbformat.reads(file_content, as_version=4)

            notebook = Notebook.new_from_json(notebook_node)
            notebook.name = os.path.basename(file_path)

            notebook_page = NotebookPage(notebook)
            notebook_page.connect("presented", self.on_widget_presented)
            self.grid.add(notebook_page)

            success, kernel = await self.jupyter_server.start_kernel_by_name("")

            if success:
                notebook_page.set_kernel(kernel)

    def on_widget_presented(self, widget):

        if isinstance(self.previously_presented_widget, NotebookPage):
            self.previously_presented_widget.disconnect_by_func(self.update_kernel_info)

        if isinstance(widget, NotebookPage):
            widget.connect("kernel-info-changed", self.update_kernel_info)
            self.update_kernel_info(widget)

        self.previously_presented_widget = widget

    def update_kernel_info(self, notebook_page):
        kernel = notebook_page.notebook_model.jupyter_kernel
        if kernel:
            self.kernel_status_menu.set_label(kernel.status)
            self.omni_label.set_label(kernel.name)
        else:
            self.kernel_status_menu.set_label("")
            self.omni_label.set_label("No Kernel")

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

    def create_sub_models(self, item):
        if isinstance(item, Gio.ListStore):
            return item
        return None

    @Gtk.Template.Callback("on_select_kernel_setup")
    def on_select_kernel_setup(self, factory, list_item):
        list_item.set_child(
            Gtk.Label(
                xalign=0,
                margin_top=6,
                margin_bottom=6,
                margin_start=6,
                margin_end=6
            )
        )

    @Gtk.Template.Callback("on_select_kernel_bind")
    def on_select_kernel_bind(self, factory, list_item):
        item = list_item.get_item().get_item()
        widget = list_item.get_child()

        print("bind")

        if isinstance(item, JupyterKernelInfo):
            widget.set_label(item.display_name)

        elif isinstance(item, JupyterKernel):
            widget.set_label(item.display_name)

        else:
            widget.set_label("Running Kernels")
            list_item.set_selectable(False)
            list_item.set_activatable(False)
            list_item.set_focusable(False)

        # widget.set_label(item.display_name)
