# kernel_terminal_panel.py
#
# Copyright 2024 Nokse22
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gtk, Panel, Adw, Gdk, Vte


class TerminalPanel(Panel.Widget):
    __gtype_name__ = 'TerminalPanel'

    def __init__(self):
        super().__init__()

        self.set_icon_name("terminal-symbolic")

        self.vte_terminal = Vte.Terminal(
            hexpand=True,
            vexpand=True,
            font_scale=0.8,
            scrollback_lines=1000
        )

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_child(self.vte_terminal)

        self.set_child(scrolled_window)

        # Style Manager to update when dark/light

        self.style_manager = Adw.StyleManager.get_default()
        self.style_manager.connect("notify::dark", self.update_style_scheme)
        self.update_style_scheme()

    def feed(self, feed_string):
        feed_string.replace("\n", "\r\n")
        self.vte_terminal.feed([ord(char) for char in feed_string + "\r\n"])

    def update_style_scheme(self, *args):
        background = Gdk.RGBA()
        foreground = Gdk.RGBA()

        background.parse('rgba(0, 0, 0, 0)')

        if Adw.StyleManager.get_default().get_dark():
            foreground.parse('#ffffff')
        else:
            foreground.parse('rgba(0, 0, 0, 0.8)')

        self.vte_terminal.set_color_background(background)
        self.vte_terminal.set_color_foreground(foreground)