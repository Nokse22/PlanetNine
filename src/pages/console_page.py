# console_page.py
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

from gi.repository import Gtk, GObject, Adw
from gi.repository import Panel, GtkSource, Spelling

import sys

from ..widgets.console_cell import ConsoleCell
from ..models.output import Output, OutputType
from ..completion_providers.completion_providers import LSPCompletionProvider, WordsCompletionProvider

from ..utils.converters import get_language_highlight_name

from ..others.style_manager import StyleManager

from ..interfaces.disconnectable import IDisconnectable
from ..interfaces.kernel import IKernel
from ..interfaces.cursor import ICursor

GObject.type_register(Panel.Widget)


@Gtk.Template(
    resource_path='/io/github/nokse22/PlanetNine/gtk/console_page.ui')
class ConsolePage(Panel.Widget, IDisconnectable, IKernel, ICursor):
    __gtype_name__ = 'ConsolePage'

    source_view = Gtk.Template.Child()
    code_buffer = Gtk.Template.Child()
    send_button = Gtk.Template.Child()
    run_list_box = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        self.jupyter_kernel = None

        self.actions_signals = []
        self.bindings = []

        self.send_button.connect("clicked", self.on_send_clicked)

        self.code_buffer.connect(
            "notify::cursor-position", self.on_cursor_position_changed)

        # SET HIGHLIGHT AND LANGUAGE

        lm = GtkSource.LanguageManager()
        lang = lm.get_language("python3")
        self.code_buffer.set_language(lang)
        self.code_buffer.set_highlight_syntax(True)

        self.style_manager = StyleManager()
        self.style_manager.connect("style-changed", self.update_style_scheme)
        self.update_style_scheme()

        # ENABLE SPELL CHECK

        checker = Spelling.Checker.get_default()
        adapter = Spelling.TextBufferAdapter.new(self.code_buffer, checker)
        extra_menu = adapter.get_menu_model()

        self.source_view.set_extra_menu(extra_menu)
        self.source_view.insert_action_group('spelling', adapter)

        adapter.set_enabled(True)

        # ADD COMPLETION PROVIDERS

        completion = self.source_view.get_completion()

        completion_words = WordsCompletionProvider()
        completion_words.register(self.code_buffer)

        completion.add_provider(completion_words)
        # completion.add_provider(LSPCompletionProvider())

    #
    #   Implement Cursor Interface
    #

    def on_cursor_position_changed(self, *args):
        self.emit("cursor-moved", self.code_buffer, 0)

    def get_cursor_position(self):
        return self.code_buffer, 0

    def move_cursor(self, line, column, _index=0):
        succ, cursor_iter = self.code_buffer.get_iter_at_line_offset(
            line, column)
        if succ:
            self.code_buffer.place_cursor(cursor_iter)

    #
    # Implement Kernel Interface
    #

    def set_kernel(self, jupyter_kernel):
        lm = GtkSource.LanguageManager()
        lang_name = get_language_highlight_name(jupyter_kernel.language)
        lang = lm.get_language(lang_name)
        self.code_buffer.set_language(lang)

        if self.jupyter_kernel:
            self.jupyter_kernel.disconnect_by_func(self.on_kernel_info_changed)

        self.jupyter_kernel = jupyter_kernel
        self.jupyter_kernel.connect(
            "status-changed", self.on_kernel_info_changed)

        self.emit("kernel-info-changed")

    def get_kernel(self):
        return self.jupyter_kernel

    def on_kernel_info_changed(self, *args):
        self.emit("kernel-info-changed")

    #
    #
    #

    def update_style_scheme(self, *args):
        scheme = self.style_manager.get_current_scheme()
        self.code_buffer.set_style_scheme(scheme)

    def on_send_clicked(self, *args):
        self.run_code()

    def run_code(self):
        content = self.get_content()

        if content == "":
            return

        if content.startswith("!"):
            # self.reset_output()
            # self.command_line.run_command(
            #     content[1:].split(" "),
            #     self.run_command_callback,
            #     cell
            # )
            pass
        elif self.jupyter_kernel:
            cell = self.add_run_cell(content)
            self.code_buffer.set_text("")
            self.jupyter_kernel.execute(
                content,
                self.run_code_callback,
                cell
            )

    # def run_command_callback(self, line, cell):
    #     output = Output(OutputType.STREAM)
    #     output.text = line + '\n'
    #     cell.add_output(output)

    def run_code_callback(self, msg, cell):
        msg_type = msg['header']['msg_type']
        content = msg['content']

        if msg_type == 'stream':
            output = Output(OutputType.STREAM)
            output.parse(content)
            cell.add_output(output)

        elif msg_type == 'execute_input':
            count = content['execution_count']
            cell.execution_count = int(count)
            cell.reset_output()

        elif msg_type == 'display_data':
            output = Output(OutputType.DISPLAY_DATA)
            output.parse(content)
            cell.add_output(output)

        elif msg_type == 'error':
            output = Output(OutputType.ERROR)
            output.parse(content)
            cell.add_output(output)

    def add_run_cell(self, content):
        cell = ConsoleCell(content)
        lang_name = get_language_highlight_name(self.jupyter_kernel.language)
        cell.set_language(lang_name)
        self.run_list_box.append(cell)
        return cell

    def get_content(self):
        start = self.code_buffer.get_start_iter()
        end = self.code_buffer.get_end_iter()
        return self.code_buffer.get_text(start, end, True)

    def disconnect(self, *args):
        self.style_manager.disconnect_by_func(self.update_style_scheme)
        self.send_button.disconnect_by_func(self.on_send_clicked)
        self.code_buffer.disconnect_by_func(self.on_cursor_position_changed)

        if self.jupyter_kernel:
            self.jupyter_kernel.disconnect_by_func(self.on_kernel_info_changed)

        for action, callback in self.actions_signals:
            action.disconnect_by_func(callback)
        del self.actions_signals

        for binding in self.bindings:
            binding.unbind()
        del self.bindings

        print("unrealize:", sys.getrefcount(self))

    def __del__(self, *args):
        print(f"DELETING {self}")
