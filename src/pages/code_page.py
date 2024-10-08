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

from ..utils.converters import get_language_highlight_name

import sys

GObject.type_register(GtkSource.Map)
GObject.type_register(GtkSource.VimIMContext)


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/code_page.ui')
class CodePage(Panel.Widget):
    __gtype_name__ = 'CodePage'

    __gsignals__ = {
        'kernel-info-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'cursor-moved':
            (GObject.SignalFlags.RUN_FIRST, None, (Gtk.TextBuffer, int))
    }

    source_view = Gtk.Template.Child()
    code_buffer = Gtk.Template.Child()
    event_controller_key = Gtk.Template.Child()
    command_label = Gtk.Template.Child()
    command_bar_label = Gtk.Template.Child()

    def __init__(self, _path=None):
        super().__init__()

        self.connect("unrealize", self.__on_unrealized)

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

        # SET THE LANGUAGE STYLE SCHEME

        lm = GtkSource.LanguageManager()
        lang = lm.get_language("python3")
        self.code_buffer.set_language(lang)
        self.code_buffer.set_highlight_syntax(True)

        sm = GtkSource.StyleSchemeManager()
        scheme = sm.get_scheme("Adwaita-dark")
        self.code_buffer.set_style_scheme(scheme)

        self.style_manager = Adw.StyleManager.get_default()
        self.style_manager.connect("notify::dark", self.update_style_scheme)
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

        if not self.path:
            self.save_delegate.set_is_draft(True)

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

    def on_text_changed(self, *args):
        self.set_modified(True)

    def on_cursor_position_changed(self, *args):
        self.emit("cursor-moved", self.code_buffer, 0)

    def update_style_scheme(self, *args):
        scheme_name = "Adwaita"
        if Adw.StyleManager.get_default().get_dark():
            scheme_name += "-dark"
        sm = GtkSource.StyleSchemeManager()
        scheme = sm.get_scheme(scheme_name)
        self.code_buffer.set_style_scheme(scheme)

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

    def on_kernel_info_changed(self, *args):
        self.emit("kernel-info-changed")

    def get_kernel(self):
        return self.jupyter_kernel

    def get_path(self):
        return self.path

    def set_path(self, _path):
        self.path = _path

    def get_content(self):
        return

    def __on_unrealized(self, *args):
        self.style_manager.disconnect_by_func(self.update_style_scheme)
        self.code_buffer.disconnect_by_func(self.on_cursor_position_changed)

        self.save_delegate.unbind_all()

        if self.jupyter_kernel:
            self.jupyter_kernel.disconnect_by_func(self.on_kernel_info_changed)

        self.disconnect_by_func(self.__on_unrealized)

        print("unrealize:", sys.getrefcount(self))

    def __del__(self, *args):
        print(f"DELETING {self}")
