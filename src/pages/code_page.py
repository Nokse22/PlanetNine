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

from gi.repository import Gtk, GObject, Adw, Gio
from gi.repository import Panel, GtkSource
from gi.repository import Spelling

from ..others.save_delegate import GenericSaveDelegate
from ..others.image_loader import ImageLoader
from ..others.style_manager import StyleManager

from ..utils.converters import get_language_highlight_name

from ..interfaces.saveable import ISaveable
from ..interfaces.disconnectable import IDisconnectable
from ..interfaces.kernel import IKernel
from ..interfaces.cursor import ICursor
from ..interfaces.language import ILanguage

import os

GObject.type_register(GtkSource.Map)
GObject.type_register(GtkSource.VimIMContext)


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/code_page.ui')
class CodePage(
            Panel.Widget, ISaveable, IDisconnectable,
            ICursor, IKernel, ILanguage):
    __gtype_name__ = 'CodePage'

    source_view = Gtk.Template.Child()
    code_buffer = Gtk.Template.Child()
    event_controller_key = Gtk.Template.Child()
    command_label = Gtk.Template.Child()
    command_bar_label = Gtk.Template.Child()

    def __init__(self, _path=None):
        super().__init__()

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

        self.code_buffer.connect(
            "notify::cursor-position", self.on_cursor_position_changed)

        self.jupyter_kernel = None

        self.path = _path

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

        self.set_language("python3")

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

        # ADD SAVE DELEGATE

        self.save_delegate = GenericSaveDelegate(self)
        self.set_save_delegate(self.save_delegate)

        if self.path:
            self.save_delegate.set_is_draft(False)

        # LOAD File

        if self.path:
            with open(self.path, 'r') as file:
                content = file.read()

            self.code_buffer.set_text(content)

            self.set_path(_path)

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

        self.code_buffer.connect("changed", self.on_text_changed)

    def get_selected_cell_content(self):
        cursor_iter = self.code_buffer.get_iter_at_mark(
            self.code_buffer.get_insert())

        delimiter = "# %%"

        result = cursor_iter.backward_search(
            delimiter, Gtk.TextSearchFlags.VISIBLE_ONLY, None)

        if result:
            match_start, match_end = result
            match_end.forward_line()
            start_iter = match_end
        else:
            start_iter = self.code_buffer.get_start_iter()

        result = cursor_iter.forward_search(
            delimiter, Gtk.TextSearchFlags.VISIBLE_ONLY, None)

        if result:
            match_start, match_end = result
            match_start.backward_line()
            end_iter = match_start
        else:
            end_iter = self.code_buffer.get_end_iter()

        return self.code_buffer.get_text(start_iter, end_iter, False)

    #
    #
    #

    def run_code_callback(self, msg):
        if msg is None or msg['header'] is None:
            print("No message")
            return
        msg_type = msg['header']['msg_type']
        content = msg['content']

        print(content)

        # TODO add the output somewhere

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

    def on_text_changed(self, *args):
        self.set_modified(True)

    def update_style_scheme(self, *args):
        scheme = self.style_manager.get_current_scheme()
        self.code_buffer.set_style_scheme(scheme)

    #
    #   Implement Language Interface
    #

    def set_language(self, _language):
        self.language = _language

        if self.language + "cells" in self.language_manager.get_language_ids():
            lang = self.language_manager.get_language(self.language + "cells")
        else:
            lang = self.language

        # TODO change the language based on the file mimetype

        self.code_buffer.set_language(lang)
        self.code_buffer.set_highlight_syntax(True)

    #
    #   Implement Cursor Interface
    #

    def on_cursor_position_changed(self, *args):
        self.emit("cursor-moved", self.code_buffer, 0)

    #
    # Implement Kernel Interface
    #

    def get_kernel(self):
        return self.jupyter_kernel

    def set_kernel(self, jupyter_kernel):
        if self.jupyter_kernel:
            self.jupyter_kernel.disconnect_by_func(self.on_kernel_info_changed)

        self.jupyter_kernel = jupyter_kernel
        self.jupyter_kernel.connect(
            "status-changed", self.on_kernel_info_changed)

        self.emit("kernel-info-changed")

    def on_kernel_info_changed(self, *args):
        self.emit("kernel-info-changed")

    #
    #   Implement Saveable Page Interface
    #

    def get_path(self):
        return self.path

    def set_path(self, _path):
        self.path = _path
        self.set_title(
            os.path.basename(self.path) if self.path else "Untitled")
        self.save_delegate.set_is_draft(False)

    def get_content(self):
        start = self.code_buffer.get_start_iter()
        end = self.code_buffer.get_end_iter()
        return self.code_buffer.get_text(start, end, True)

    #
    #   Implement Cells Interface
    #

    def run_selected_cell(self):
        code_portion = self.get_selected_cell_content()
        self.jupyter_kernel.execute(
            code_portion,
            self.run_code_callback
        )

    def run_all_cells(self):
        self.jupyter_kernel.execute(
            self.get_content(),
            self.run_code_callback
        )

    #
    #   Implement Disconnectable Interface
    #

    def disconnect(self, *args):
        self.style_manager.disconnect_by_func(self.update_style_scheme)
        self.code_buffer.disconnect_by_func(self.on_cursor_position_changed)
        self.code_buffer.disconnect_by_func(self.on_text_changed)

        self.save_delegate.disconnect_all()

        if self.jupyter_kernel:
            self.jupyter_kernel.disconnect_by_func(self.on_kernel_info_changed)

        print(f"closing: {self}")

    def __del__(self):
        print(f"DELETING {self}")
