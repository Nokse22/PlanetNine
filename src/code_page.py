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

from gi.repository import Gtk, GObject, Adw
from gi.repository import Panel, GtkSource
from gi.repository import Spelling

from .converters import get_language_highlight_name

import sys

GObject.type_register(GtkSource.Map)
GObject.type_register(GtkSource.VimIMContext)


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/code_page.ui')
class CodePage(Panel.Widget):
    __gtype_name__ = 'CodePage'

    __gsignals__ = {
        'kernel-info-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    source_view = Gtk.Template.Child()
    code_buffer = Gtk.Template.Child()
    event_controller_key = Gtk.Template.Child()
    command_label = Gtk.Template.Child()
    command_bar_label = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        self.connect("unrealize", self.__on_unrealized)

        # SETUP VIM

        self.vim_im_context = GtkSource.VimIMContext()

        self.event_controller_key.set_im_context(self.vim_im_context)
        self.event_controller_key.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.vim_im_context.set_client_widget(self.source_view)

        self.vim_im_context.bind_property("command-bar-text", self.command_bar_label, "label")
        self.vim_im_context.bind_property("command-text", self.command_label, "label")

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

        self.jupyter_kernel = jupyter_kernel
        self.jupyter_kernel.connect("status-changed", lambda *args: self.emit("kernel-info-changed"))

        self.emit("kernel-info-changed")

    def get_kernel(self):
        return self.jupyter_kernel

    def __on_unrealized(self, *args):
        self.style_manager.disconnect_by_func(self.update_style_scheme)

        self.disconnect_by_func(self.__on_unrealized)

        print("unrealize:", sys.getrefcount(self))

    def __del__(self, *args):
        print(f"DELETING {self}")
