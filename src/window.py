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
from gi.repository import Panel

import subprocess
import re
import threading
import time
import os
import json
import nbformat
from pprint import pprint

from .jupyter_server import JupyterServer
from .cell_ui import CellUI
from .cell import Cell, CellType
from .output import Output, OutputType
from .command_line import CommandLine
from .notebook import Notebook
from .notebook_view import NotebookView
from .jupyter_kernel import JupyterKernel
from .browser_page import BrowserPage
from .kernel_manager_view import KernelManager

@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/window.ui')
class PlanetnineWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'PlanetnineWindow'

    # toolbar_view = Gtk.Template.Child()
    terminal = Gtk.Template.Child()
    # main_frame = Gtk.Template.Child()
    grid = Gtk.Template.Child()
    omni_bar = Gtk.Template.Child()
    kernel_status_menu = Gtk.Template.Child()
    kernel_manager_view = Gtk.Template.Child()
    select_kernel_dialog = Gtk.Template.Child()
    select_kernel_combo_row = Gtk.Template.Child()
    omni_label = Gtk.Template.Child()
    server_status_label = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.jupyter_server = JupyterServer()

        self.jupyter_server.connect("started", self.on_jupyter_server_started)
        self.jupyter_server.connect("new-line", self.on_jupyter_server_has_new_line)

        # self.jupyter_server.start()

        self.terminal.set_color_background(Gdk.RGBA(alpha=1))

        self.create_action('add-text-block', lambda *args: self.add_cell_to_selected_notebook(Cell(CellType.TEXT)))
        self.create_action('add-code-block', lambda *args: self.add_cell_to_selected_notebook(Cell(CellType.CODE)))
        self.create_action('new-notebook', lambda *args: self.add_notebook_page(Notebook(name="Untitled.ipynb")))

        self.create_action('run-selected-cell', self.run_selected_cell)
        self.create_action('shutdown-kernel', self.shutdown_kernel)
        self.create_action('stop-execution', self.run_selected_cell)
        self.create_action('start-kernel', self.start_kernel)
        self.create_action('restart-kernel', self.restart_kernel)
        self.create_action('restart-kernel-and-run', self.restart_kernel_and_run)
        self.create_action('start-server', self.start_server)

        self.create_action('open-notebook', self.open_notebook)

        self.create_action('new-browser-page', self.open_browser_page)

        self.command_line = CommandLine()

        self.previously_presented_widget = None

        self.add_notebook_page(Notebook(name="Untitled.ipynb"))

    def start_server(self, *args):
        self.jupyter_server.start()

    def shutdown_kernel(self, *args):
        print("Shutdown")

        self.select_kernel_dialog.present(self)

    def add_cell_to_selected_notebook(self, cell):
        notebook = self.get_selected_notebook()
        notebook.add_cell(cell)

    def run_selected_cell(self, *args):
        notebook = self.get_selected_notebook()
        notebook.run_selected_cell()

    def on_jupyter_server_started(self, server):
        self.server_status_label.set_label(_("Server Connected"))
        server.get_kernel_specs(self.on_got_kernel_specs)
        server.start_kernel_by_name("python3", self.on_kernel_started, self.get_selected_notebook())

    def on_got_kernel_specs(self, success, specs):
        if success:
            self.kernel_manager_view.parse(specs)

    def on_kernel_started(self, successful, kernel_client, notebook):
        print(kernel_client)

        notebook.set_kernel(kernel_client)

    def start_kernel(self, *args):
        print("start_kernel")

        self.jupyter_server.new_session("python3", "Session1", self.new_session_callback)

    def new_session_callback(self, succ, session):
        pprint(session)

        k_id = session['kernel']['id']

        self.jupyter_server.get_kernel_info(k_id, lambda suc, info: pprint(info))

    def on_jupyter_server_has_new_line(self, server, line):
        self.terminal.feed([ord(char) for char in line + "\r\n"])

    def restart_kernel(self, *args):
        print("RESTART")
        # self.jupyter_server.restart_kernel(2, lambda *args: print("restarted"))

        # self.get_selected_notebook()

        self.jupyter_server.get_sessions(lambda succ, sessions: pprint(sessions))

    def restart_kernel_and_run(self, *args):
        print("RESTART and run!")
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
        try:
            file_path = dialog.open_finish(response)
        except:
            return

        with open(file_path, 'r') as file:
            file_content = file.read()
            notebook_node = nbformat.reads(file_content, as_version=4)

            notebook = Notebook.new_from_json(notebook_node)
            notebook.name = os.path.basename(file_path)

            self.add_notebook_page(notebook)

    def add_notebook_page(self, notebook):
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
        self.omni_label.set_label(kernel_name)

    @Gtk.Template.Callback("on_create_frame")
    def on_create_frame(self, grid):
        new_frame = Panel.Frame()
        new_frame.set_placeholder(
            Adw.StatusPage(
                title="No Notebooks Open",
                child=Gtk.Button(
                    css_classes=["suggested-action", "pill"],
                    action_name="win.open-notebook",
                    label=_("Open Notebook"),
                    halign=Gtk.Align.CENTER
                )
            )
        )
        tab_bar = Panel.FrameTabBar()
        new_frame.set_header(tab_bar)

        return new_frame

    @Gtk.Template.Callback("on_key_pressed")
    def on_key_pressed(self, controller, keyval, keycode, state):
        print(keyval, keycode, state)

