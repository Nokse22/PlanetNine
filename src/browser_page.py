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

from gi.repository import Gtk, GObject
from gi.repository import Panel, WebKit

import sys

GObject.type_register(WebKit.WebView)

@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/browser_page.ui')
class BrowserPage(Panel.Widget):
    __gtype_name__ = 'BrowserPage'

    __gsignals__ = {
        # 'changed': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.TextBuffer,)),
    }

    web_view = Gtk.Template.Child()
    uri_entry = Gtk.Template.Child()
    toolbar_view = Gtk.Template.Child()
    back_button = Gtk.Template.Child()
    forward_button = Gtk.Template.Child()
    reload_button = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        self.actions_signals = []
        self.bindings = []

        self.connect("unrealize", self.__on_unrealized)

        self.uri_entry.connect("activate", self.on_entry_activated)

        self.back_button.connect("clicked", self.on_back_clicked)
        self.forward_button.connect("clicked", self.on_forward_clicked)
        self.reload_button.connect("clicked", self.on_reload_clicked)

        self.web_view.connect("notify::uri", self.on_uri_changed)
        self.web_view.connect("notify::title", self.on_title_changed)

        self.web_view.load_uri("https://www.gnome.org/")

    @classmethod
    def new_from_html(cls, html_string):
        instance = cls()

        instance.web_view.load_html(html_string)
        instance.toolbar_view.set_reveal_top_bars(False)

        return instance

    def on_entry_activated(self, entry):
        buffer = entry.get_buffer()

        uri = buffer.get_text()

        self.web_view.load_uri(uri)

    def on_uri_changed(self, web_view, *args):
        uri = web_view.get_uri()
        self.uri_entry.get_buffer().set_text(uri, len(uri))
        self.toolbar_view.set_reveal_top_bars(True)

    def on_title_changed(self, web_view, *args):
        self.set_title(web_view.get_title())

    def on_back_clicked(self, *args):
        self.web_view.go_back()

    def on_forward_clicked(self, *args):
        self.web_view.go_forward()

    def on_reload_clicked(self, *args):
        self.web_view.reload()

    def __on_unrealized(self, *args):
        self.web_view.disconnect_by_func(self.on_uri_changed)
        self.back_button.disconnect_by_func(self.on_back_clicked)
        self.forward_button.disconnect_by_func(self.on_forward_clicked)
        self.reload_button.disconnect_by_func(self.on_reload_clicked)
        self.web_view.disconnect_by_func(self.on_title_changed)

        for action, callback in self.actions_signals:
            action.disconnect_by_func(callback)

        for binding in self.bindings:
            binding.unbind()

        self.disconnect_by_func(self.__on_unrealized)

        print("unrealize:", sys.getrefcount(self))

    def __del__(self, *args):
        print(f"DELETING {self}")
