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
from .pages.geo_json_page import GeoJsonPage

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
from .interfaces.searchable import ISearchable

from .widgets.launcher import Launcher
from .widgets.chapter_row import ChapterRow

from .utils.converters import is_mime_displayable
from .utils.converters import get_language_icon

from gettext import gettext as _

GObject.type_register(TerminalPanel)
GObject.type_register(KernelTerminalPanel)


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
    server_status_label = Gtk.Template.Child()
    start_sidebar_panel_frame = Gtk.Template.Child()
    bottom_panel_frame = Gtk.Template.Child()
    language_button = Gtk.Template.Child()
    position_menu_button = Gtk.Template.Child()
    add_cell_button = Gtk.Template.Child()
    move_cursor_entry_buffer = Gtk.Template.Child()
    notebook_navigation_menu = Gtk.Template.Child()
    chapters_list_view = Gtk.Template.Child()
    toolbar_view = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    omni_bar = Gtk.Template.Child()
    omni_image = Gtk.Template.Child()
    omni_label = Gtk.Template.Child()

    kernel_language_label = Gtk.Template.Child()
    kernel_display_name_label = Gtk.Template.Child()
    kernel_name_label = Gtk.Template.Child()

    toast_overlay = Gtk.Template.Child()

    cache_dir = os.environ["XDG_CACHE_HOME"]
    files_cache_dir = os.path.join(cache_dir, "files")

    images_path = os.path.join(cache_dir, "g_images")
    html_path = os.path.join(cache_dir, "g_html")
    latex_path = os.path.join(cache_dir, "g_latex")

    os.makedirs(images_path, exist_ok=True)
    os.makedirs(html_path, exist_ok=True)
    os.makedirs(latex_path, exist_ok=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # TODO Instead of starting kernels use sessions

        # TODO Check for running kernels at startup
        # TODO Make shutting down servers more reliable
        # TODO Get kernel metadata and save it in notebooks
        # TODO Select/start last selected kernel for notebook

        # TODO Add cell splitting

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
        self.run_cell_and_advance_action = self.create_action(
            'run-cell-and-advance', self.on_run_and_advance)
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
        self.interrupt_kernel_action = self.create_action(
            'interrupt-kernel', self.on_interrupt_kernel)

        self.create_action_with_target(
            'select-cell',
            GLib.VariantType.new("u"),
            self.on_select_cell_action)

        self.run_cell_and_advance_action.set_enabled(False)
        self.run_line_action.set_enabled(False)
        self.run_selected_action.set_enabled(False)
        self.restart_kernel_and_run_action.set_enabled(False)
        self.restart_kernel_action.set_enabled(False)
        self.change_kernel_action.set_enabled(False)
        self.interrupt_kernel_action.set_enabled(False)

        #   OTHER ACTIONS

        self.start_server_action = self.create_action(
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

        self.create_action_with_target(
            'new-session',
            GLib.VariantType.new("(sss)"),
            self.start_new_session)

        self.create_action_with_target(
            'error-toast',
            GLib.VariantType.new("(ss)"),
            self.on_error_toast_action)

        self.create_action_with_target(
            'error-toast-info',
            GLib.VariantType.new("s"),
            self.on_error_toast_info_action)

        self.create_action(
            'empty-text', self.on_empty_text_action)
        self.create_action(
            'empty-json', self.on_empty_json_action)
        self.create_action(
            'empty-geo-json', self.on_empty_geo_json_action)
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

    #
    #   NEW NOTEBOOK PAGE WITH KERNEL NAME
    #

    def on_new_notebook_action(self, action, parameter):
        """Creates a new notebook page with a requested kernel by name"""
        notebook_page = NotebookPage(None, kernel_name=parameter.get_string())
        self.panel_grid.add(notebook_page)

    #
    #   NEW NOTEBOOK PAGE WITH EXISTING KERNEL FROM ID
    #

    def on_new_notebook_id_action(self, action, parameter):
        """Creates a new notebook page with an existing kernel by id"""
        notebook_page = NotebookPage(None, kernel_id=parameter.get_string())
        self.panel_grid.add(notebook_page)

    #
    #   NEW CONSOLE PAGE WITH KERNEL NAME
    #

    def on_new_console_action(self, action, parameter):
        """Creates a new console page with a requested kernel by name"""
        console_page = ConsolePage(kernel_name=parameter.get_string())
        self.panel_grid.add(console_page)

    #
    #   NEW CONSOLE PAGE WITH EXISTING KERNEL FROM ID
    #

    def on_new_console_id_action(self, action, parameter):
        """Creates a new console page with an existing kernel by id"""
        console_page = ConsolePage(kernel_id=parameter.get_string())
        self.panel_grid.add(console_page)

    #
    #   NEW CODE PAGE WITH KERNEL NAME
    #

    def on_new_code_action(self, action, parameter):
        """Creates a new code page with a requested kernel by name"""
        code_page = CodePage(None, kernel_name=parameter.get_string())
        self.panel_grid.add(code_page)

    #
    #   NEW CODE PAGE WITH EXISTING KERNEL FROM ID
    #

    def on_new_code_id_action(self, action, parameter):
        """Creates a new code page with an existing kernel by id"""
        code_page = CodePage(None, kernel_id=parameter.get_string())
        self.panel_grid.add(code_page)

    #
    #   SET A NEW or EXISTING KERNEL TO A PAGE
    #

    def on_request_kernel_name(self, action, parameter):
        """Handles the request-kernel-name action"""

        page_id, kernel_name = parameter.unpack()
        asyncio.create_task(self._on_request_kernel_name(page_id, kernel_name))

    async def _on_request_kernel_name(self, page_id, kernel_name):
        """Handles the request-kernel-name action asynchronously
        and starts the new kernel and adds it to the page with
        the corresponding page_id"""

        page = self.find_ikernel_page(page_id)
        if page:
            success, kernel = await self.jupyter_server.start_kernel_by_name(
                kernel_name)

            if success:
                page.set_kernel(kernel)
                self.update_kernel_info(page)

    def on_request_kernel_id(self, action, parameter):
        """Handles the request-kernel-id action by retriving the requested
        kernel and adding it to the page with the corresponding page_id"""

        page_id, kernel_id = parameter.unpack()
        page = self.find_ikernel_page(page_id)
        if page:
            success, kernel = self.jupyter_server.get_kernel_by_id(
                kernel_id)

            if success:
                page.set_kernel(kernel)
                self.update_kernel_info(page)

    def find_ikernel_page(self, page_id):
        """Finds the page with the corresponding page_id"""

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

    def start_server(self, *_args):
        """Starts the Jupyter Kernel"""

        self.jupyter_server.start()

    #
    #   SHUTDOWN KERNEL BY ID
    #

    def shutdown_kernel_by_id(self, action, parameter):
        """Shutsdown a kernel given an id"""

        asyncio.create_task(
            self._shutdown_kernel_by_id(parameter.get_string()))

    async def _shutdown_kernel_by_id(self, kernel_id):
        """Shutsdown a kernel given an id asynchronously"""

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

    def restart_kernel_by_id(self, action, parameter):
        """Restart a kernel given an id"""

        asyncio.create_task(self._restart_kernel_by_id(parameter.get_string()))

    async def _restart_kernel_by_id(self, kernel_id):
        """Restart a kernel given an id asynchronously"""

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

    def interrupt_kernel_by_id(self, action, parameter):
        """Interrupt a kernel given an id"""

        asyncio.create_task(
            self._interrupt_kernel_by_id(parameter.get_string()))

    async def _interrupt_kernel_by_id(self, kernel_id):
        """Interrupt a kernel given an id asynchronously"""

        success = await self.jupyter_server.interrupt_kernel(kernel_id)
        if success:
            print("kernel has been interrupted")
        else:
            print("kernel has NOT been interrupted")

    #
    #   RESTART VISIBLE KERNEL
    #

    def restart_kernel_visible(self, *_args):
        """Restart the visible page kernel"""

        kernel_id = self.get_visible_page().get_kernel().kernel_id
        self.activate_action(
            "win.restart-kernel-id", GLib.Variant('s', kernel_id))

    #
    #   RESTART VISIBLE KERNEL AND RUN ALL CELLS
    #

    def restart_kernel_and_run(self, *_args):
        """Restart the visible page kernel and runs all cells"""

        asyncio.create_task(self._restart_kernel_and_run())

    async def _restart_kernel_and_run(self):
        """Restart the visible page kernel and runs all cells asynchronously"""

        kernel_id = self.get_visible_page().get_kernel().kernel_id

        success = await self._restart_kernel_by_id(kernel_id)

        if success:
            self.get_visible_page().run_all_cells()

    #
    #   INTERRUPT VISIBLE KERNEL
    #

    def on_interrupt_kernel(self, *_args):
        """Interrupts the visible page kernel"""

        kernel_id = self.get_visible_page().get_kernel().kernel_id

        asyncio.create_task(self._interrupt_kernel_by_id(kernel_id))

    #
    #   SAVE VISIBLE PAGE
    #

    def save_viewed(self):
        """Saves the visible page"""

        page = self.get_visible_page()
        if isinstance(page, ISaveable):
            page.get_save_delegate().save_async(
                None, self.on_saved_finished)

    def on_saved_finished(self, delegate, result):
        """Save operation finish callback"""

        print("saved")

    #
    #   OPEN BROWSER PAGE WITH URL
    #

    def open_browser_page(self, action, parameter):
        """Opens a new Browser page with a starting url or the default
        if empty"""

        page = BrowserPage(parameter.get_string())
        self.panel_grid.add(page)

    #
    #   OPEN EMPTY VIEWERS
    #

    def on_empty_text_action(self, *_args):
        self.panel_grid.add(TextPage())

    def on_empty_json_action(self, *_args):
        self.panel_grid.add(JsonViewerPage())

    def on_empty_geo_json_action(self, *_args):
        self.panel_grid.add(GeoJsonPage())

    #
    #   CREATE ACTIONS WITH OR WITHOUT TARGETS
    #

    def create_action(self, name, callback):
        """Used to create a new action without target"""

        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        return action

    def create_action_with_target(self, name, target_type, callback):
        """Used to create a new action with a target"""

        action = Gio.SimpleAction.new(name, target_type)
        action.connect("activate", callback)
        self.add_action(action)
        return action

    #
    #   OPEN FILES OR NOTEBOOKS
    #

    def on_open_notebook_action(self, *_args):
        """Opens a new notebook using a File dialog"""

        asyncio.create_task(self._on_open_notebook_action())

    async def _on_open_notebook_action(self):
        """Opens a new notebook using a File dialog asynchronously"""

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
            self.panel_grid.add(NotebookPage(file.get_path()))
        except Exception as error:
            self.activate_action(
                "win.error-toast",
                GLib.Variant(
                    "(ss)", (_("Could not open Notebook"), str(error))))

    def on_open_code_action(self, *_args):
        """Opens a new code page using a File dialog"""

        asyncio.create_task(self._on_open_code_action())

    async def _on_open_code_action(self):
        """Opens a new code page using a File dialog asynchronously"""

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
            self.panel_grid.add(CodePage(file.get_path()))
        except Exception as e:
            print(e)

    #
    #   OPEN ANY FILE
    #

    def on_open_file_action(self, action, parameter):
        """Handles the open-file action, takes the file's path"""
        file_path = parameter.get_string()

        self.open_file(file_path)

    def open_file(self, file_path):
        """Opens a file given his path, if already open it raises it's page"""
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
            case "application/geo+json":
                self.panel_grid.add(GeoJsonPage(file_path))
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

    def open_file_with_text(self, action, parameter):
        """Opens a file using the Text page"""
        file_path = parameter.get_string()

        if self.raise_page_if_open(file_path):
            return

        self.panel_grid.add(TextPage(file_path))

    def raise_page_if_open(self, file_path):
        """Raises a page if it has opened a file with the same path

        :returns: if a page has been raised
        :rtypes: bool
        """

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
        """Raises a page

        :returns: if a page has been raised
        :rtypes: bool
        """

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

    def on_focus_changed(self, *_args):
        """Called when the focused widget changes it checks the visible page
        properties and connects signals/shows hide UI based on it
        """

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
        """Updates the UI with the page kernel information or hides UI if
        the kernel is None
        """

        if page:
            kernel = page.get_kernel()
            if kernel:
                self.kernel_status_menu.set_label(kernel.status)
                self.omni_label.set_label(kernel.display_name)
                self.omni_image.set_visible(True)
                self.omni_image.set_from_icon_name(
                    get_language_icon(kernel.language))

                self.kernel_language_label.set_label(kernel.language)
                self.kernel_display_name_label.set_label(kernel.display_name)
                self.kernel_name_label.set_label(kernel.name)

                self.variables_panel.set_model(kernel.get_variables())
                self.kernel_terminal.set_kernel(kernel)

                if kernel.status == "busy":
                    self.omni_bar.start_pulsing()
                    self.interrupt_kernel_action.set_enabled(True)
                else:
                    self.omni_bar.stop_pulsing()
                    self.interrupt_kernel_action.set_enabled(False)

                self.run_cell_and_advance_action.set_enabled(True)
                self.run_line_action.set_enabled(True)
                self.run_selected_action.set_enabled(True)
                self.restart_kernel_and_run_action.set_enabled(True)
                self.restart_kernel_action.set_enabled(True)
        else:
            self.kernel_status_menu.set_label("")
            self.omni_label.set_label("No Kernel")
            self.omni_image.set_visible(False)

            self.kernel_language_label.set_label(_("None"))
            self.kernel_display_name_label.set_label(_("None"))
            self.kernel_name_label.set_label(_("None"))

            self.variables_panel.set_model(None)
            self.kernel_terminal.set_kernel(None)

            self.run_cell_and_advance_action.set_enabled(False)
            self.run_line_action.set_enabled(False)
            self.run_selected_action.set_enabled(False)
            self.restart_kernel_and_run_action.set_enabled(False)
            self.restart_kernel_action.set_enabled(False)
            self.interrupt_kernel_action.set_enabled(False)

    def update_page_language(self, page):
        """Updates the UI with the page language"""

        lang = page.get_language()
        if lang == "" or lang is None:
            lang = _("None")

        self.language_button.set_label(lang.title())

    def on_cursor_moved(self, page, buffer, index):
        """Updates the UI with the new cursor position"""

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
        """Disconnect all functions connected to the previously visible page"""

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
    def on_move_cursor_activated(self, *_args):
        """Handles clicking the cursor GO button or activating the entry"""

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
    #   START A NEW SESSION
    #

    def start_new_session(self, action, target):
        kernel_name, session_name, file_path = target.unpack()
        asyncio.create_task(
            self._start_new_session(kernel_name, session_name, file_path))

    async def _start_new_session(self, kernel_name, session_name, file_path):
        succ, session_id = await self.jupyter_server.new_session(
            kernel_name, session_name, file_path)

        if succ:
            print(session_id)

    #
    #   CHANGE/SELECT KERNEL OF A PAGE BY ID OR VISIBLE
    #

    def on_change_kernel_action(self, action, target):
        """Handles the change-kernel action

        If the target is empty it changes the visible page kernel, if not it
        finds the page with the corresponding page_id and raises it
        """

        if target.get_string() == "":
            page = self.get_visible_page()
        else:
            page = self.find_ikernel_page(target.get_string())
            self.raise_page(page)

        if page:
            asyncio.create_task(self._change_kernel(page))

    async def _change_kernel(self, page):
        """Changes the kernel of the given page by showing a dialog"""

        self.select_kernel_combo_row.set_selected(0)
        # TODO start with the current kernel

        choice = await dialog_choose_async(self, self.select_kernel_dialog)

        if choice == 'select':

            kernel = self.select_kernel_combo_row.get_selected_item()

            old_kernel = page.get_kernel()

            if isinstance(kernel, JupyterKernelInfo):
                succ, new_ker = await self.jupyter_server.start_kernel_by_name(
                    kernel.name)
                if succ:
                    page.set_kernel(new_ker)
                    self.update_kernel_info(page)
            elif isinstance(kernel, JupyterKernel):
                page.set_kernel(kernel)
                self.update_kernel_info(page)

            if old_kernel:
                self.shutdown_kernel_if_orphan(old_kernel.kernel_id)

    #
    #   CHARGE/SELECT KERNEL ALERT DIALOG LIST VIEW
    #

    @Gtk.Template.Callback("on_select_kernel_header_setup")
    def on_select_kernel_header_setup(self, factory, list_item):
        """Setup a change kernel dialog list view header"""

        list_item.set_child(
            Gtk.Label(
                xalign=0,
                margin_start=6,
                margin_end=6
            )
        )

    @Gtk.Template.Callback("on_select_kernel_header_bind")
    def on_select_kernel_header_bind(self, factory, list_item):
        """Binds a change kernel dialog list view header"""

        item = list_item.get_item()
        label = list_item.get_child()

        # FIXME It would be better to have a way to get the name stored
        #           in the MultiListModel
        if isinstance(item, JupyterKernelInfo):
            label.set_label(_("Avalaible Kernels"))
        elif isinstance(item, JupyterKernel):
            label.set_label(_("Running Kernels"))

    @Gtk.Template.Callback("on_select_kernel_setup")
    def on_select_kernel_setup(self, factory, list_item):
        """Setup the change kernel dialog list view widgets"""

        list_item.set_child(
            Gtk.Label(
                xalign=0,
                margin_start=6,
                margin_end=6
            )
        )

    @Gtk.Template.Callback("on_select_kernel_bind")
    def on_select_kernel_bind(self, factory, list_item):
        """Binds a change kernel dialog list view widget to a list_item"""

        item = list_item.get_item()
        label = list_item.get_child()

        label.set_label(item.display_name)

    #
    #   SEARCH VISIBLE PAGE
    #

    def search_visible_page(self):
        """Handles app.search action"""

        page = self.get_visible_page()

        if isinstance(page, ISearchable):
            self.toolbar_view.set_reveal_bottom_bars(True)
            page.set_search_text(self.search_entry.get_text())
            page.search_text()

    @Gtk.Template.Callback("on_search_changed")
    def on_search_changed(self, *_args):
        """Callback to the search entry search-changed signal"""

        page = self.get_visible_page()
        if isinstance(page, ISearchable):
            page.set_search_text(self.search_entry.get_text())
            page.search_text()

    @Gtk.Template.Callback("on_search_next_match")
    def on_search_next_match(self, *_args):
        """Handles focusing to the next search match"""

        pass

    @Gtk.Template.Callback("on_search_previous_match")
    def on_search_previous_match(self, *_args):
        """Handles focusing to the previous search match"""

        pass

    @Gtk.Template.Callback("on_search_close_clicked")
    def on_search_close_clicked(self, *_args):
        """Callback to the search bar close button clicked signal"""

        self.toolbar_view.set_reveal_bottom_bars(False)

        page = self.get_visible_page()
        if isinstance(page, ISearchable):
            page.set_search_text("")

    #
    #   CLOSE
    #

    def close(self):
        """Called when the user request the app to be closed"""

        self.panel_grid.agree_to_close_async(None, self.finish_close)
        return True

    def finish_close(self, _grid, result):
        """Callback to the close function after having closed all pages"""

        try:
            success = self.panel_grid.agree_to_close_finish(result)
            if success:
                asyncio.create_task(self._quit())
        except Exception as e:
            print(e)

    async def _quit(self):
        """Asynchronously shutdown the server with a confirmation dialog"""

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
        """Add cell of type cell_type to the visible page"""

        page = self.get_visible_page()
        if isinstance(page, ICells):
            page.add_cell(cell_type)

    def on_run(self, *_args):
        """Run the visible page selected cell"""

        page = self.get_visible_page()
        if isinstance(page, ICells):
            page.run_selected_cell()

    def on_run_and_advance(self, *_args):
        """Run the visible page selected cell and advance to the next one"""

        page = self.get_visible_page()
        if isinstance(page, ICells):
            page.run_selected_and_advance()

    def on_run_line(self, *_args):
        """Run the visible page line, only for CodePage"""

        page = self.get_visible_page()
        if isinstance(page, CodePage):
            page.run_line()

    def on_jupyter_server_started(self, server):
        """Callback to the Server started signal, updates the UI"""

        self.server_status_label.set_label("Server Connected")

        self.change_kernel_action.set_enabled(True)
        self.start_server_action.set_enabled(False)

        asyncio.create_task(self.get_se())

    async def get_se(self):
        await self.jupyter_server.get_running_kernels()
        await self.jupyter_server.get_sessions()

    def on_jupyter_server_has_new_line(self, server, line):
        """Callback to the Server new-line signal,
        updates the Server Terminal Panel"""

        self.server_terminal.feed(line)

    def get_visible_page(self):
        """Returns the visible page"""

        try:
            return self.panel_grid.get_most_recent_frame().get_visible_child()
        except Exception as e:
            print(e)
            return None

    @Gtk.Template.Callback("on_create_frame")
    def on_create_frame(self, *_args):
        """create frame function for panel_grid"""

        new_frame = Panel.Frame()
        new_frame.set_placeholder(
            Launcher(self.jupyter_server.avalaible_kernels))
        tab_bar = Panel.FrameTabBar()
        new_frame.set_header(tab_bar)

        new_frame.connect("page-closed", self.on_page_closed)

        return new_frame

    def on_page_closed(self, frame, widget):
        """Callback to any frame page-closed signal"""

        if widget == self.previous_page:
            self.disconnect_page_funcs(widget)

            self.previous_page = None

        if isinstance(widget, IDisconnectable):
            widget.disconnect()

        if isinstance(widget, IKernel):
            kernel = widget.get_kernel()
            if kernel:
                kernel_id = kernel.kernel_id
                self.shutdown_kernel_if_orphan(kernel_id)

        # Update the UI
        self.on_focus_changed()

    def shutdown_kernel_if_orphan(self, kernel_id):
        if not self.get_page_with_kernel(kernel_id):
            if self.settings.get_boolean("auto-shutdown-kernel"):
                asyncio.create_task(
                    self.jupyter_server.shutdown_kernel(kernel_id))
            else:
                asyncio.create_task(
                    self._shutdown_kernel_by_id(kernel_id))

    def get_page_with_kernel(self, kernel_id):
        """Returns a page with a specific kernel by kernel_id"""

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
        """Callback to the KeyController key-pressed signal"""

        print(keyval, keycode, state)

        if keycode == 36 and state == Gdk.ModifierType.CONTROL_MASK:
            self.activate_action("win.run-cell")

    #
    #   ERROR TOAST
    #

    def on_error_toast_action(self, action, parameter):
        print("activated")
        brief, message = parameter.unpack()

        toast = Adw.Toast(
            title=brief,
            button_label="Info",
            action_name="win.error-toast-info",
            action_target=GLib.Variant("s", message))

        self.toast_overlay.add_toast(toast)

    def on_error_toast_info_action(self, action, parameter):
        message = parameter.unpack()

        builder = Gtk.Builder.new_from_resource(
            "/io/github/nokse22/PlanetNine/gtk/error_dialog.ui")
        builder.get_object("label").set_label(message)

        builder.get_object("dialog").present(self.get_root())

    #
    #   CHAPTER VIEW for NotebookPage
    #

    def on_select_cell_action(self, action, parameter):
        """Handles the select-cell action, takes the cell index to select"""

        notebook = self.get_visible_page()
        if not isinstance(notebook, NotebookPage):
            return

        notebook.set_selected_cell_index(parameter.get_uint32())

    @Gtk.Template.Callback("on_chapter_menu_activated")
    def on_chapter_menu_activated(self, *_args):
        """Run when the chapter menu popover is activate to populate it"""

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
        """Chapter tree create sub model function"""

        if item.children == []:
            return None

        child_model = Gio.ListStore.new(TreeNode)
        for child in item.children:
            child_model.append(child)
        return child_model

    @Gtk.Template.Callback("on_chapter_factory_setup")
    def on_chapter_factory_setup(self, factory, list_item):
        """Factory setup for chapter listview"""

        list_item.set_child(ChapterRow(css_classes=["chapter-button"]))

    @Gtk.Template.Callback("on_chapter_factory_bind")
    def on_chapter_factory_bind(self, factory, list_item):
        """Factory bind for chapter listview"""

        item = list_item.get_item()
        widget = list_item.get_child()
        widget.expander.set_list_row(item)

        item = list_item.get_item().get_item()

        widget.set_action_name("win.select-cell")
        widget.set_action_target_value(GLib.Variant('u', item.index))
        widget.set_text(item.node_name)

    @Gtk.Template.Callback("on_chapter_factory_unbind")
    def on_chapter_factory_unbind(self, factory, list_item):
        """Factory unbind for chapter listview"""

        list_item.get_child().disconnect()
