# sheet.py
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


class MatrixRow(GObject.GObject):
    __gtype_name__ = 'MatrixRow'

    def __init__(self):
        super().__init__()

        self._cells = [0]

    def get_cell(self, index):
        if len(self._cells) > index:
            return self._cells[index]

        return ""

    def append(self, value):
        self._cells.append(value)

    def set_number(self, number):
        self._cells[0] = number


class Matrix(GObject.GObject):
    __gtype_name__ = 'Matrix'

    def __init__(self):
        super().__init__()

        self._rows = Gio.ListStore()
        self._columns = [""]

    def append(self, row):
        self._rows.append(row)

    def add_column(self, column_name):
        self._columns.append(column_name)

    @GObject.property(type=GObject.GObject)
    def columns(self):
        return self._columns

    @GObject.property(type=GObject.GObject)
    def rows(self):
        return self._rows


class MatrixViewer(Gtk.ColumnView):
    __gtype_name__ = 'MatrixViewer'

    def __init__(self):
        super().__init__()

        self.set_show_column_separators(True)
        self.set_show_row_separators(True)

        self.set_reorderable(False)

        self.add_css_class("matrixviewer")

    def set_matrix(self, model):
        for index, column_name in enumerate(model.columns):
            column = Gtk.ColumnViewColumn(title=column_name)
            if index == 0:
                column.set_expand(False)
                column.set_fixed_width(50)
            else:
                column.set_expand(True)
                column.set_resizable(True)
            factory = Gtk.SignalListItemFactory()
            factory.connect("setup", self.on_factory_setup, index)
            factory.connect("bind", self.on_factory_bind, index)
            column.set_factory(factory)
            self.append_column(column)

        selection = Gtk.NoSelection.new(model=model.rows)
        self.set_model(model=selection)

    def on_factory_setup(self, _factory, list_item, index):
        if index == 0:
            inscr = Gtk.Inscription()
            inscr.add_css_class("dim-label")
            inscr.add_css_class("index-cell")
            inscr.set_xalign(0)
            list_item.set_child(inscr)
        else:
            label = Gtk.Label(ellipsize=3)
            label.set_selectable(True)
            label.set_xalign(1)
            list_item.set_child(label)

    def on_factory_bind(self, _factory, list_item, index):
        widget = list_item.get_child()
        row = list_item.get_item()

        if index == 0:
            widget.set_text(str(row.get_cell(index)))
        else:
            widget.set_label(str(row.get_cell(index)))

    def disconnect(self, *args):
        for column in self.get_columns():
            factory = column.get_factory()
            factory.disconnect_by_func(self.on_factory_setup)
            factory.disconnect_by_func(self.on_factory_bind)

        self.set_model(None)

        print(f"Closing: {self}")

    def __del__(self, *args):
        print(f"DELETING {self}")
