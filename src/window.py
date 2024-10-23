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
from gi.repository import Gio, Gdk
from gi.repository import Panel, GObject

import os
import logging
import asyncio
import re

from .utils.async_helpers import dialog_choose_async

from .backend.jupyter_server import JupyterServer
from .backend.jupyter_kernel import JupyterKernel, JupyterKernelInfo
from .backend.command_line import CommandLine

from .models.cell import CellType
from .models.multi_list_model import MultiListModel

from .pages.notebook_page import NotebookPage
from .pages.browser_page import BrowserPage
from .pages.console_page import ConsolePage
from .pages.code_page import CodePage
from .pages.json_viewer_page import JsonViewerPage
from .pages.text_page import TextPage
from .pages.matrix_page import MatrixPage

from .panels.kernel_manager_panel import KernelManagerPanel
from .panels.workspace_panel import WorkspacePanel
from .panels.variables_panel import VariablesPanel
from .panels.images_panel import ImagesPanel
from .panels.terminal_panel import TerminalPanel
from .panels.kernel_terminal_panel import KernelTerminalPanel

from .interfaces.kernel import IKernel
from .interfaces.cells import ICells
from .interfaces.saveable import ISaveable
from .interfaces.disconnectable import IDisconnectable
from .interfaces.cursor import ICursor
from .interfaces.language import ILanguage

from .widgets.launcher import Launcher
from .widgets.chapter_row import ChapterRow

from .utils.converters import is_mime_displayable

from gettext import gettext as _


class TreeNode(GObject.Object):
    def __init__(self, node_name, index, children=None):
        super().__init__()
        self.node_name = node_name
        self.index = index
        self.children = children or []


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/window.ui')
class PlanetnineWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'PlanetnineWindow'

    server_terminal = Gtk.Template.Child()
    kernel_terminal = Gtk.Template.Child()
    panel_grid = Gtk.Template.Child()
    kernel_controls = Gtk.Template.Child()
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
    language_button = Gtk.Template.Child()
    position_menu_button = Gtk.Template.Child()
    add_cell_button = Gtk.Template.Child()
    move_cursor_entry_buffer = Gtk.Template.Child()
    notebook_navigation_menu = Gtk.Template.Child()
    chapters_list_view = Gtk.Template.Child()

    cache_dir = os.environ["XDG_CACHE_HOME"]
    files_cache_dir = os.path.join(cache_dir, "files")

    images_path = os.path.join(cache_dir, "g_images")
    html_path = os.path.join(cache_dir, "g_html")

    os.makedirs(images_path, exist_ok=True)
    os.makedirs(html_path, exist_ok=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Gio.Subprocess.new(
        #     ['pylsp', '--tcp', '--host', '127.0.0.1', '--port', '2087'],
        #     Gio.SubprocessFlags.NONE
        # )

        self.connect_after("notify::focus-widget", self.on_focus_changed)

        self.jupyter_server = JupyterServer()

        self.jupyter_server.connect(
            "started", self.on_jupyter_server_started)
        self.jupyter_server.connect(
            "new-line", self.on_jupyter_server_has_new_line)

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

        #   ADDING AND BINDING STATIC PANELS

        # TODO Save the arrangement of the panels and restore it at startup

        self.kernel_manager_panel = KernelManagerPanel(
            self.jupyter_server.avalaible_kernels,
            self.jupyter_server.kernels
        )
        self.start_sidebar_panel_frame.add(self.kernel_manager_panel)

        self.workspace_view = WorkspacePanel()
        self.start_sidebar_panel_frame.add(self.workspace_view)

        self.variables_panel = VariablesPanel()
        self.bottom_panel_frame.add(self.variables_panel)

        self.images_panel = ImagesPanel()
        self.bottom_panel_frame.add(self.images_panel)

        self.all_kernels = MultiListModel()
        self.all_kernels.add_section(
            self.jupyter_server.avalaible_kernels,
            _("Avaliable Kernels"))
        self.all_kernels.add_section(
            self.jupyter_server.kernels,
            _("Running Kernels"))

        self.select_kernel_combo_row.set_model(self.all_kernels)

        #   NEW CELL ON VISIBLE NOTEBOOK

        self.create_action(
            'add-text-cell',
            lambda *_: self.add_cell_to_page(CellType.TEXT))
        self.create_action(
            'add-code-cell',
            lambda *_: self.add_cell_to_page(CellType.CODE))
        self.create_action(
            'add-raw-cell',
            lambda *_: self.add_cell_to_page(CellType.TEXT))

        #   NEW BROWSER PAGE

        self.create_action_with_target(
            'new-browser-page',
            GLib.VariantType.new("s"),
            self.open_browser_page)

        #   NEW NOTEBOOK/CONSOLE/CODE WITH NEW KERNEL BY NAME
        #   if name is empty it will start the default kernel

        self.create_action_with_target(
            'new-notebook-name',
            GLib.VariantType.new("s"),
            self.on_new_notebook_action)

        self.create_action_with_target(
            'new-console-name',
            GLib.VariantType.new("s"),
            self.on_new_console_action)

        self.create_action_with_target(
            'new-code-name',
            GLib.VariantType.new("s"),
            self.on_new_code_action)

        #   NEW NOTEBOOK/CONSOLE/CODE WITH EXISTING KERNEL BY ID

        self.create_action_with_target(
            'new-notebook-id',
            GLib.VariantType.new("s"),
            self.on_new_notebook_id_action)

        self.create_action_with_target(
            'new-console-id',
            GLib.VariantType.new("s"),
            self.on_new_console_id_action)

        self.create_action_with_target(
            'new-code-id',
            GLib.VariantType.new("s"),
            self.on_new_code_id_action)

        #   OPERATION ON RUNNING KERNEL

        self.create_action_with_target(
            'shutdown-kernel-id',
            GLib.VariantType.new("s"),
            self.shutdown_kernel_by_id)

        self.create_action_with_target(
            'interrupt-kernel-id',
            GLib.VariantType.new("s"),
            self.interrupt_kernel_by_id)

        self.create_action_with_target(
            'restart-kernel-id',
            GLib.VariantType.new("s"),
            self.restart_kernel_by_id)

        #   ACTIONS FOR THE VIEWED NOTEBOOK/CODE/CONSOLE

        self.run_selected_action = self.create_action(
            'run-cell', self.on_run)
        self.run_cell_and_proceed_action = self.create_action(
            'run-cell-and-proceed', self.on_run_line)
        self.run_line_action = self.create_action(
            'run-line', self.on_run_line)
        self.restart_kernel_action = self.create_action(
            'restart-kernel-visible', self.restart_kernel_visible)
        self.restart_kernel_and_run_action = self.create_action(
            'restart-kernel-and-run', self.restart_kernel_and_run)
        self.change_kernel_action = self.create_action_with_target(
            'change-kernel',
            GLib.VariantType.new("s"),
            self.on_change_kernel_action)

        self.create_action_with_target(
            'select-cell',
            GLib.VariantType.new("u"),
            self.on_select_cell_action)

        self.run_cell_and_proceed_action.set_enabled(False)
        self.run_line_action.set_enabled(False)
        self.run_selected_action.set_enabled(False)
        self.restart_kernel_and_run_action.set_enabled(False)
        self.restart_kernel_action.set_enabled(False)
        self.change_kernel_action.set_enabled(False)

        #   OTHER ACTIONS

        self.create_action(
            'start-server', self.start_server)

        self.create_action(
            'open-notebook', self.on_open_notebook_action)
        self.create_action(
            'open-code', self.on_open_code_action)
        self.create_action(
            'open-workspace', self.workspace_view.set_workspace_folder)

        self.create_action_with_target(
            'open-file',
            GLib.VariantType.new("s"),
            self.on_open_file_action)

        self.create_action_with_target(
            'open-file-with-text',
            GLib.VariantType.new("s"),
            self.open_file_with_text)

        #   Action for IKernel pages to request kernel

        self.create_action_with_target(
            'request-kernel-id',
            GLib.VariantType.new("(ss)"),
            self.on_request_kernel_id)

        self.create_action_with_target(
            'request-kernel-name',
            GLib.VariantType.new("(ss)"),
            self.on_request_kernel_name)

        #

        self.command_line = CommandLine()

        self.previous_page = None

        # Hack to get the launcher to show

        widget = Panel.Widget()
        self.panel_grid.add(widget)
        widget.close()

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

        #   START SERVER IMMEDIATELY

        if self.settings.get_boolean("start-server-immediately"):
            self.jupyter_server.start()
            self.change_kernel_action.set_enabled(True)

    #
    #   NEW NOTEBOOK PAGE WITH KERNEL NAME
    #

    def on_new_notebook_action(self, action, variant):
        notebook_page = NotebookPage(None, kernel_name=variant.get_string())
        self.panel_grid.add(notebook_page)

    #
    #   NEW NOTEBOOK PAGE WITH EXISTING KERNEL FROM ID
    #

    def on_new_notebook_id_action(self, action, variant):
        notebook_page = NotebookPage(None, kernel_id=variant.get_string())
        self.panel_grid.add(notebook_page)

    #
    #   NEW CONSOLE PAGE WITH KERNEL NAME
    #

    def on_new_console_action(self, action, variant):
        console_page = ConsolePage(kernel_name=variant.get_string())
        self.panel_grid.add(console_page)

    #
    #   NEW CONSOLE PAGE WITH EXISTING KERNEL FROM ID
    #

    def on_new_console_id_action(self, action, variant):
        console_page = ConsolePage(kernel_id=variant.get_string())
        self.panel_grid.add(console_page)

    #
    #   NEW CODE PAGE WITH KERNEL NAME
    #

    def on_new_code_action(self, action, variant):
        code_page = CodePage(None, kernel_name=variant.get_string())
        self.panel_grid.add(code_page)

    #
    #   NEW CODE PAGE WITH EXISTING KERNEL FROM ID
    #

    def on_new_code_id_action(self, action, variant):
        code_page = CodePage(None, kernel_id=variant.get_string())
        self.panel_grid.add(code_page)

    #
    #   SET A NEW or EXISTING KERNEL TO A PAGE
    #

    def on_request_kernel_name(self, action, variant):
        page_id, kernel_name = variant.unpack()
        asyncio.create_task(self._on_request_kernel_name(page_id, kernel_name))

    async def _on_request_kernel_name(self, page_id, kernel_name):
        page = self.find_ikernel_page(page_id)
        if page:
            success, kernel = await self.jupyter_server.start_kernel_by_name(
                kernel_name)

            if success:
                page.set_kernel(kernel)
                self.update_kernel_info(page)

    def on_request_kernel_id(self, action, variant):
        page_id, kernel_id = variant.unpack()
        asyncio.create_task(self._on_request_kernel_id(page_id, kernel_id))

    async def _on_request_kernel_id(self, page_id, kernel_id):
        page = self.find_ikernel_page(page_id)
        if page:
            success, kernel = self.jupyter_server.get_kernel_by_id(
                kernel_id)

            if success:
                page.set_kernel(kernel)
                self.update_kernel_info(page)

    def find_ikernel_page(self, page_id):
        result = None

        def check_frame(frame):
            nonlocal result
            for adw_page in frame.get_pages():
                page = adw_page.get_child()
                if isinstance(page, IKernel):
                    if page.page_id == page_id:
                        result = page
                        return

        self.panel_grid.foreach_frame(check_frame)

        return result

    #
    #   START SERVER
    #

    def start_server(self, *args):
        self.jupyter_server.start()
        self.change_kernel_action.set_enabled(True)

    #
    #   SHUTDOWN KERNEL BY ID
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
    #   RESTART KERNEL BY ID
    #

    def restart_kernel_by_id(self, action, variant):
        asyncio.create_task(self._restart_kernel_by_id(variant.get_string()))

    async def _restart_kernel_by_id(self, kernel_id):
        choice = await dialog_choose_async(self, self.restart_kernel_dialog)

        if choice == 'restart':
            success = await self.jupyter_server.restart_kernel(kernel_id)
            if success:
                return True
            else:
                return False

        return False

    #
    #   INTERRUPT KERNEL  BY ID
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
        kernel_id = self.get_visible_page().get_kernel().kernel_id

        success = await self._restart_kernel_by_id(kernel_id)

        if success:
            self.get_visible_page().run_all_cells()

    #
    #   SAVE VISIBLE PAGE
    #

    def save_viewed(self):
        page = self.get_visible_page()
        if isinstance(page, ISaveable):
            page.get_save_delegate().save_async(
                None, self.on_saved_finished)

    def on_saved_finished(self, delegate, result):
        print("saved")

    #
    #   OPEN BROWSER PAGE WITH URL
    #

    def open_browser_page(self, action, variant):
        page = BrowserPage(variant.get_string())
        self.panel_grid.add(page)

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

    def on_open_notebook_action(self, *args):
        asyncio.create_task(self._on_open_notebook_action())

    async def _on_open_notebook_action(self):
        file_filter = Gtk.FileFilter(name=_("All supported formats"))
        file_filter.add_pattern("*.ipynb")
        filter_list = Gio.ListStore.new(Gtk.FileFilter())
        filter_list.append(file_filter)

        dialog = Gtk.FileDialog(
            title=_("Open File"),
            filters=filter_list,
        )
        try:
            file = await dialog.open(self)
            self.open_notebook(file.get_path())
        except Exception as e:
            print(e)

    def on_open_code_action(self, *args):
        asyncio.create_task(self._on_open_code_action())

    async def _on_open_code_action(self):
        file_filter = Gtk.FileFilter(name=_("All supported formats"))
        file_filter.add_pattern("*.py")
        filter_list = Gio.ListStore.new(Gtk.FileFilter())
        filter_list.append(file_filter)

        dialog = Gtk.FileDialog(
            title=_("Open File"),
            filters=filter_list,
        )

        try:
            file = await dialog.open(self)
            self.open_code(file.get_path())
        except Exception as e:
            print(e)

    #
    #   OPEN ANY FILE
    #

    def on_open_file_action(self, action, variant):
        file_path = variant.get_string()

        self.open_file(file_path)

    def open_file(self, file_path):
        if self.raise_page_if_open(file_path):
            return

        gfile = Gio.File.new_for_path(file_path)

        file_info = gfile.query_info("standard::content-type", 0, None)
        mime_type = file_info.get_content_type()

        match mime_type:
            case "application/json":
                self.panel_grid.add(JsonViewerPage(file_path))
            case "text/csv":
                self.panel_grid.add(MatrixPage(file_path))
            case "application/x-ipynb+json":
                self.panel_grid.add(NotebookPage(file_path))
            case "text/x-python":
                self.panel_grid.add(CodePage(file_path))
            case mime_type if is_mime_displayable(mime_type):
                self.panel_grid.add(TextPage(file_path))
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

        if self.raise_page_if_open(file_path):
            return

        self.panel_grid.add(TextPage(file_path))

    def open_notebook(self, file_path=None):
        self.panel_grid.add(NotebookPage(file_path))

    def open_code(self, file_path):
        self.panel_grid.add(CodePage(file_path))

    def raise_page_if_open(self, file_path):
        result = False

        def check_frame(frame):
            nonlocal result
            for adw_page in frame.get_pages():
                page = adw_page.get_child()
                if isinstance(page, ISaveable):
                    if page.get_path() == file_path:
                        result = True
                        frame.set_visible_child(page)
                        return

        self.panel_grid.foreach_frame(check_frame)

        return result

    def raise_page(self, rise_page):
        result = False

        def check_frame(frame):
            nonlocal result
            for adw_page in frame.get_pages():
                page = adw_page.get_child()
                if page == rise_page:
                    result = True
                    frame.set_visible_child(page)
                    return

        self.panel_grid.foreach_frame(check_frame)

        return result

    #
    #   CONNECT STATIC UI TO VISIBLE PAGE PROPERTIES
    #

    def on_focus_changed(self, *args):
        page = self.get_visible_page()

        self.disconnect_page_funcs(self.previous_page)

        # Kernel Interface (Notebook, Code, Console)
        if isinstance(page, IKernel):
            page.connect("kernel-info-changed", self.update_kernel_info)
            self.update_kernel_info(page)

            self.kernel_controls.set_visible(True)
            self.kernel_status_menu.set_visible(True)
        else:
            self.update_kernel_info(None)

            self.kernel_controls.set_visible(False)
            self.kernel_status_menu.set_visible(False)

        if isinstance(page, NotebookPage):
            self.notebook_navigation_menu.set_visible(True)
        else:
            self.notebook_navigation_menu.set_visible(False)

        # Language Interface (Text, Notebook, Code, Console, Json, Table)
        if isinstance(page, ILanguage):
            page.connect("language-changed", self.update_page_language)
            self.update_page_language(page)
            if page.get_is_language_settable():
                self.language_button.set_active(True)
            else:
                self.language_button.set_active(False)
            self.language_button.set_visible(True)
        else:
            self.language_button.set_visible(False)

        # Cursor Interface (Text, Notebook, Code, Console, Json, Table)
        if isinstance(page, ICursor):
            page.connect("cursor-moved", self.on_cursor_moved)
            buffer, index = page.get_cursor_position()
            self.on_cursor_moved(page, buffer, index)
            self.position_menu_button.set_visible(True)
        else:
            self.position_menu_button.set_visible(False)

        if isinstance(page, ICells):
            self.add_cell_button.set_visible(True)
        else:
            self.add_cell_button.set_visible(False)

        self.previous_page = page

    def update_kernel_info(self, page):
        if page:
            kernel = page.get_kernel()
            if kernel:
                self.kernel_status_menu.set_label(kernel.status)
                self.omni_label.set_label(kernel.display_name)

                self.variables_panel.set_model(kernel.get_variables())
                self.kernel_terminal.set_kernel(kernel)

                self.run_cell_and_proceed_action.set_enabled(True)
                self.run_line_action.set_enabled(True)
                self.run_selected_action.set_enabled(True)
                self.restart_kernel_and_run_action.set_enabled(True)
                self.restart_kernel_action.set_enabled(True)
        else:
            self.kernel_status_menu.set_label("")
            self.omni_label.set_label("No Kernel")

            self.variables_panel.set_model(None)
            self.kernel_terminal.set_kernel(None)

            self.run_cell_and_proceed_action.set_enabled(False)
            self.run_line_action.set_enabled(False)
            self.run_selected_action.set_enabled(False)
            self.restart_kernel_and_run_action.set_enabled(False)
            self.restart_kernel_action.set_enabled(False)

    def update_page_language(self, page):
        lang = page.get_language()
        if lang == "" or lang is None:
            lang = _("None")

        self.language_button.set_label(lang.title())

    def on_cursor_moved(self, page, buffer, index):
        if buffer is None:
            return
        insert_mark = buffer.get_insert()
        iter_at_cursor = buffer.get_iter_at_mark(insert_mark)
        line_n = iter_at_cursor.get_line()
        column_n = iter_at_cursor.get_line_offset()

        # Used to indicate the line and column number
        position = _("Ln ") + str(line_n) + _(", Col ") + str(column_n)

        entry_position = str(line_n) + ":" + str(column_n)

        if index == 0:
            self.position_menu_button.set_label(position)
            self.move_cursor_entry_buffer.set_text(
                entry_position, len(entry_position))
        else:
            # Used to indicate the focused cell
            position = _("Cell ") + str(index) + ", " + position
            self.position_menu_button.set_label(position)

            entry_position = str(index) + ":" + entry_position
            self.move_cursor_entry_buffer.set_text(
                entry_position, len(entry_position))

    def disconnect_page_funcs(self, page):
        if isinstance(page, IKernel):
            page.disconnect_by_func(self.update_kernel_info)
        if isinstance(page, ICursor):
            page.disconnect_by_func(self.on_cursor_moved)
        if isinstance(page, ILanguage):
            page.disconnect_by_func(self.update_page_language)

    #
    #   MOVE CURSOR
    #

    @Gtk.Template.Callback("on_move_cursor_activated")
    def on_move_cursor_activated(self, *args):
        page = self.get_visible_page()
        if isinstance(page, ICursor):
            text = self.move_cursor_entry_buffer.get_text()
            parts = text.split(":")
            print(parts)
            if len(parts) == 3:
                page.move_cursor(int(parts[1]), int(parts[2]), int(parts[0]))
            elif len(parts) == 2:
                page.move_cursor(int(parts[0]), int(parts[1]))

    #
    #   CHANGE/SELECT KERNEL OF A PAGE BY ID OR VISIBLE
    #

    def on_change_kernel_action(self, action, target):
        if target.get_string() == "":
            page = self.get_visible_page()
        else:
            page = self.find_ikernel_page(target.get_string())

        if page:
            asyncio.create_task(self._change_kernel(page))

    async def _change_kernel(self, page):
        self.select_kernel_combo_row.set_selected(0)
        # 2 + len of avalab kernels + pos in kernels

        self.raise_page(page)

        choice = await dialog_choose_async(self, self.select_kernel_dialog)

        if choice == 'select':

            kernel = self.select_kernel_combo_row.get_selected_item()

            if isinstance(kernel, JupyterKernelInfo):
                succ, new_ker = await self.jupyter_server.start_kernel_by_name(
                    kernel.name)
                if succ:
                    print("kernel has restarted")
                    page.set_kernel(new_ker)
                    self.update_kernel_info(page)
                else:
                    print("kernel has NOT restarted")
            elif isinstance(kernel, JupyterKernel):
                page.set_kernel(kernel)
                self.update_kernel_info(page)
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
        self.panel_grid.agree_to_close_async(None, self.finish_close)
        return True

    def finish_close(self, _grid, result):
        try:
            success = self.panel_grid.agree_to_close_finish(result)
            print("RESULT: ", success)
            if success:
                asyncio.create_task(self._quit())
        except Exception as e:
            print(e)

    async def _quit(self):
        if self.jupyter_server.get_is_running():
            choice = await dialog_choose_async(self, self.quit_dialog)

            if choice == 'quit':
                self.jupyter_server.stop()
            else:
                return

        self.activate_action("app.quit")

    #
    #   VARIOUS
    #

    def add_cell_to_page(self, cell_type):
        page = self.get_visible_page()
        if isinstance(page, ICells):
            page.add_cell(cell_type)

    def on_run(self, *args):
        page = self.get_visible_page()
        if isinstance(page, ICells):
            page.run_selected_cell()

    def on_run_line(self, *args):
        page = self.get_visible_page()
        if isinstance(page, CodePage):
            page.run_line()

    def on_jupyter_server_started(self, server):
        self.server_status_label.set_label("Server Connected")

    def on_jupyter_server_has_new_line(self, server, line):
        self.server_terminal.feed(line)

    def get_visible_page(self):
        try:
            return self.panel_grid.get_most_recent_frame().get_visible_child()
        except Exception as e:
            print(e)
            return None

    @Gtk.Template.Callback("on_create_frame")
    def on_create_frame(self, *args):
        new_frame = Panel.Frame()
        new_frame.set_placeholder(
            Launcher(self.jupyter_server.avalaible_kernels))
        tab_bar = Panel.FrameTabBar()
        new_frame.set_header(tab_bar)

        new_frame.connect("page-closed", self.on_page_closed)

        return new_frame

    def on_page_closed(self, frame, widget):
        if widget == self.previous_page:
            self.disconnect_page_funcs(widget)

            self.previous_page = None

        if isinstance(widget, IDisconnectable):
            widget.disconnect()

        if isinstance(widget, IKernel):
            kernel = widget.get_kernel()
            if kernel:
                kernel_id = kernel.kernel_id
                if not self.get_page_with_kernel(kernel_id):
                    asyncio.create_task(self._shutdown_kernel_by_id(kernel_id))

    def get_page_with_kernel(self, kernel_id):
        result = None

        def check_frame(frame):
            nonlocal result
            for adw_page in frame.get_pages():
                page = adw_page.get_child()
                if isinstance(page, IKernel):
                    if page.get_kernel().kernel_id == kernel_id:
                        result = page
                        return

        self.panel_grid.foreach_frame(check_frame)

        return result

    @Gtk.Template.Callback("on_key_pressed")
    def on_key_pressed(self, controller, keyval, keycode, state):
        print(keyval, keycode, state)

        if keycode == 36 and state == Gdk.ModifierType.CONTROL_MASK:
            self.activate_action("win.run-cell")

    #
    #   CHAPTER VIEW for NotebookPage
    #

    def on_select_cell_action(self, action, variant):
        notebook = self.get_visible_page()
        if not isinstance(notebook, NotebookPage):
            return

        notebook.set_selected_cell_index(variant.get_uint32())

    @Gtk.Template.Callback("on_chapter_menu_activated")
    def on_chapter_menu_activated(self, *args):
        page = self.get_visible_page()
        if not isinstance(page, NotebookPage):
            return

        chapters = []

        header_pattern = re.compile(r'^(#{1,6})\s+(.+)', re.MULTILINE)

        for index, cell in enumerate(page.notebook_model):
            if cell.cell_type == CellType.TEXT:
                matches = header_pattern.findall(cell.source)

                for match in matches:
                    chapters.append((len(match[0]), match[1].strip(), index))

        print(chapters)
        chapter_model = Gio.ListStore.new(TreeNode)

        level_stack = []
        for chapter in chapters:
            level, title, index = chapter
            node = TreeNode(title, index, [])

            if level == 0:
                chapter_model.append(node)
                level_stack = [(level, node)]
            else:
                while level_stack and level_stack[-1][0] >= level:
                    level_stack.pop()

                if not level_stack:
                    chapter_model.append(node)
                    level_stack = [(level, node)]
                    continue

                parent_node = level_stack[-1][1]
                parent_node.children.append(node)

                level_stack.append((level, node))

        tree_list_model = Gtk.TreeListModel.new(
            chapter_model, False, True, self.create_model_func)

        selection_model = Gtk.NoSelection(model=tree_list_model)

        self.chapters_list_view.set_model(selection_model)

    def create_model_func(self, item):
        if item.children == []:
            return None

        child_model = Gio.ListStore.new(TreeNode)
        for child in item.children:
            child_model.append(child)
        return child_model

    @Gtk.Template.Callback("on_chapter_factory_setup")
    def on_chapter_factory_setup(self, factory, list_item):
        list_item.set_child(ChapterRow(css_classes=["chapter-button"]))

    @Gtk.Template.Callback("on_chapter_factory_bind")
    def on_chapter_factory_bind(self, factory, list_item):
        item = list_item.get_item()
        widget = list_item.get_child()
        widget.expander.set_list_row(item)

        item = list_item.get_item().get_item()

        widget.set_action_name("win.select-cell")
        widget.set_action_target_value(GLib.Variant('u', item.index))
        widget.set_text(item.node_name)
