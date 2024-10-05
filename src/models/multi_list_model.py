# section_model.py
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

from gi.repository import Gtk, GObject, Gio


class Prova(GObject.GObject):
    __gtype_name__ = 'Prova'

    def __init__(self, _name):
        super().__init__()

        self.display_name = _name


class MultiListModel(GObject.GObject, Gio.ListModel, Gtk.SectionModel):
    __gtype_name__ = 'MultiListModel'

    def __init__(self):
        super().__init__()
        self.sections = []
        self.section_names = []

    def add_section(self, list_store, section_name):
        if not isinstance(list_store, Gio.ListStore):
            raise ValueError("list_store must be a Gio.ListStore")
        prev_size = self.get_n_items()
        self.sections.append(list_store)
        self.section_names.append(section_name)
        list_store.connect("items-changed", self._on_section_items_changed)
        self.items_changed(prev_size, 0, list_store.get_n_items())
        self.notify_sections_changed(len(self.sections) - 1, 1)

    def _on_section_items_changed(self, list_store, position, removed, added):
        section_index = self.sections.index(list_store)
        start_position = sum(
            store.get_n_items() for store in self.sections[:section_index])
        self.items_changed(start_position + position, removed, added)

    def notify_sections_changed(self, start, count):
        self.emit("sections-changed", start, count)

    def do_get_section(self, position):
        if position >= self.get_n_items():
            return (self.get_n_items(), 0xFFFFFFFF)

        section_start = 0
        for store in self.sections:
            section_end = section_start + store.get_n_items()
            if position >= section_start and position < section_end:
                return (section_start, section_end)
            section_start = section_end

        return (0, 0)

    #
    #   ListModel methods
    #

    def __iter__(self):
        return None

    def do_get_item(self, position):
        for store in self.sections:
            if position < store.get_n_items():
                return store.get_item(position)
            position -= store.get_n_items()

    def do_get_item_type(self):
        return GObject.Object

    def do_get_n_items(self):
        n_items = sum(store.get_n_items() for store in self.sections)
        return n_items
