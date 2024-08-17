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

GObject.type_register(WebKit.WebView)

@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/browser_page.ui')
class BrowserPage(Panel.Widget):
    __gtype_name__ = 'BrowserPage'

    __gsignals__ = {
        # 'changed': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.TextBuffer,)),
    }

    web_kit_view = Gtk.Template.Child()
    uri_entry = Gtk.Template.Child()
    toolbar_view = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        self.web_kit_view.load_uri("https://www.gnome.org/")

        self.web_kit_view.connect("notify::uri", self.on_uri_changed)

    @classmethod
    def new_from_html(cls, html_string):
        instance = cls()

        instance.web_kit_view.load_html(html_string)
        instance.toolbar_view.set_reveal_top_bars(False)

        return instance

    def on_uri_changed(self, web_view, *args):
        uri = web_view.get_uri()
        self.uri_entry.get_buffer().set_text(uri, len(uri))
        self.toolbar_view.set_reveal_top_bars(True)

    def __on_unrealized(self, *args):
        pass

    def __del__(self, *args):
        print(f"DELETING {self}")
