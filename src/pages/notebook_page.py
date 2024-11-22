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
from ..completion_providers.kernel_completion import KernelCompletionProvider
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
        ISearchable.__init__(self, True)
        ICursor.__init__(self, True)
        ISaveable.__init__(self, True)
        ILanguage.__init__(self)
        IDisconnectable.__init__(self)

        self.bindings = []

        self.previous_buffer = None

        self.notebook_model = None

        asyncio.create_task(self.load_file(_file_path))

        self.words_provider = WordsCompletionProvider()
        # self.lsp_provider = LSPCompletionProvider()
        self.kernel_provider = KernelCompletionProvider(self)

        self.list_drop_target.set_gtypes([Cell])
        self.list_drop_target.set_actions(Gdk.DragAction.MOVE)

        self.command_line = CommandLine()

        self.list_drop_target.connect("drop", self.on_drop_target_drop)
        self.list_drop_target.connect("motion", self.on_drop_target_motion)
        self.list_drop_target.connect("leave", self.on_drop_target_leave)

        self.cells_list_box.connect(
            "selected-rows-changed", self.on_selected_cell_changed)

        self.set_selected_cell_index(0)

    async def load_file(self, file_path):
        """Load a file"""

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

    def on_selected_cell_changed(self, *_args):
        """Handles when the selected cell has changed"""

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
        """Handles running a cell"""

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
        elif self.get_kernel():
            cell.reset_output()
            cell.executing = True
            self.get_kernel().execute(
                cell.source,
                self.run_code_callback,
                cell
            )
        else:
            print(f"can't run code: {self.get_kernel()}")

    def run_command_callback(self, line, cell):
        """Callback to running a command for a cell"""

        output = Output(OutputType.STREAM)
        output.text = line + '\n'
        cell.add_output(output)

    def run_code_callback(self, msg, cell):
        """Callback to running the code in a cell"""

        if msg is None or msg['header'] is None:
            return
        msg_type = msg['header']['msg_type']
        content = msg['content']

        self.set_modified(True)

        if msg_type == 'stream':
            output = Output(OutputType.STREAM)
            output.parse(content)
            cell.add_output(output)

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
        """Create widgets for the Gtk.ListBox"""

        cell = CellUI(cell)
        cell.connect("request-delete", self.on_cell_request_delete)
        cell.connect("notify::source", self.on_cell_source_changed)
        cell.add_provider(self.words_provider)
        cell.add_provider(self.kernel_provider)
        kernel = self.get_kernel()
        if kernel:
            cell.set_language(kernel.language)
        return cell

    def on_cell_source_changed(self, *_args):
        """Sets the page status to modified when a cell content has changed"""

        self.set_modified(True)

    def on_cell_request_delete(self, cell_ui):
        """Handle the request of deletion of a cell"""

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
        """Adds a cell of type cell_type to the notebook_model"""

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
        """Return the selected cell"""

        cell_ui = self.cells_list_box.get_selected_row().get_child()
        return cell_ui.cell

    def select_next_cell(self):
        """Selects the next cell"""

        cell = self.get_selected_cell()
        found, position = self.notebook_model.find(cell)
        if found and position != self.notebook_model.get_n_items() - 1:
            self.set_selected_cell_index(position + 1)

    def get_selected_cell_index(self):
        """Returns the index of the selected cell"""

        selected_cell = self.cells_list_box.get_selected_row()

        for index in range(0, self.notebook_model.get_n_items()):
            if self.cells_list_box.get_row_at_index(index) == selected_cell:
                return index

        return self.notebook_model.get_n_items() - 1

    def set_selected_cell_index(self, index):
        """Sets the selected cell from an index"""

        row = self.cells_list_box.get_row_at_index(index)
        if row:
            self.cells_list_box.select_row(row)

    #
    #   Drag and Drop
    #

    def on_drop_target_drop(self, drop_target, cell, x, y):
        """Handles dropping a cell into cells_list_box"""

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
        """Handles moving on cells_list_box while a drag and drop operation"""

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
                current_scroll_position + delta,
                content_height - visible_height)
            vadjustment.set_value(new_value)

        return Gdk.DragAction.MOVE

    def on_drop_target_leave(self, drop_target):
        """Handles leaving cells_list_box while a drag and drop operation"""

        self.cells_list_box.drag_unhighlight_row()

    #
    #   Implement Language Interface
    #

    def get_language(self):
        """Overrides the get_language method of ILanguage"""

        kernel = self.get_kernel()
        if kernel:
            self.language = kernel.language
            return self.language
        else:
            return None

    def set_language(self, _language):
        """Overrides the set_language method of ILanguage"""

        self.language = _language

        for index in range(0, self.notebook_model.get_n_items()):
            cell = self.cells_list_box.get_row_at_index(index).get_child()
            cell.set_language(self.language)

        self.emit('language-changed')

    #
    #   Implement Cursor Interface
    #

    def on_cursor_position_changed(self, buffer, pos, index):
        """Emits cursor-moved signal when the cursor position changes"""

        self.emit("cursor-moved", buffer, index + 1)

    def get_cursor_position(self):
        """Returns the currently selected buffer and cell"""

        row = self.cells_list_box.get_selected_row()
        if row:
            cell_ui = row.get_child()
            buffer = cell_ui.buffer
            index = self.get_selected_cell_index()

            return buffer, index
        return None, 0

    def move_cursor(self, line, column, index):
        """Handles moving the cursor to a cell position"""

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
        """Overrides the get_path of the ISaveable interface"""

        return self.notebook_model.get_path()

    def set_path(self, _path):
        """Overrides the set_path of the ISaveable interface"""

        self.notebook_model.set_path(_path)
        self.save_delegate.set_subtitle(_path)
        if not _path:
            self.save_delegate.set_is_draft(True)
        else:
            self.save_delegate.set_is_draft(False)

    def get_content(self):
        """Overrides the get_content of the ISaveable interface"""

        return nbformat.writes(
            self.notebook_model.get_notebook_node())

    #
    #   Implement Kernel Page Interface
    #

    def on_kernel_status_changed(self, kernel, status):
        """Overrides the on_kernel_status_changed of the IKernel interface"""

        if status == "starting":
            for cell in self.notebook_model:
                cell.executing = False

    #
    #   Implement Cells Interface
    #

    def run_selected_cell(self):
        """Overrides the run_selected_cell of the ICells interface"""

        cell = self.get_selected_cell()
        self.run_cell(cell)

    def run_selected_and_advance(self):
        """Overrides the run_selected_and_advance of the ICells interface"""

        self.run_selected_cell()
        self.select_next_cell()

    def run_all_cells(self):
        """Overrides the run_all_cells of the ICells interface"""

        for index, cell in enumerate(self.notebook_model):
            if cell.cell_type == CellType.CODE:
                self.run_cell(cell)

    #
    #   Implement Searchable Interface
    #

    def search_text(self):
        """Overrides the search_text of the ISearchable interface"""

        for index in range(0, self.notebook_model.get_n_items()):
            cell = self.cells_list_box.get_row_at_index(index).get_child()
            cell.search_text()

    def set_search_text(self, text):
        """Overrides the set_search_text of the ISearchable interface"""

        for index in range(0, self.notebook_model.get_n_items()):
            cell = self.cells_list_box.get_row_at_index(index).get_child()
            cell.set_search_text(text)

    #
    #   Implement Disconnectable Interface
    #

    def disconnect(self, *_args):
        """Disconnect all signals"""

        IDisconnectable.disconnect(self)

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

        self.cells_list_box.bind_model(
            None,
            None
        )

        self.save_delegate.disconnect_all()

        print(f"Disconnected:  {self}")

    def __del__(self):
        print(f"DELETING {self}")

