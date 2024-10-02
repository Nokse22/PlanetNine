# variables_viewer.py
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

from gi.repository import Gtk, Panel


@Gtk.Template(
    resource_path='/io/github/nokse22/PlanetNine/gtk/variables_view.ui')
class VariablesPanel(Panel.Widget):
    __gtype_name__ = 'VariablesPanel'

    column_view = Gtk.Template.Child()
    column_name = Gtk.Template.Child()
    column_type = Gtk.Template.Child()
    column_value = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        # self.connect("unrealize", self.__on_unrealized)

        self.column_name.get_factory().connect("setup", self.on_factory_setup)
        self.column_name.get_factory().connect(
            "bind", self.on_factory_bind, "name")

        self.column_type.get_factory().connect("setup", self.on_factory_setup)
        self.column_type.get_factory().connect(
            "bind", self.on_factory_bind, "type")

        self.column_value.get_factory().connect("setup", self.on_factory_setup)
        self.column_value.get_factory().connect(
            "bind", self.on_factory_bind, "value")

    def set_model(self, variables):
        selection = Gtk.NoSelection.new(model=variables)
        self.column_view.set_model(model=selection)

    def on_factory_setup(self, _factory, list_item):
        label = Gtk.Label(ellipsize=3)
        label.set_selectable(True)
        label.set_xalign(0)
        label.set_yalign(0)
        list_item.set_child(label)

    def on_factory_bind(self, _factory, list_item, attr):
        widget = list_item.get_child()
        variable = list_item.get_item()

        if attr == 'value':
            widget.set_xalign(1)
            widget.set_margin_end(12)
            widget.add_css_class("monospace")

        value = str(getattr(variable, attr)).replace('\\n', '\n')

        widget.set_label(value)

    def __on_unrealized(self, *args):
        self.disconnect_by_func(self.__on_unrealized)

        for column in self.column_view.get_columns():
            factory = column.get_factory()
            factory.disconnect_by_func(self.on_factory_setup)
            factory.disconnect_by_func(self.on_factory_bind)

        print(f"Unrealize {self}")

    def __del__(self, *args):
        print(f"DELETING {self}")
