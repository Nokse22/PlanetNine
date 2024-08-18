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

from gi.repository import Gtk, Gio, GObject, Adw, GLib, Gdk
from gi.repository import Panel
from enum import IntEnum


class NodeType(IntEnum):
    ROOT = 0
    FILE = 1
    FOLDER = 2


class TreeNode(GObject.Object):
    def __init__(self, name, node_type, children=None):
        super().__init__()
        self.name = name
        self.node_type = node_type
        self.children = children or []


class TreeWidget(Adw.Bin):
    def __init__(self):
        super().__init__()

        box = Gtk.Box(
            spacing=6,
            margin_start=6,
            margin_end=10,
            margin_top=6,
            margin_bottom=6
        )

        self.expander = Gtk.TreeExpander.new()
        self.expander.set_hide_expander(True)
        self.expander.set_indent_for_icon(False)

        self.label = Gtk.Label(
            xalign=0,
            ellipsize=3,
        )

        self.image = Gtk.Image(icon_name="python-symbolic", margin_end=6)

        self.menu_model = Gio.Menu()

        box.append(self.expander)
        box.append(self.image)
        box.append(self.label)

        self.click_controller = Gtk.GestureClick(button=0)
        self.click_controller.connect("released", self.on_click_released)
        self.add_controller(self.click_controller)

        self.set_child(box)

    def set_text(self, text):
        self.label.set_text(text)

    def set_icon_name(self, icon_name):
        self.image.set_from_icon_name(icon_name)

    def set_menu_model(self, model):
        self.menu_model = model

    def on_click_released(self, gesture, n_press, click_x, click_y):
        if gesture.get_current_button() == 3:
            if n_press != 1:
                return

            widget = gesture.get_widget()
            popover = Gtk.PopoverMenu(position=1, menu_model=self.menu_model)
            popover.set_parent(widget)
            popover.popup()

            return True
        elif gesture.get_current_button() == 1:
            list_row = self.expander.get_list_row()
            list_row.set_expanded(not list_row.get_expanded())

@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/workspace_view.ui')
class WorkspaceView(Panel.Widget):
    __gtype_name__ = 'WorkspaceView'

    __gsignals__ = {
        # 'changed': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.TextBuffer,)),
    }

    workspace_list_view = Gtk.Template.Child()

    workspace_model = Gio.ListStore()

    def __init__(self):
        super().__init__()

        self.root = TreeNode("/home/user/.var/app", NodeType.ROOT, [
            TreeNode("data", NodeType.FOLDER, [
                TreeNode("raw_data.csv", NodeType.FILE),
                TreeNode("persons.csv", NodeType.FILE),
            ]),
            TreeNode("image.png", NodeType.FILE),
            TreeNode("processed data", NodeType.FOLDER, [
                TreeNode("results.csv", NodeType.FILE),
            ]),
        ])

        tree_model = Gio.ListStore.new(TreeNode)
        tree_model.append(self.root)

        tree_list_model = Gtk.TreeListModel.new(tree_model, False, True, self.create_model_func)

        selection_model = Gtk.NoSelection(model=tree_list_model)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.on_factory_setup)
        factory.connect("bind", self.on_factory_bind)

        list_view = Gtk.ListView.new(selection_model, factory)
        list_view.add_css_class("workspace")

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_child(list_view)
        scrolled_window.set_vexpand(True)

        self.set_child(scrolled_window)

        self.action_group = Gio.SimpleActionGroup()
        self.insert_action_group("workspace", self.action_group)

        self.create_action_with_target(
            'copy-path',
            GLib.VariantType.new("s"),
            self.on_copy_path_action
        )

        self.create_action("new-file", lambda *args: print("new file!"))

    def on_copy_path_action(self, action, variant):
        clipboard = Gdk.Display().get_default().get_clipboard()
        clipboard.set(variant.get_string())

    def on_new_file_action(self, action, variant):
        pass

    def get_path(self, target_node):
        def dfs(node, node_path):
            node_path.append(node.name)

            if node == target_node:
                return '/'.join(node_path)

            for child in node.children:
                result = dfs(child, node_path.copy())
                if result:
                    return result

            return None

        return dfs(self.root, [])

    def new_root_menu(self):
        root_menu = Gio.Menu()
        root_menu.append("Add File", "workspace.add-file")
        root_menu.append("Add Folder", "workspace.add-folder")
        new_submenu = Gio.Menu()
        new_submenu.append("New File", "workspace.new-file")
        new_submenu.append("New Folder", "workspace.new-folder")
        root_menu.append_section(None, new_submenu)
        return root_menu

    def new_folder_menu(self, node_path):
        folder_menu = Gio.Menu()

        menu_item = Gio.MenuItem()
        menu_item.set_label("Copy Path")
        menu_item.set_action_and_target_value("workspace.copy-path", GLib.Variant('s', node_path))
        folder_menu.append_item(menu_item)

        menu_item = Gio.MenuItem()
        menu_item.set_label("New File")
        menu_item.set_action_and_target_value("workspace.new-file", GLib.Variant('s', node_path))
        folder_menu.append_item(menu_item)

        return folder_menu

    def new_file_menu(self, node_path):
        file_menu = Gio.Menu()

        menu_item = Gio.MenuItem()
        menu_item.set_label("Copy Path")
        menu_item.set_action_and_target_value("workspace.copy-path", GLib.Variant('s', node_path))
        file_menu.append_item(menu_item)

        return file_menu

    def create_model_func(self, item):
        if (item.node_type == NodeType.FOLDER or item.node_type == NodeType.ROOT) and item.children:
            child_model = Gio.ListStore.new(TreeNode)
            for child in item.children:
                child_model.append(child)
            return child_model
        return None

    def on_factory_setup(self, factory, list_item):
        list_item.set_child(TreeWidget())

    def on_factory_bind(self, factory, list_item):
        item = list_item.get_item()
        widget = list_item.get_child()
        widget.expander.set_list_row(item)

        item = list_item.get_item().get_item()

        if item.node_type == NodeType.ROOT:
            widget.set_icon_name("root-symbolic")
            widget.set_menu_model(self.new_root_menu())
            widget.set_text("Workspace")

        elif item.node_type == NodeType.FOLDER:
            widget.set_icon_name("folder-symbolic")
            widget.set_menu_model(self.new_folder_menu(self.get_path(item)))
            widget.set_text(item.name)

        elif item.node_type == NodeType.FILE:
            widget.set_icon_name("python-symbolic")
            widget.set_menu_model(self.new_file_menu(self.get_path(item)))
            widget.set_text(item.name)

    def create_action_with_target(self, name, target_type, callback):
        action = Gio.SimpleAction.new(name, target_type)
        action.connect("activate", callback)
        self.action_group.add_action(action)
        return action

    def create_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.action_group.add_action(action)
        return action
