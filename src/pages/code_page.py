# code_page.py
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

from gi.repository import Gtk, GObject, Gio
from gi.repository import Panel, GtkSource
from gi.repository import Spelling

from ..others.image_loader import ImageLoader

from ..completion_providers.completion_providers import WordsCompletionProvider
from ..completion_providers.kernel_completion import KernelCompletionProvider

from ..interfaces.saveable import ISaveable
from ..interfaces.disconnectable import IDisconnectable
from ..interfaces.kernel import IKernel
from ..interfaces.cursor import ICursor
from ..interfaces.language import ILanguage
from ..interfaces.cells import ICells
from ..interfaces.searchable import ISearchable
from ..interfaces.style_update import IStyleUpdate

import asyncio

GObject.type_register(GtkSource.Map)
GObject.type_register(GtkSource.VimIMContext)


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/code_page.ui')
class CodePage(
        Panel.Widget, ISaveable, IDisconnectable, IStyleUpdate,
        ICursor, IKernel, ILanguage, ICells, ISearchable):
    __gtype_name__ = 'CodePage'

    source_view = Gtk.Template.Child()
    buffer = Gtk.Template.Child()
    event_controller_key = Gtk.Template.Child()
    command_label = Gtk.Template.Child()
    command_bar_label = Gtk.Template.Child()

    def __init__(self, file_path=None, **kwargs):
        super().__init__(**kwargs)
        IKernel.__init__(self, **kwargs)
        ISearchable.__init__(self)
        ICursor.__init__(self)
        IStyleUpdate.__init__(self)
        ISaveable.__init__(self)
        IDisconnectable.__init__(self)

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

        self.path = file_path

        # SETUP VIM

        # self.settings.connect('notify::code-vim', self.on_code_vim_changed)
        # self.default_im_context = self.event_controller_key.get_im_context()

        if self.settings.get_boolean('code-vim'):
            vim_im_context = GtkSource.VimIMContext()

            self.event_controller_key.set_im_context(vim_im_context)
            self.event_controller_key.set_propagation_phase(
                Gtk.PropagationPhase.CAPTURE)
            vim_im_context.set_client_widget(self.source_view)

            vim_im_context.bind_property(
                "command-bar-text", self.command_bar_label, "label")
            vim_im_context.bind_property(
                "command-text", self.command_label, "label")
        else:
            self.command_bar_label.set_visible(False)
            self.command_label.set_visible(False)

        # SET THE LANGUAGE and STYLE SCHEME

        self.language_manager = GtkSource.LanguageManager()
        self.language_manager.append_search_path(
            "resource:///io/github/nokse22/PlanetNine/custom_languages/")

        # ENABLE SPELL CHECK

        checker = Spelling.Checker.get_default()
        adapter = Spelling.TextBufferAdapter.new(self.buffer, checker)
        extra_menu = adapter.get_menu_model()

        self.source_view.set_extra_menu(extra_menu)
        self.source_view.insert_action_group('spelling', adapter)

        adapter.set_enabled(True)

        # Add Providers

        self.words_provider = WordsCompletionProvider()

        self.words_provider.register(self.buffer)
        self.source_view.get_completion().add_provider(self.words_provider)

        self.kernel_provider = KernelCompletionProvider(self)

        self.kernel_provider.register(self.buffer)
        self.source_view.get_completion().add_provider(self.kernel_provider)

        # LOAD File

        asyncio.create_task(self.ov_load_file(file_path))

        # VIEW SETTINGS

        self.settings.bind(
            'code-line-number',
            self.source_view,
            'show-line-numbers',
            Gio.SettingsBindFlags.DEFAULT
        )
        self.settings.bind(
            'code-highlight-row',
            self.source_view,
            'highlight-current-line',
            Gio.SettingsBindFlags.DEFAULT
        )

    async def ov_load_file(self, file_path):
        await self.load_file(file_path)

        self.start_kernel()

    def get_selected_cell_content(self):
        """Returns the selected cell content"""

        cursor_iter = self.buffer.get_iter_at_mark(
            self.buffer.get_insert())

        delimiter = "# %%"

        result = cursor_iter.backward_search(
            delimiter, Gtk.TextSearchFlags.VISIBLE_ONLY, None)

        if result:
            match_start, match_end = result
            match_end.forward_line()
            start_iter = match_end
        else:
            start_iter = self.buffer.get_start_iter()

        result = cursor_iter.forward_search(
            delimiter, Gtk.TextSearchFlags.VISIBLE_ONLY, None)

        if result:
            match_start, match_end = result
            match_start.backward_line()
            end_iter = match_start
        else:
            end_iter = self.buffer.get_end_iter()

        return self.buffer.get_text(start_iter, end_iter, False)

    def go_to_next_cell(self):
        cursor_iter = self.buffer.get_iter_at_mark(
            self.buffer.get_insert())

        delimiter = "# %%"

        result = cursor_iter.forward_search(
            delimiter, Gtk.TextSearchFlags.VISIBLE_ONLY, None)

        if result:
            match_start, match_end = result
            match_end.forward_line()

            self.buffer.place_cursor(match_end)

    #
    #
    #

    def run_code_callback(self, msg):
        """Callback to receive messages from the kernel"""

        if msg is None or msg['header'] is None:
            print("No message")
            return
        msg_type = msg['header']['msg_type']
        content = msg['content']

        print(content)

        if msg_type == 'stream':
            print("Stream")

        elif msg_type == 'execute_input':
            print("execute_input")

        elif msg_type == 'display_data':
            loader = ImageLoader()
            loader.load_from_base64(None, content)

        elif msg_type == 'execute_result':
            print("execute_input")

        elif msg_type == 'error':
            print("ERROR: \n", content)

    #
    #   Implement Language Interface
    #

    def set_language(self, _language):
        """Overrides the ILanguage interface set_language method to use
        custom language definition that supports highlighting cells"""

        self.language = _language

        if self.language + "cells" in self.language_manager.get_language_ids():
            lang = self.language_manager.get_language(self.language + "cells")
        else:
            lang = self.language_manager.get_language(self.language)

        self.buffer.set_language(lang)
        self.buffer.set_highlight_syntax(True)

        self.emit('language-changed')

    #
    #   Implement Cells Interface
    #

    def run_selected_cell(self):
        """Runs the currently selected cell"""

        code_portion = self.get_selected_cell_content()
        self.get_kernel().execute(
            code_portion,
            self.run_code_callback
        )

    def run_selected_and_advance(self):
        """Runs current cell and moves the cursor to the next cell"""

        self.run_selected_cell()
        self.go_to_next_cell()

    def run_all_cells(self):
        """Runs the entire script"""

        self.get_kernel().execute(
            self.get_content(),
            self.run_code_callback
        )

    # Only for code page
    def run_line(self):
        """Runs the current line where is the cursor"""

        start_iter = self.buffer.get_iter_at_mark(
            self.buffer.get_insert())

        start_iter.set_line_offset(0)
        end_iter = start_iter.copy()
        end_iter.forward_to_line_end()

        code_portion = self.buffer.get_text(start_iter, end_iter, False)

        self.get_kernel().execute(
            code_portion,
            self.run_code_callback
        )

    def add_cell(self, cell_type):
        """Add a cell to the page

        :param CellType cell_type: the type of cell to add
        """

        self.buffer.begin_user_action()

        bounds = self.buffer.get_selection_bounds()
        start, end = None, None
        if bounds:
            start, end = bounds

        if bounds and start != end:
            start_line = start.get_line()
            end_line = end.get_line()

            succ, iter_start = self.buffer.get_iter_at_line(start_line)
            self.buffer.insert(iter_start, "# %%\n")

            succ, iter_end = self.buffer.get_iter_at_line(end_line)
            iter_end.forward_to_line_end()
            iter_end.forward_line()
            iter_end.forward_line()
            self.buffer.insert(iter_end, "# %%\n")
        else:
            cursor = self.buffer.get_iter_at_mark(
                self.buffer.get_insert())
            line = cursor.get_line()
            succ, iter_line = self.buffer.get_iter_at_line(line)
            self.buffer.insert(iter_line, "# %%\n")

        self.buffer.set_modified(True)

        self.buffer.end_user_action()

    #
    #   Implement Disconnectable Interface
    #

    def disconnect(self, *_args):
        """Disconnect all signals"""

        IDisconnectable.disconnect(self)
        IStyleUpdate.disconnect(self)
        ICursor.disconnect(self)
        ISaveable.disconnect(self)

        print(f"Disconnected:  {self}")

    def __del__(self):
        print(f"DELETING {self}")
