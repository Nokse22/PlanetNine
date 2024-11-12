# json_viewer.py
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

from gi.repository import Gtk, Adw, GObject, Gio

from enum import IntEnum

import json

from ..utils.utilities import format_json


class NodeType(IntEnum):
    ARRAY = 0
    DICTIONARY = 1
    BOOL = 2
    INT = 3
    FLOAT = 4
    STRING = 5
    ROOT = 6


class TreeNode(GObject.Object):
    def __init__(self, key, content, node_type, children=None):
        super().__init__()
        self.key = key
        self.content = content
        self.node_type = node_type
        self.children = children or []


class TreeWidget(Adw.Bin):
    def __init__(self):
        super().__init__()

        box = Gtk.Box(
            spacing=6,
            margin_start=3,
            margin_end=10,
            margin_top=3,
            margin_bottom=3
        )
        self.expander = Gtk.TreeExpander.new()
        self.key_label = Gtk.Label(
            xalign=0,
            yalign=0,
            ellipsize=3,
            selectable=True,
            css_classes=["dim-label"]
        )

        self.value_label = Gtk.Label(
            xalign=0,
            yalign=0,
            ellipsize=3,
            selectable=True
        )

        box.append(self.expander)
        box.append(self.key_label)
        box.append(self.value_label)
        self.set_child(box)

        self.click_controller = Gtk.GestureClick(button=1)
        self.click_controller.connect("released", self.on_click_released)
        self.add_controller(self.click_controller)

    def on_click_released(self, gesture, n_press, click_x, click_y):
        list_row = self.expander.get_list_row()
        list_row.set_expanded(not list_row.get_expanded())

    def set_key(self, node_type, key):
        if node_type == NodeType.ROOT:
            self.key_label.set_text("Object")
        else:
            self.key_label.set_text(f"{key}:")

    def set_value(self, node_type, value):
        if node_type == NodeType.ROOT:
            return

        if node_type == NodeType.ARRAY:
            self.value_label.set_text(f"[ {len(value)} ]")
        elif node_type == NodeType.DICTIONARY:
            self.value_label.set_text(f"{{ {len(value)} }}")
        else:
            self.value_label.set_text(f"{value}")

    def disconnect(self, *_args):
        self.click_controller.disconnect_by_func(self.on_click_released)

        print(f"disconnect: {self}")

    def __del__(self, *_args):
        print(f"DELETING {self}")


class JsonViewer(Gtk.Box):
    __gtype_name__ = 'JsonViewer'

    def __init__(self):
        super().__init__()

        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(12)

    def create_tree_view(self, tree_model):
        tree_list_model = Gtk.TreeListModel.new(
            tree_model, False, True, self.create_model_func)
        tree_list_model.set_autoexpand(False)
        selection_model = Gtk.NoSelection(model=tree_list_model)
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.on_factory_setup)
        factory.connect("bind", self.on_factory_bind)
        factory.connect("unbind", self.on_factory_unbind)
        list_view = Gtk.ListView.new(selection_model, factory)
        return list_view

    def parse_json_string(self, json_string):
        try:
            json_obj = json.loads(format_json(json_string))
        except Exception as e:
            print(e)
            return

        root_node = self.create_tree_node("Root", json_obj)

        tree_model = Gio.ListStore.new(TreeNode)
        tree_model.append(root_node)

        self.append(self.create_tree_view(tree_model))

    def create_tree_node(self, node_key, node_value):
        node_type = self.get_node_type(node_value)
        if node_type in [NodeType.DICTIONARY, NodeType.ROOT]:
            children = [
                self.create_tree_node(j_key, j_value)
                for j_key, j_value in node_value.items()
            ]
            return TreeNode(node_key, node_value, node_type, children)
        elif node_type == NodeType.ARRAY:
            children = [
                self.create_tree_node(str(a_index), a_value)
                for a_index, a_value in enumerate(node_value)
            ]
            return TreeNode(node_key, node_value, node_type, children)
        else:
            return TreeNode(node_key, str(node_value), node_type)

    def get_node_type(self, value):
        if isinstance(value, dict):
            return NodeType.DICTIONARY
        elif isinstance(value, list):
            return NodeType.ARRAY
        elif isinstance(value, bool):
            return NodeType.BOOL
        elif isinstance(value, int):
            return NodeType.INT
        elif isinstance(value, float):
            return NodeType.FLOAT
        else:
            return NodeType.STRING

    def create_model_func(self, item):
        if item.node_type in [
            NodeType.ARRAY, NodeType.DICTIONARY, NodeType.ROOT
        ]:
            child_model = Gio.ListStore.new(TreeNode)
            for child in item.children:
                child_model.append(child)
            return child_model
        return None

    def on_factory_setup(self, factory, list_item):
        list_item.set_child(TreeWidget())

    def on_factory_bind(self, factory, list_item):
        widget = list_item.get_child()
        tree_list_row = list_item.get_item()
        widget.expander.set_list_row(tree_list_row)

        tree_node = tree_list_row.get_item()
        widget.set_key(tree_node.node_type, tree_node.key)
        widget.set_value(tree_node.node_type, tree_node.content)

    def on_factory_unbind(self, factory, list_item):
        list_item.get_child().disconnect()

    def disconnect(self, *_args):
        list_view = self.get_first_child()
        while list_view:
            list_view.set_model(None)
            list_view.get_factory().disconnect_by_func(self.on_factory_setup)
            list_view.get_factory().disconnect_by_func(self.on_factory_bind)
            list_view.get_factory().disconnect_by_func(self.on_factory_unbind)

            self.remove(list_view)
            list_view = self.get_first_child()

        print(f"disconnect {self}")

    def __del__(self, *_args):
        print(f"DELETING {self}")
