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
from pprint import pprint

from .jupyter_server import JupyterServer
from .cell import Cell, CellType
from .command_line import CommandLine
from .notebook import Notebook
from .notebook_view import NotebookView
from .browser_page import BrowserPage
from .kernel_manager_view import KernelManagerView
from .workspace_view import WorkspaceView
from .launcher import Launcher


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
            'add-text-block',
            lambda *_: self.add_cell_to_selected_notebook(Cell(CellType.TEXT))
        )
        self.create_action(
            'add-code-block',
            lambda *_: self.add_cell_to_selected_notebook(Cell(CellType.CODE))
        )
        self.create_action_with_target(
            'new-notebook',
            GLib.VariantType.new("s"),
            self.on_new_notebook_action
        )

        self.create_action('run-selected-cell', self.run_selected_cell)

        self.create_action_with_target(
            'shutdown-kernel',
            GLib.VariantType.new("s"),
            lambda _, variant: self.shutdown_kernel_by_id(variant.get_string())
        )
        self.create_action_with_target(
            'interrupt-kernel',
            GLib.VariantType.new("s"),
            lambda _, variant: self.interrupt_kernel_by_id(variant.get_string())
        )
        self.create_action_with_target(
            'restart-kernel',
            GLib.VariantType.new("s"),
            lambda _, variant: self.restart_kernel_by_id(variant.get_string())
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

    def on_new_notebook_action(self, action, variant):
        notebook = Notebook(name="Untitled.ipynb")

        widget = Panel.Widget(
            icon_name="python-symbolic",
            title=notebook.name
        )
        widget.connect("presented", self.on_widget_presented)
        save_delegate = Panel.SaveDelegate()
        widget.set_save_delegate(save_delegate)
        notebook_view = NotebookView(notebook)
        widget.set_child(notebook_view)
        self.grid.add(widget)

        self.jupyter_server.start_kernel_by_name(
            variant.get_string(),
            self.on_kernel_started,
            notebook_view
        )

    def on_kernel_started(self, success, kernel, notebook):
        notebook.set_kernel(kernel)

    def start_server(self, *args):
        self.jupyter_server.start()

    #
    #   SHUTDOWN KERNEL
    #

    def shutdown_kernel_by_id(self, kernel_id):
        self.shutdown_kernel_dialog.choose(
            self,
            None,
            self.on_shutdown_kernel_choosen,
            kernel_id
        )

    def on_shutdown_kernel_choosen(self, dialog, result, kernel_id):
        choice = dialog.choose_finish(result)

        if choice == 'shutdown':
            self.jupyter_server.shutdown_kernel(
                kernel_id,
                self.on_kernel_is_shutdown
            )

    def on_kernel_is_shutdown(self, success):
        pass

    #
    #   RESTART_KERNEL
    #

    def restart_kernel_by_id(self, kernel_id):
        self.restart_kernel_dialog.choose(
            self,
            None,
            self.on_restart_kernel_choosen,
            kernel_id
        )

    def on_restart_kernel_choosen(self, dialog, result, kernel_id):
        choice = dialog.choose_finish(result)

        if choice == 'restart':
            self.jupyter_server.restart_kernel(
                kernel_id,
                self.on_kernel_is_restarted
            )

    def on_kernel_is_restarted(self, success):
        print("Restarted")

    #
    #   INTERRUPT KERNEL
    #

    def interrupt_kernel_by_id(self, kernel_id):
        self.jupyter_server.interrupt_kernel(
            kernel_id,
            self.on_kernel_is_interrupted
        )

    def on_kernel_is_interrupted(self, success):
        print("Interrupted")

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
        self.jupyter_server.get_kernel_specs(self.on_got_kernel_specs)

    def on_got_kernel_specs(self, success, specs):
        if not success:
            self.jupyter_server.get_kernel_specs(self.on_got_kernel_specs)

    def on_jupyter_server_has_new_line(self, server, line):
        self.terminal.feed([ord(char) for char in line + "\r\n"])

    def restart_kernel_and_run(self, *args):
        notebook = self.get_selected_notebook()
        notebook.jupyter_kernel.restart_kernel(2, lambda *args: print("restarted"))
        notebook.run_all_cells()

    def get_selected_notebook(self):
        return self.grid.get_most_recent_frame().get_visible_child().get_child()

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
        widget.set_child(NotebookView(notebook))
        self.grid.add(widget)

    def on_widget_presented(self, widget):
        widget = widget.get_child()

        if isinstance(self.previously_presented_widget, NotebookView):
            self.previously_presented_widget.disconnect_by_func(self.on_kernel_info_changed)

        if isinstance(widget, NotebookView):
            widget.connect("kernel-info-changed", self.on_kernel_info_changed)
            self.set_kernel_info(widget.kernel_name, widget.kernel_status)

        self.previously_presented_widget = widget

    def on_kernel_info_changed(self, notebook_view, kernel_name, status):
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

