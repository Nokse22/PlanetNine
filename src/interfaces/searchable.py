# searchable.py
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
from gi.repository import GtkSource, Gio, Panel
from gettext import gettext as _


# The ISearchable interface is used for any page that supports seraching
#       it's content
class ISearchable:
    def __init__(self, override=False):
        if not override:
            self.search_settings = GtkSource.SearchSettings()
            self.search_context = GtkSource.SearchContext.new(
                self.buffer, self.search_settings
            )

        if isinstance(self, Panel.Widget):
            menu = Gio.Menu()

            menu_item = Gio.MenuItem.new(_("Find..."), "app.search")
            menu.append_item(menu_item)

            self.get_menu_model().append_section(None, menu)

    def search_text(self):
        """Search the string in the page"""
        start_iter = self.buffer.get_start_iter()
        self.search_context.forward_async(start_iter)

    def set_search_text(self, text):
        """Sets the string to be searched

        :param str text: The text to search
        """
        self.search_settings.set_search_text(text)
