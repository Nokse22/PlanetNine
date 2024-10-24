# notebook_page.py
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

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Panel, GLib

import os
import nbformat
import asyncio

from ..models.cell import Cell, CellType
from ..widgets.cell_ui import CellUI
from ..models.output import Output, OutputType
from ..models.notebook import Notebook
from ..backend.command_line import CommandLine
# from ..completion_providers.completion_providers import LSPCompletionProvider
from ..completion_providers.completion_providers import WordsCompletionProvider
from ..others.save_delegate import GenericSaveDelegate
from ..interfaces.saveable import ISaveable
from ..interfaces.disconnectable import IDisconnectable
from ..interfaces.cursor import ICursor
from ..interfaces.kernel import IKernel
from ..interfaces.language import ILanguage
from ..interfaces.cells import ICells
from ..interfaces.searchable import ISearchable


@Gtk.Template(
    resource_path='/io/github/nokse22/PlanetNine/gtk/notebook_page.ui')
class NotebookPage(
            Panel.Widget, ISaveable, IDisconnectable,
            IKernel, ICursor, ILanguage, ICells, ISearchable):
    __gtype_name__ = 'NotebookPage'

    cells_list_box = Gtk.Template.Child()
    list_drop_target = Gtk.Template.Child()
    scrolled_window = Gtk.Template.Child()
    stack = Gtk.Template.Child()

    cache_dir = os.environ["XDG_CACHE_HOME"]

    def __init__(self, _file_path="", **kwargs):
        super().__init__(**kwargs)
        IKernel.__init__(self, **kwargs)

        self.bindings = []

        self.previous_buffer = None

        self.notebook_model = None

        asyncio.create_task(self._load_file(_file_path))

        self.words_provider = WordsCompletionProvider()
        # self.lsp_provider = LSPCompletionProvider()

        self.list_drop_target.set_gtypes([Cell])
        self.list_drop_target.set_actions(Gdk.DragAction.MOVE)

        self.command_line = CommandLine()

        self.list_drop_target.connect("drop", self.on_drop_target_drop)
        self.list_drop_target.connect("motion", self.on_drop_target_motion)
        self.list_drop_target.connect("leave", self.on_drop_target_leave)

        self.cells_list_box.connect(
            "selected-rows-changed", self.on_selected_cell_changed)

        self.set_selected_cell_index(0)

    async def _load_file(self, file_path):
        if file_path:
            self.notebook_model = await asyncio.to_thread(
                Notebook.new_from_file,
                file_path)
        else:
            self.notebook_model = Notebook()

        # self.set_title(self.notebook_model.title)
        self.bindings.append(
            self.notebook_model.bind_property("title", self, "title", 2))

        self.cells_list_box.bind_model(
            self.notebook_model,
            self.create_widgets
        )

        if self.notebook_model.get_n_items() == 0:
            self.add_cell(CellType.CODE)

        self.save_delegate = GenericSaveDelegate(self)
        self.set_save_delegate(self.save_delegate)

        self.set_path(self.get_path())

        self.stack.set_visible_child_name("content")

        self.start_kernel()

        self.set_modified(False)

    def on_selected_cell_changed(self, *args):
        selected_row = self.cells_list_box.get_selected_row()
        if selected_row:
            buffer = selected_row.get_child().buffer

            if self.previous_buffer:
                self.previous_buffer.disconnect_by_func(
                    self.on_cursor_position_changed)

            index = self.get_selected_cell_index()
            buffer.connect(
                "notify::cursor-position",
                self.on_cursor_position_changed, index)

            self.previous_buffer = buffer

            self.emit("cursor-moved", buffer, index + 1)

    def run_cell(self, cell):
        if cell.cell_type != CellType.CODE:
            return

        found, position = self.notebook_model.find(cell)

        if cell.executing:
            return

        if cell.source.startswith("!"):
            cell.reset_output()
            self.command_line.run_command(
                cell.source[1:].split(" "),
                self.run_command_callback,
                cell
            )
        elif self.notebook_model.jupyter_kernel:
            cell.reset_output()
            cell.executing = True
            self.notebook_model.jupyter_kernel.execute(
                cell.source,
                self.run_code_callback,
                cell
            )
        else:
            print(f"can't run code: {self.notebook_model.jupyter_kernel}")

    def run_command_callback(self, line, cell):
        output = Output(OutputType.STREAM)
        output.text = line + '\n'
        cell.add_output(output)

    def run_code_callback(self, msg, cell):
        if msg is None or msg['header'] is None:
            return
        msg_type = msg['header']['msg_type']
        content = msg['content']

        self.set_modified(True)

        if msg_type == 'stream':
            output = Output(OutputType.STREAM)
            output.parse(content)
            cell.add_output(output)

            self.emit("kernel-info-changed")

        elif msg_type == 'execute_input':
            count = content['execution_count']
            cell.execution_count = int(count)

        elif msg_type == 'display_data':
            output = Output(OutputType.DISPLAY_DATA)
            output.parse(content)
            cell.add_output(output)

        elif msg_type == 'update_display_data':
            cell.update_output(content)

        elif msg_type == 'execute_result':
            output = Output(OutputType.EXECUTE_RESULT)
            output.parse(content)
            cell.add_output(output)

        elif msg_type == 'error':
            output = Output(OutputType.ERROR)
            output.parse(content)
            cell.add_output(output)

        elif msg_type == 'status':
            if content['execution_state'] == "idle":
                cell.executing = False
                print("cell finished executing")

    def create_widgets(self, cell):
        cell = CellUI(cell)
        cell.connect("request-delete", self.on_cell_request_delete)
        cell.connect("notify::source", self.on_cell_source_changed)
        cell.add_provider(self.words_provider)
        # cell.add_provider(self.lsp_provider)
        return cell

    def on_cell_source_changed(self, *args):
        self.set_modified(True)

    def on_cell_request_delete(self, cell_ui):
        found, position = self.notebook_model.find(cell_ui.cell)

        if found:
            self.notebook_model.remove(position)
            cell_ui.disconnect_by_func(self.on_cell_request_delete)
            cell_ui.disconnect_by_func(self.on_cell_source_changed)

            del cell_ui

            if self.notebook_model.get_n_items() == 0:
                self.add_cell(Cell(CellType.CODE))
            else:
                row = self.cells_list_box.get_row_at_index(position)
                if row:
                    self.cells_list_box.select_row(row)
                else:
                    row = self.cells_list_box.get_row_at_index(position - 1)
                    if row:
                        self.cells_list_box.select_row(row)

    def add_cell(self, cell_type):
        cell = Cell(cell_type)
        if self.notebook_model.get_n_items() > 1:
            index = self.get_selected_cell_index()
            self.notebook_model.insert(index + 1, cell)
        else:
            self.notebook_model.append(cell)

        self.set_modified(True)

        found, position = self.notebook_model.find(cell)

        if found:
            self.set_selected_cell_index(position)

    def get_selected_cell(self):
        cell_ui = self.cells_list_box.get_selected_row().get_child()
        return cell_ui.cell

    def select_next_cell(self):
        cell = self.get_selected_cell()
        found, position = self.notebook_model.find(cell)
        if found and position != self.notebook_model.get_n_items() - 1:
            self.set_selected_cell_index(position + 1)

    def get_selected_cell_index(self):
        selected_cell = self.cells_list_box.get_selected_row()

        for index in range(0, self.notebook_model.get_n_items()):
            if self.cells_list_box.get_row_at_index(index) == selected_cell:
                return index

        return self.notebook_model.get_n_items() - 1

    def set_selected_cell_index(self, index):
        row = self.cells_list_box.get_row_at_index(index)
        if row:
            self.cells_list_box.select_row(row)

    #
    #   Drag and Drop
    #

    def on_drop_target_drop(self, drop_target, cell, x, y):
        target_row = self.cells_list_box.get_row_at_y(y)

        cell_index = None
        for index, model_cell in enumerate(self.notebook_model):
            if cell == model_cell:
                cell_index = index

        if cell_index:
            self.notebook_model.remove(cell_index)

        if target_row:
            target_index = target_row.get_index()
            self.notebook_model.insert(target_index, cell)
        else:
            self.notebook_model.append(cell)

    def on_drop_target_motion(self, drop_target, x, y):
        target_row = self.cells_list_box.get_row_at_y(y)

        if target_row:
            self.cells_list_box.drag_highlight_row(target_row)

        vadjustment = self.scrolled_window.get_vadjustment()

        visible_height = vadjustment.get_page_size()
        content_height = vadjustment.get_upper()

        current_scroll_position = vadjustment.get_value()

        margin = 50

        relative_y = y - current_scroll_position

        if relative_y < margin:
            delta = (margin - relative_y) / margin * 20
            new_value = max(current_scroll_position - delta, 0)
            vadjustment.set_value(new_value)
        elif relative_y > visible_height - margin:
            delta = (relative_y - (visible_height - margin)) / margin * 20
            new_value = min(
              current_scroll_position + delta, content_height - visible_height)
            vadjustment.set_value(new_value)

        return Gdk.DragAction.MOVE

    def on_drop_target_leave(self, drop_target):
        self.cells_list_box.drag_unhighlight_row()

    #
    #   Implement Language Interface
    #

    def get_language(self):
        kernel = self.get_kernel()
        if kernel:
            self.language = kernel.language
            return self.language
        else:
            return None

    def set_language(self, _language):
        # self.get_kernel().language = _language
        # self.language = _language
        # lang = self.language_manager.get_language(self.language)
        # self.buffer.set_language(lang)
        # self.buffer.set_highlight_syntax(True)

        # TODO Need to ask the kernel to change the language if it make sense
        #           or set as fixed

        self.emit('language-changed')

    #
    #   Implement Cursor Interface
    #

    def on_cursor_position_changed(self, buffer, pos, index):
        self.emit("cursor-moved", buffer, index + 1)

    def get_cursor_position(self):
        row = self.cells_list_box.get_selected_row()
        if row:
            cell_ui = row.get_child()
            buffer = cell_ui.buffer
            index = self.get_selected_cell_index()

            return buffer, index
        return None, 0

    def move_cursor(self, line, column, index):
        index = index - 1
        if index < self.notebook_model.get_n_items():
            row = self.cells_list_box.get_row_at_index(index)
            buffer = row.get_child().buffer

            succ, cursor_iter = buffer.get_iter_at_line_offset(
                line, column)
            if succ:
                self.set_selected_cell_index(index)
                buffer.place_cursor(cursor_iter)

    #
    #   Implement Saveable Page Interface
    #

    def get_path(self):
        return self.notebook_model.get_path()

    def set_path(self, _path):
        self.notebook_model.set_path(_path)
        self.save_delegate.set_subtitle(_path)
        if not _path:
            self.save_delegate.set_is_draft(True)
        else:
            self.save_delegate.set_is_draft(False)

    def get_content(self):
        return nbformat.writes(
            self.notebook_model.get_notebook_node())

    #
    #   Implement Kernel Page Interface
    #

    def set_kernel(self, jupyter_kernel):
        kernel = self.get_kernel()

        if kernel:
            kernel.disconnect_by_func(self.on_kernel_status_changed)

        self.notebook_model.jupyter_kernel = jupyter_kernel
        self.notebook_model.jupyter_kernel.connect(
            "status-changed", self.on_kernel_status_changed)
        self.emit("kernel-info-changed")

    def get_kernel(self):
        if self.notebook_model:
            return self.notebook_model.jupyter_kernel
        return None

    def on_kernel_status_changed(self, kernel, status):
        self.emit("kernel-info-changed")

        if status == "starting":
            for cell in self.notebook_model:
                cell.executing = False

    #
    #   Implement Cells Interface
    #

    def run_selected_cell(self):
        cell = self.get_selected_cell()
        self.run_cell(cell)

    def run_selected_and_advance(self):
        self.run_selected_cell()
        self.select_next_cell()

    def run_all_cells(self):
        for index, cell in enumerate(self.notebook_model):
            if cell.cell_type == CellType.CODE:
                self.run_cell(cell)

    #
    #   Implement Searchable Interface
    #

    def search_text(self):
        for index in range(0, self.notebook_model.get_n_items()):
            cell = self.cells_list_box.get_row_at_index(index).get_child()
            cell.search_text()

    def set_search_text(self, text):
        for index in range(0, self.notebook_model.get_n_items()):
            cell = self.cells_list_box.get_row_at_index(index).get_child()
            cell.set_search_text()

    #
    #   Implement Disconnectable Interface
    #

    def disconnect(self, *args):
        self.list_drop_target.disconnect_by_func(self.on_drop_target_drop)
        self.list_drop_target.disconnect_by_func(self.on_drop_target_motion)
        self.list_drop_target.disconnect_by_func(self.on_drop_target_leave)

        self.cells_list_box.disconnect_by_func(self.on_selected_cell_changed)

        if self.previous_buffer:
            self.previous_buffer.disconnect_by_func(
                self.on_cursor_position_changed)

        for index in range(0, self.notebook_model.get_n_items()):
            cell = self.cells_list_box.get_row_at_index(index).get_child()
            cell.disconnect_by_func(self.on_cell_request_delete)
            cell.disconnect_by_func(self.on_cell_source_changed)
            cell.disconnect()

        kernel = self.get_kernel()
        if kernel:
            kernel.disconnect_by_func(self.on_kernel_status_changed)

        self.cells_list_box.bind_model(
            None,
            None
        )

        for binding in self.bindings:
            binding.unbind()
        del self.bindings

        self.save_delegate.disconnect_all()

        print(f"Disconnected:  {self}")

    def __del__(self):
        print(f"DELETING {self}")
