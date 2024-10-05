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
import logging
import asyncio

from .utils.async_helpers import dialog_choose_async

from .backend.jupyter_server import JupyterServer
from .backend.jupyter_kernel import JupyterKernel, JupyterKernelInfo
from .backend.command_line import CommandLine

from .models.cell import Cell, CellType
from .models.notebook import Notebook
from .models.multi_list_model import MultiListModel

from .pages.notebook_page import NotebookPage
from .pages.browser_page import BrowserPage
from .pages.console_page import ConsolePage
from .pages.code_page import CodePage
from .pages.json_viewer_page import JsonViewerPage
from .pages.text_page import TextPage
from .pages.matrix_page import MatrixPage

from .widgets.kernel_manager_view import KernelManagerView
from .widgets.workspace_view import WorkspaceView
from .widgets.variables_view import VariablesPanel
from .widgets.images_panel import ImagesPanel
from .widgets.launcher import Launcher

from .utils.converters import is_mime_displayable

from gettext import gettext as _


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
    quit_dialog = Gtk.Template.Child()
    select_kernel_combo_row = Gtk.Template.Child()
    omni_label = Gtk.Template.Child()
    server_status_label = Gtk.Template.Child()
    start_sidebar_panel_frame = Gtk.Template.Child()
    bottom_panel_frame = Gtk.Template.Child()
    language_label = Gtk.Template.Child()
    position_menu_button = Gtk.Template.Child()
    add_cell_button = Gtk.Template.Child()

    cache_dir = os.environ["XDG_CACHE_HOME"]
    files_cache_dir = os.path.join(cache_dir, "files")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Gio.Subprocess.new(
        #     ['pylsp', '--tcp', '--host', '127.0.0.1', '--port', '2087'],
        #     Gio.SubprocessFlags.NONE
        # )

        self.connect("notify::focus-widget", self.on_focus_changed)

        self.jupyter_server = JupyterServer()

        self.jupyter_server.connect(
            "started", self.on_jupyter_server_started)
        self.jupyter_server.connect(
            "new-line", self.on_jupyter_server_has_new_line)

        #
        #   ADDING AND BINDING STATIC PANELS
        #

        # TODO Save the last position and restore it at startup

        self.kernel_manager_view = KernelManagerView(
            self.jupyter_server.avalaible_kernels,
            self.jupyter_server.kernels
        )
        self.start_sidebar_panel_frame.add(self.kernel_manager_view)

        self.workspace_view = WorkspaceView()
        self.start_sidebar_panel_frame.add(self.workspace_view)

        self.variables_panel = VariablesPanel()
        self.bottom_panel_frame.add(self.variables_panel)

        self.images_panel = ImagesPanel()
        self.bottom_panel_frame.add(self.images_panel)

        # TODO Fix MultiListModel because it crashes when displaying
        #           the combo_row
        self.all_kernels = MultiListModel()
        self.all_kernels.add_section(
            self.jupyter_server.avalaible_kernels,
            _("Avaliable Kernels")
        )
        self.all_kernels.add_section(
            self.jupyter_server.kernels,
            _("Running Kernels")
        )

        self.select_kernel_combo_row.set_model(self.all_kernels)

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
        #   NEW BROWSER PAGE
        #

        self.create_action_with_target(
            'new-browser-page',
            GLib.VariantType.new("s"),
            self.open_browser_page
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
            self.on_new_notebook_id_action
        )

        self.create_action_with_target(
            'new-console-id',
            GLib.VariantType.new("s"),
            self.on_new_console_id_action
        )

        self.create_action_with_target(
            'new-code-id',
            GLib.VariantType.new("s"),
            self.on_new_code_id_action
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

        self.run_action = self.create_action(
            'run-selected-cell', self.run_clicked)
        self.restart_kernel_and_run_action = self.create_action(
            'restart-kernel-and-run', self.restart_kernel_and_run)
        self.create_action(
            'start-server', self.start_server)
        self.create_action(
            'change-kernel', self.change_kernel)
        self.restart_kernel_action = self.create_action(
            'restart-kernel-visible', self.restart_kernel_visible)

        #
        #   OTHER ACTIONS
        #

        self.create_action(
            'open-notebook', self.open_notebook)
        self.create_action(
            'open-workspace', self.workspace_view.set_workspace_folder)

        self.create_action_with_target(
            'open-file',
            GLib.VariantType.new("s"),
            self.open_file
        )

        self.create_action_with_target(
            'open-file-with-text',
            GLib.VariantType.new("s"),
            self.open_file_with_text
        )

        self.command_line = CommandLine()

        self.previous_page = None

        # Hack to get the launcher to show

        widget = Panel.Widget()
        self.grid.add(widget)
        widget.close()

        # Style Manager to update when dark/light

        self.style_manager = Adw.StyleManager.get_default()
        self.style_manager.connect("notify::dark", self.update_style_scheme)
        self.update_style_scheme()

        # Load examples folder

        self.home_folder = GLib.getenv('XDG_DATA_HOME')
        self.example_folder = GLib.build_filenamev(
            [self.home_folder, 'examples'])

        if os.path.exists(self.example_folder):
            for file_name in os.listdir(self.example_folder):
                file_path = os.path.join(self.example_folder, file_name)

                print(f"File: {file_name}, Path: {file_path}")
        else:
            print("The example folder does not exist.")

    #
    #   NEW NOTEBOOK PAGE WITH KERNEL NAME
    #

    def on_new_notebook_action(self, action, variant):
        asyncio.create_task(
            self._on_new_notebook_action(variant.get_string()))

    async def _on_new_notebook_action(self, kernel_name):
        notebook = Notebook()

        notebook_page = NotebookPage(notebook)
        notebook_page.set_draft()
        self.grid.add(notebook_page)

        success, kernel = await self.jupyter_server.start_kernel_by_name(
            kernel_name)

        if success:
            notebook_page.set_kernel(kernel)
            self.update_kernel_info(notebook_page)

    #
    #   NEW NOTEBOOK PAGE WITH EXISTING KERNEL FROM ID
    #

    def on_new_notebook_id_action(self, action, variant):
        asyncio.create_task(
            self._on_new_notebook_id_action(variant.get_string()))

    async def _on_new_notebook_id_action(self, kernel_id):
        notebook = Notebook()

        notebook_page = NotebookPage(notebook)
        notebook_page.set_draft()
        self.grid.add(notebook_page)

        success, kernel = self.jupyter_server.get_kernel_by_id(kernel_id)

        if success:
            notebook_page.set_kernel(kernel)
            self.update_kernel_info(notebook_page)

    #
    #   NEW CONSOLE PAGE WITH KERNEL NAME
    #

    def on_new_console_action(self, action, variant):
        asyncio.create_task(self._on_new_console_action(variant.get_string()))

    async def _on_new_console_action(self, kernel_name):
        console_page = ConsolePage()

        self.grid.add(console_page)

        success, kernel = await self.jupyter_server.start_kernel_by_name(
            kernel_name)

        if success:
            console_page.set_kernel(kernel)
            self.update_kernel_info(console_page)

    #
    #   NEW CONSOLE PAGE WITH EXISTING KERNEL FROM ID
    #

    def on_new_console_id_action(self, action, variant):
        asyncio.create_task(self._on_new_console_action(variant.get_string()))

    async def _on_new_console_id_action(self, kernel_id):
        console_page = ConsolePage()

        self.grid.add(console_page)

        success, kernel = self.jupyter_server.get_kernel_by_id(kernel_id)

        if success:
            console_page.set_kernel(kernel)
            self.update_kernel_info(console_page)

    #
    #   NEW CODE PAGE WITH KERNEL NAME
    #

    def on_new_code_action(self, action, variant):
        asyncio.create_task(self._on_new_code_action(variant.get_string()))

    async def _on_new_code_action(self, kernel_name):
        code_page = CodePage()

        self.grid.add(code_page)

        success, kernel = await self.jupyter_server.start_kernel_by_name(
            kernel_name)

        if success:
            code_page.set_kernel(kernel)
            self.update_kernel_info(code_page)

    #
    #   NEW CODE PAGE WITH EXISTING KERNEL FROM ID
    #

    def on_new_code_id_action(self, action, variant):
        asyncio.create_task(self._on_new_code_id_action(variant.get_string()))

    async def _on_new_code_id_action(self, kernel_id):
        code_page = CodePage()

        self.grid.add(code_page)

        success, kernel = self.jupyter_server.get_kernel_by_id(kernel_id)

        if success:
            code_page.set_kernel(kernel)
            self.update_kernel_info(code_page)

    #
    #   START SERVER
    #

    def start_server(self, *args):
        self.jupyter_server.start()

    #
    #   SHUTDOWN KERNEL
    #

    def shutdown_kernel_by_id(self, action, variant):
        asyncio.create_task(self._shutdown_kernel_by_id(variant.get_string()))

    async def _shutdown_kernel_by_id(self, kernel_id):
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
        asyncio.create_task(self._restart_kernel_by_id(variant.get_string()))

    async def _restart_kernel_by_id(self, kernel_id):
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
        asyncio.create_task(self._interrupt_kernel_by_id(variant.get_string()))

    def _interrupt_kernel_by_id(self, kernel_id):
        success = self.jupyter_server.interrupt_kernel(kernel_id)
        if success:
            print("kernel has been interrupted")
        else:
            print("kernel has NOT been interrupted")

    #
    #   RESTART VISIBLE KERNEL
    #

    def restart_kernel_visible(self, *args):
        kernel_id = self.get_visible_page().get_kernel().kernel_id
        self.activate_action(
            "win.restart-kernel-id", GLib.Variant('s', kernel_id))

    #
    #   RESTART VISIBLE KERNEL AND RUN ALL CELLS
    #

    def restart_kernel_and_run(self, *args):
        asyncio.create_task(self._restart_kernel_and_run())

    async def _restart_kernel_and_run(self):
        choice = await dialog_choose_async(self, self.restart_kernel_dialog)

        if choice == 'restart':
            notebook_page = self.get_visible_page()
            if isinstance(notebook_page, NotebookPage):
                kernel_id = notebook_page.get_kernel().kernel_id
            success = await self.jupyter_server.restart_kernel(kernel_id)
            if success:
                notebook_page.run_all_cells()
            else:
                print("kernel has NOT restarted")

    #
    #   SAVE VISIBLE PAGE
    #

    def save_viewed(self):
        page = self.get_visible_page()
        if page:
            page.get_save_delegate().save_async(
                None, self.on_saved_finished)

    def on_saved_finished(self, delegate, result):
        print("saved")

    #
    #   OPEN BROWSER PAGE WITH URL
    #

    def open_browser_page(self, action, variant):
        page = BrowserPage(variant.get_string())
        self.grid.add(page)

    #
    #   CREATE ACTIONS WITH OR WITHOUT TARGETS
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

    #
    #   OPEN FILES OR NOTEBOOKS
    #

    def open_notebook(self, *args):
        asyncio.create_task(self.__open_notebook_file())

    async def __open_notebook_file(self):
        file_filter = Gtk.FileFilter(name="All supported formats")
        file_filter.add_pattern("*.ipynb")
        filter_list = Gio.ListStore.new(Gtk.FileFilter())
        filter_list.append(file_filter)

        dialog = Gtk.FileDialog(
            title="Open File",
            filters=filter_list,
        )

        file_path = await dialog.open(self)

        notebook = Notebook.new_from_file(file_path)

        notebook_page = NotebookPage(notebook)
        self.grid.add(notebook_page)

        success, kernel = await self.jupyter_server.start_kernel_by_name("")

        if success:
            notebook_page.set_kernel(kernel)
            self.update_kernel_info(notebook_page)

    def open_file(self, action, variant):
        file_path = variant.get_string()

        gfile = Gio.File.new_for_path(file_path)

        file_info = gfile.query_info("standard::content-type", 0, None)
        mime_type = file_info.get_content_type()

        print(mime_type)

        match mime_type:
            case "application/json":
                self.grid.add(JsonViewerPage(file_path))
            case "text/csv":
                self.grid.add(MatrixPage(file_path))
            case "application/x-ipynb+json":
                notebook = Notebook.new_from_file(file_path)
                notebook_page = NotebookPage(notebook)
                self.grid.add(notebook_page)
            case mime_type if is_mime_displayable(mime_type):
                self.grid.add(TextPage(file_path))
            case _:
                try:
                    file = Gio.File.new_for_path(file_path)
                except GLib.GError:
                    print("Failed to construct a new Gio.File object.")
                else:
                    launcher = Gtk.FileLauncher.new(file)
                    launcher.set_always_ask(True)

                    launcher.launch(self, None, None)

    def open_file_with_text(self, action, variant):
        file_path = variant.get_string()

        gfile = Gio.File.new_for_path(file_path)

        file_info = gfile.query_info("standard::content-type", 0, None)
        mime_type = file_info.get_content_type()

        if is_mime_displayable(mime_type):
            self.grid.add(TextPage(file_path))

    #
    #   CONNECT STATIC UI TO VISIBLE PAGE PROPERTIES
    #

    def on_focus_changed(self, *args):
        page = self.get_visible_page()

        if (isinstance(page, NotebookPage) or
                isinstance(page, ConsolePage) or
                isinstance(page, CodePage)):

            if self.previous_page:
                self.previous_page.disconnect_by_func(self.update_kernel_info)
                self.previous_page.disconnect_by_func(self.on_cursor_moved)

            page.connect("kernel-info-changed", self.update_kernel_info)
            self.update_kernel_info(page)
            page.connect("cursor-moved", self.on_cursor_moved)
            self.previous_page = page

            self.omni_bar.set_visible(True)
            self.language_label.set_visible(True)

            if isinstance(page, NotebookPage):
                self.add_cell_button.set_visible(True)
            else:
                self.add_cell_button.set_visible(False)
        else:
            self.position_menu_button.set_visible(False)
            self.language_label.set_visible(False)
            self.omni_bar.set_visible(False)

    def update_kernel_info(self, page):
        kernel = page.get_kernel()
        if kernel:
            self.kernel_status_menu.set_label(kernel.status)
            self.omni_label.set_label(kernel.display_name)
            self.language_label.set_label(kernel.language.title() or "None")

            self.variables_panel.set_model(kernel.get_variables())

            self.run_action.set_enabled(True)
            self.restart_kernel_and_run_action.set_enabled(True)
            self.restart_kernel_action.set_enabled(True)
        else:
            self.kernel_status_menu.set_label("")
            self.omni_label.set_label("No Kernel")

            self.variables_panel.set_model(None)

            self.run_action.set_enabled(False)
            self.restart_kernel_and_run_action.set_enabled(False)
            self.restart_kernel_action.set_enabled(False)

    def on_cursor_moved(self, page, buffer, index):
        insert_mark = buffer.get_insert()
        iter_at_cursor = buffer.get_iter_at_mark(insert_mark)
        line_n = iter_at_cursor.get_line()
        column_n = iter_at_cursor.get_line_offset()

        # Used to indicate the line and column number
        position = _("Ln ") + str(line_n) + _(", Col ") + str(column_n)

        if index == 0:

            self.position_menu_button.set_label(position)
        else:
            # Used to indicate the focused cell
            position = _("Cell ") + str(index) + ", " + position
            self.position_menu_button.set_label(position)

        self.position_menu_button.set_visible(True)

    #
    #   CHANGE/SELECT KERNEL TO VISIBLE PAGE
    #

    def change_kernel(self, action, target):
        notebook = self.get_visible_page()
        asyncio.create_task(self._change_kernel(notebook))

    async def _change_kernel(self, notebook):
        self.select_kernel_combo_row.set_selected(1)
        # 2 + len of avalab kernels + pos in kernels

        choice = await dialog_choose_async(self, self.select_kernel_dialog)

        if choice == 'select':

            kernel = self.select_kernel_combo_row.get_selected_item()

            if isinstance(kernel, JupyterKernelInfo):
                success, new_kernel = await self.jupyter_server.start_kernel_by_name(kernel.name)
                if success:
                    print("kernel has restarted")
                    notebook.set_kernel(new_kernel)
                    self.update_kernel_info(notebook)
                else:
                    print("kernel has NOT restarted")
            elif isinstance(kernel, JupyterKernel):
                notebook.set_kernel(kernel)
                self.update_kernel_info(notebook)
                print("kernel changed")

    #
    #   CHARGE/SELECT KERNEL ALERT DIALOG LIST VIEW
    #

    def create_sub_models(self, item):
        if isinstance(item, Gio.ListStore):
            return item
        return None

    @Gtk.Template.Callback("on_select_kernel_header_setup")
    def on_select_kernel_header_setup(self, factory, list_item):
        list_item.set_child(
            Gtk.Label(
                xalign=0,
                margin_start=6,
                margin_end=6
            )
        )

    @Gtk.Template.Callback("on_select_kernel_header_bind")
    def on_select_kernel_header_bind(self, factory, list_item):
        item = list_item.get_item()
        label = list_item.get_child()

        print("HEADER ", item)

        # FIXME It would be better to have a way to get the name stored
        #           in the MultiListModel
        if isinstance(item, JupyterKernelInfo):
            label.set_label(_("Avalaible Kernels"))
        elif isinstance(item, JupyterKernel):
            label.set_label(_("Running Kernels"))

    @Gtk.Template.Callback("on_select_kernel_setup")
    def on_select_kernel_setup(self, factory, list_item):
        list_item.set_child(
            Gtk.Label(
                xalign=0,
                margin_start=6,
                margin_end=6
            )
        )

    @Gtk.Template.Callback("on_select_kernel_bind")
    def on_select_kernel_bind(self, factory, list_item):
        item = list_item.get_item()
        label = list_item.get_child()

        label.set_label(item.display_name)

    #
    #   CLOSE
    #

    def close(self):
        if self.jupyter_server.get_is_running():
            asyncio.create_task(self._quit())
            return True
        else:
            return False

    async def _quit(self):
        choice = await dialog_choose_async(self, self.quit_dialog)

        if choice == 'quit':
            self.jupyter_server.stop()

            self.activate_action("app.quit")

    #
    #   VARIOUS
    #

    def add_cell_to_selected_notebook(self, cell):
        page = self.get_visible_page()
        if isinstance(page, NotebookPage):
            page.add_cell(cell)

        print(page.notebook_model)

    def run_clicked(self, *args):
        notebook = self.get_visible_page()
        notebook.run_selected_cell()

    def on_jupyter_server_started(self, server):
        self.server_status_label.set_label("Server Connected")

    def on_jupyter_server_has_new_line(self, server, line):
        self.terminal.feed([ord(char) for char in line + "\r\n"])

    def get_visible_page(self):
        try:
            return self.grid.get_most_recent_frame().get_visible_child()

        except Exception as e:
            logging.Logger.debug(f"{e}")

    def update_style_scheme(self, *args):
        background = Gdk.RGBA()
        foreground = Gdk.RGBA()

        background.parse('rgba(0, 0, 0, 0)')

        if Adw.StyleManager.get_default().get_dark():
            foreground.parse('#ffffff')
        else:
            foreground.parse('rgba(0, 0, 0, 0.8)')

        self.terminal.set_color_background(background)
        self.terminal.set_color_foreground(foreground)

    @Gtk.Template.Callback("on_create_frame")
    def on_create_frame(self, grid):
        new_frame = Panel.Frame()
        new_frame.set_placeholder(
            Launcher(self.jupyter_server.avalaible_kernels))
        tab_bar = Panel.FrameTabBar()
        new_frame.set_header(tab_bar)

        new_frame.connect("page-closed", self.on_page_closed)

        return new_frame

    def on_page_closed(self, frame, widget):
        if widget == self.previous_page:
            widget.disconnect_by_func(self.update_kernel_info)
            widget.disconnect_by_func(self.on_cursor_moved)

            self.previous_page = None

    @Gtk.Template.Callback("on_key_pressed")
    def on_key_pressed(self, controller, keyval, keycode, state):
        print(keyval, keycode, state)
