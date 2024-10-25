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

        self.back_button.connect("clicked", self.on_back_clicked_cb)
        self.forward_button.connect("clicked", self.on_forward_clicked_cb)
        self.reload_button.connect("clicked", self.on_reload_clicked_cb)
        self.cancel_reload_button.connect(
            "clicked", self.on_cancel_reload_clicked_cb)

        self.web_view.connect("notify::uri", self.on_uri_changed_cb)
        self.web_view.connect("notify::title", self.on_title_changed_cb)

        self.web_view.connect("create", self.on_open_new_browser_cb)

        if _initial_uri:
            self.web_view.load_uri(_initial_uri)
        elif _initial_uri is None or _initial_uri == "":
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

    def on_entry_activated(self, entry):
        """Handles the activation of the entry and loads the new uri"""
        uri = entry.get_buffer().get_text()

        self.web_view.load_uri(uri)

    def on_uri_changed_cb(self, web_view, *_args):
        """Updates the uri entry with the new web_view uri"""
        uri = web_view.get_uri()
        self.search_entry.get_buffer().set_text(uri, len(uri))
        self.toolbar_view.set_reveal_top_bars(True)

    def on_title_changed_cb(self, web_view, *_args):
        """Updates the page title with the new web_view title"""
        self.set_title(web_view.get_title() or "Browser")

    def on_back_clicked_cb(self, *_args):
        """When the back button has been clicked"""
        self.web_view.go_back()

    def on_forward_clicked_cb(self, *_args):
        """When the forward button has been clicked"""
        self.web_view.go_forward()

    def on_reload_clicked_cb(self, *_args):
        """When the reload button has been clicked"""
        self.web_view.reload()

    def on_cancel_reload_clicked_cb(self, *_args):
        """When the cancel reload button has been clicked"""
        self.web_view.stop_loading()

    def on_open_url(self, action, variant):
        """Handles opening a new url"""
        self.web_view.load_uri(variant.get_string())

    def add_bookmark(self, bookmark_name, bookmark_url):
        """Handles adding a new bookmark to the bookmark menu"""
        menu_item = Gio.MenuItem()
        menu_item.set_label(bookmark_name)
        menu_item.set_action_and_target_value(
            "browser.open", GLib.Variant('s', bookmark_url))
        self.bookmark_menu.append_item(menu_item)

    def on_open_new_browser_cb(self, web_view, navigation_action):
        """Handles opening an url in a new separate page"""
        uri = navigation_action.get_request().get_uri()
        self.activate_action(
            "win.new-browser-page", GLib.Variant('s', uri))

    def create_action_with_target(self, name, target_type, callback):
        """Used to create an action with target"""
        action = Gio.SimpleAction.new(name, target_type)
        action.connect("activate", callback)
        self.action_group.add_action(action)
        self.actions_signals.append((action, callback))
        return action

    #
    #   Implement Disconnectable Interface
    #

    def disconnect(self, *_args):
        """Disconnect all signals"""
        self.back_button.disconnect_by_func(self.on_back_clicked_cb)
        self.forward_button.disconnect_by_func(self.on_forward_clicked_cb)
        self.reload_button.disconnect_by_func(self.on_reload_clicked_cb)
        self.web_view.disconnect_by_func(self.on_title_changed_cb)
        self.web_view.disconnect_by_func(self.on_uri_changed_cb)
        self.web_view.disconnect_by_func(self.on_open_new_browser_cb)
        self.search_entry.disconnect_by_func(self.on_entry_activated)
        self.cancel_reload_button.disconnect_by_func(
            self.on_cancel_reload_clicked_cb)

        for action, callback in self.actions_signals:
            action.disconnect_by_func(callback)
        del self.actions_signals

        for binding in self.bindings:
            binding.unbind()
        del self.bindings

        print(f"Disconnected:  {self}")

    def __del__(self):
        print(f"DELETING {self}")
