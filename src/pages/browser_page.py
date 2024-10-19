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

from gi.repository import Gtk, GObject, Gio, GLib
from gi.repository import Panel, WebKit

from ..interfaces.disconnectable import IDisconnectable

from ..others.no_save_delegate import NoSaveDelegate

GObject.type_register(WebKit.WebView)


@Gtk.Template(
    resource_path='/io/github/nokse22/PlanetNine/gtk/browser_page.ui')
class BrowserPage(Panel.Widget, IDisconnectable):
    __gtype_name__ = 'BrowserPage'

    __gsignals__ = {
        # 'changed': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.TextBuffer,)),
    }

    web_view = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    toolbar_view = Gtk.Template.Child()
    back_button = Gtk.Template.Child()
    forward_button = Gtk.Template.Child()
    reload_button = Gtk.Template.Child()
    bookmark_menu = Gtk.Template.Child()
    cancel_reload_button = Gtk.Template.Child()

    def __init__(self, _initial_uri=None):
        super().__init__()

        self.actions_signals = []
        self.bindings = []

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

        self.save_delagate = NoSaveDelegate()
        self.set_save_delegate(self.save_delagate)
        self.set_modified(False)

        self.search_entry.connect("activate", self.on_entry_activated)

        self.back_button.connect("clicked", self.on_back_clicked)
        self.forward_button.connect("clicked", self.on_forward_clicked)
        self.reload_button.connect("clicked", self.on_reload_clicked)
        self.cancel_reload_button.connect(
            "clicked", self.on_cancel_reload_clicked)

        self.web_view.connect("notify::uri", self.on_uri_changed)
        self.web_view.connect("notify::title", self.on_title_changed)

        self.web_view.connect("create", self.on_open_new_browser)

        if _initial_uri:
            self.web_view.load_uri(_initial_uri)
        else:
            self.web_view.load_uri(
                self.settings.get_string('browser-default-url'))

        self.action_group = Gio.SimpleActionGroup()
        self.toolbar_view.insert_action_group("browser", self.action_group)

        self.create_action_with_target(
            'open', GLib.VariantType.new("s"), self.on_open_url)

        self.bookmarks = [
            ('Duck Duck Go', 'https://start.duckduckgo.com/'),
            ('GNOME', 'https://www.gnome.org/'),
            ('Python Tutorials', 'https://docs.python.org/3/tutorial')
        ]

        for name, url in self.bookmarks:
            self.add_bookmark(name, url)

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
        self.search_entry.get_buffer().set_text(uri, len(uri))
        self.toolbar_view.set_reveal_top_bars(True)

    def on_title_changed(self, web_view, *args):
        self.set_title(web_view.get_title() or "Browser")

    def on_back_clicked(self, *args):
        self.web_view.go_back()

    def on_forward_clicked(self, *args):
        self.web_view.go_forward()

    def on_reload_clicked(self, *args):
        self.web_view.reload()

    def on_cancel_reload_clicked(self, *args):
        self.web_view.stop_loading()

    def on_open_url(self, action, variant):
        self.web_view.load_uri(variant.get_string())

    def add_bookmark(self, bookmark_name, bookmark_url):
        menu_item = Gio.MenuItem()
        menu_item.set_label(bookmark_name)
        menu_item.set_action_and_target_value(
            "browser.open", GLib.Variant('s', bookmark_url))
        self.bookmark_menu.append_item(menu_item)

    def on_open_new_browser(self, web_view, navigation_action):
        uri = navigation_action.get_request().get_uri()
        self.activate_action(
            "win.new-browser-page", GLib.Variant('s', uri))

    def create_action_with_target(self, name, target_type, callback):
        action = Gio.SimpleAction.new(name, target_type)
        action.connect("activate", callback)
        self.action_group.add_action(action)
        self.actions_signals.append((action, callback))
        return action

    #
    #   Implement Disconnectable Interface
    #

    def disconnect(self, *args):
        self.back_button.disconnect_by_func(self.on_back_clicked)
        self.forward_button.disconnect_by_func(self.on_forward_clicked)
        self.reload_button.disconnect_by_func(self.on_reload_clicked)
        self.web_view.disconnect_by_func(self.on_title_changed)
        self.web_view.disconnect_by_func(self.on_uri_changed)
        self.web_view.disconnect_by_func(self.on_open_new_browser)
        self.search_entry.disconnect_by_func(self.on_entry_activated)
        self.cancel_reload_button.disconnect_by_func(
            self.on_cancel_reload_clicked)

        for action, callback in self.actions_signals:
            action.disconnect_by_func(callback)
        del self.actions_signals

        for binding in self.bindings:
            binding.unbind()
        del self.bindings

        print(f"Disconnected:  {self}")

    def __del__(self):
        print(f"DELETING {self}")
