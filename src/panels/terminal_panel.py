# terminal_panel.py
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

from gi.repository import Gtk, Panel, Gdk, Vte, Gio

from ..interfaces.style_update import IStyleUpdate


class TerminalPanel(Panel.Widget, IStyleUpdate):
    __gtype_name__ = 'TerminalPanel'

    menu_model = Gio.Menu()

    menu_item = Gio.MenuItem.new("Copy", "terminal.copy")
    menu_model.append_item(menu_item)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.click_gesture = Gtk.GestureClick()
        self.click_gesture.set_button(3)
        self.click_gesture.connect("released", self.on_click_released)

        self.popover = Gtk.PopoverMenu.new_from_model(self.menu_model)

        self.set_icon_name("terminal-symbolic")

        self.vte_terminal = Vte.Terminal(
            hexpand=True,
            vexpand=True,
            font_scale=0.8,
            scrollback_lines=1000
        )

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add_controller(self.click_gesture)
        scrolled_window.set_child(self.vte_terminal)

        self.set_child(scrolled_window)

        IStyleUpdate.__init__(self, **kwargs)

    def feed(self, feed_string):
        """Handles feeding a string to the vte_terminal"""

        feed_string.replace("\n", "\r\n")
        self.vte_terminal.feed([ord(char) for char in feed_string + "\r\n"])

    def update_style_scheme(self, *_args):
        """Updates the vte_terminal color scheme"""

        colors = self.style_manager.get_current_colors()
        background = Gdk.RGBA()
        foreground = Gdk.RGBA()
        transparent = Gdk.RGBA()

        background.parse(colors["background"])
        foreground.parse(colors["foreground"])
        transparent.parse("rgba(0.0, 0.0, 0.0, 0.0)")

        colors_list = []

        for i in range(0, 16):
            color = Gdk.RGBA()
            color.parse(colors[f"color{i}"])
            colors_list.append(color)

        self.vte_terminal.set_colors(
            foreground,
            transparent,
            colors_list
        )
        self.vte_terminal.set_color_highlight(foreground)
        self.vte_terminal.set_color_highlight_foreground(background)

    def on_click_released(self, gesture, n_press, click_x, click_y):
        if n_press != 1:
            return

        widget = gesture.get_widget()

        position = Gdk.Rectangle()
        position.x = click_x
        position.y = click_y
        self.popover.set_parent(widget)
        self.popover.set_pointing_to(position)
        self.popover.popup()

        return True
