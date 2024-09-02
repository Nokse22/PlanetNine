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
from pprint import pprint
from enum import IntEnum
import json


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
            ellipsize=3,
            selectable=True,
            css_classes=["dim-label"]
        )

        self.value_label = Gtk.Label(
            xalign=0,
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
        if node_type == NodeType.ARRAY:
            self.value_label.set_text(f"[ {len(value)} ]")
        elif node_type == NodeType.DICTIONARY:
            self.value_label.set_text(f"{{ {len(value)} }}")
        elif node_type == NodeType.BOOL:
            self.value_label.set_text(f"{value}")
        elif node_type == NodeType.INT:
            self.value_label.set_text(f"{value}")
        elif node_type == NodeType.FLOAT:
            self.value_label.set_text(f"{value}")
        elif node_type == NodeType.STRING:
            self.value_label.set_text(f"\"{value}\"")

class JsonViewer(Adw.Bin):
    __gtype_name__ = 'JsonViewer'

    def __init__(self):
        super().__init__()
        self.tree_model = Gio.ListStore.new(TreeNode)
        self.set_child(self.create_tree_view())

    def create_tree_view(self):
        self.tree_list_model = Gtk.TreeListModel.new(self.tree_model, False, True, self.create_model_func)
        self.tree_list_model.set_autoexpand(False)
        selection_model = Gtk.NoSelection(model=self.tree_list_model)
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.on_factory_setup)
        factory.connect("bind", self.on_factory_bind)
        list_view = Gtk.ListView.new(selection_model, factory)
        return list_view

    def parse_json_string(self, json_string):
        json_string = json_string.replace("'", '"')
        json_string = json_string.replace('True', 'true')
        json_string = json_string.replace('False', 'false')
        try:
            json_obj = json.loads(json_string)
        except Exception as e:
            print(e)
            return

        self.tree_model.remove_all()
        root_node = self.create_tree_node("Root", json_obj, NodeType.ROOT)
        self.tree_model.append(root_node)

    def create_tree_node(self, key, value, node_type):
        print("creating node: ", key, value, node_type)
        if node_type in [NodeType.DICTIONARY, NodeType.ROOT]:
            children = [self.create_tree_node(k, v, self.get_node_type(v)) for k, v in value.items()]
            return TreeNode(key, value, node_type, children)
        elif node_type == NodeType.ARRAY:
            children = [self.create_tree_node(str(i), v, self.get_node_type(v)) for i, v in enumerate(value)]
            return TreeNode(key, value, node_type, children)
        else:
            return TreeNode(key, str(value), node_type)

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
        if item.node_type in [NodeType.ARRAY, NodeType.DICTIONARY, NodeType.ROOT]:
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
