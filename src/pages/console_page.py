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

from gi.repository import Gtk, GObject, GLib
from gi.repository import Panel, GtkSource, Spelling

import asyncio

from ..widgets.console_cell import ConsoleCell
from ..models.output import Output, OutputType
from ..completion_providers.completion_providers import LSPCompletionProvider
from ..completion_providers.completion_providers import WordsCompletionProvider

from ..utils.converters import get_language_highlight_name

from ..interfaces.disconnectable import IDisconnectable
from ..interfaces.kernel import IKernel
from ..interfaces.cursor import ICursor
from ..interfaces.style_update import IStyleUpdate
from ..interfaces.language import ILanguage

GObject.type_register(Panel.Widget)


@Gtk.Template(
    resource_path='/io/github/nokse22/PlanetNine/gtk/console_page.ui')
class ConsolePage(
        Panel.Widget, IDisconnectable, IKernel, ICursor, IStyleUpdate,
        ILanguage):
    __gtype_name__ = 'ConsolePage'

    source_view = Gtk.Template.Child()
    buffer = Gtk.Template.Child()
    send_button = Gtk.Template.Child()
    run_list_box = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        IKernel.__init__(self, **kwargs)
        ICursor.__init__(self, **kwargs)
        IStyleUpdate.__init__(self, **kwargs)
        ILanguage.__init__(self, **kwargs)

        self.jupyter_kernel = None

        self.actions_signals = []
        self.bindings = []

        self.send_button.connect("clicked", self.on_send_clicked)

        # SET LANGUAGE

        self.set_language("python3")

        # ENABLE SPELL CHECK

        checker = Spelling.Checker.get_default()
        adapter = Spelling.TextBufferAdapter.new(self.buffer, checker)
        extra_menu = adapter.get_menu_model()

        self.source_view.set_extra_menu(extra_menu)
        self.source_view.insert_action_group('spelling', adapter)

        adapter.set_enabled(True)

        # ADD COMPLETION PROVIDERS

        completion = self.source_view.get_completion()

        completion_words = WordsCompletionProvider()
        completion_words.register(self.buffer)

        completion.add_provider(completion_words)
        # completion.add_provider(LSPCompletionProvider())

        asyncio.create_task(self._start_kernel())

    async def _start_kernel(self):
        self.start_kernel()

    #
    #
    #

    def on_send_clicked(self, *args):
        self.run_code()

    def run_code(self):
        content = self.get_content()

        if content == "":
            return

        # if content.startswith("!"):
            # self.reset_output()
            # self.command_line.run_command(
            #     content[1:].split(" "),
            #     self.run_command_callback,
            #     cell
            # )
            # pass
        if self.jupyter_kernel:
            cell = self.add_run_cell(content)
            self.buffer.set_text("")
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

        print("CONSOLE: ", content)

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
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        return self.buffer.get_text(start, end, True)

    def disconnect(self, *args):
        self.style_manager.disconnect_by_func(self.update_style_scheme)
        self.send_button.disconnect_by_func(self.on_send_clicked)
        self.buffer.disconnect_by_func(self.on_cursor_position_changed)

        if self.jupyter_kernel:
            self.jupyter_kernel.disconnect_by_func(self.on_kernel_info_changed)

        for action, callback in self.actions_signals:
            action.disconnect_by_func(callback)
        del self.actions_signals

        for binding in self.bindings:
            binding.unbind()
        del self.bindings

        print(f"Disconnected:  {self}")

    def __del__(self, *args):
        print(f"DELETING {self}")
