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

from gi.repository import Gtk, Gio, GObject, GLib, Gdk
from gi.repository import Panel

from enum import IntEnum
import os
import asyncio

from ..widgets.tree_row_widget import TreeWidget, ClickAction

from ..utils.converters import get_mime_icon


class NodeType(IntEnum):
    ROOT = 0
    FILE = 1
    FOLDER = 2


class TreeNode(GObject.Object):
    def __init__(self, node_path, node_type, children=None, model=None):
        super().__init__()
        self.node_path = node_path
        self.node_type = node_type
        self.children = children or []

        self.display_name = os.path.basename(self.node_path)

        self.menu_model = model


@Gtk.Template(
    resource_path='/io/github/nokse22/PlanetNine/gtk/workspace_view.ui')
class WorkspacePanel(Panel.Widget):
    __gtype_name__ = 'WorkspacePanel'

    box = Gtk.Template.Child()

    workspace_menu = Gtk.Template.Child()
    other_menu = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        self.workspace_root = TreeNode(
            "Workspace", NodeType.ROOT, [], self.workspace_menu)
        self.setup_listview(self.workspace_root)

        self.files_root = TreeNode(
            "Other Files", NodeType.ROOT, [], self.other_menu)
        self.setup_listview(self.files_root)

        self.action_group = Gio.SimpleActionGroup()
        self.box.insert_action_group("workspace", self.action_group)

        self.create_action_with_target(
            'copy-path', GLib.VariantType.new("s"), self.on_copy_path_action)

        self.create_action_with_target(
            'new-file', GLib.VariantType.new("s"), self.on_new_file_action)

        self.create_action_with_target(
            'new-folder', GLib.VariantType.new("s"), self.on_new_folder_action)

        self.create_action("set", self.set_workspace_folder)

        self.create_action("add-files", self.on_add_file)
        self.create_action("add-folders", self.on_add_folder)

        self.create_action("import-files", self.on_import_file)
        self.create_action("import-folders", self.on_import_folder)

    def setup_listview(self, root):
        tree_model = Gio.ListStore.new(TreeNode)
        tree_model.append(root)

        tree_list_model = Gtk.TreeListModel.new(
            tree_model, False, True, self.create_model_func)
        tree_list_model.set_autoexpand(False)

        selection_model = Gtk.NoSelection(model=tree_list_model)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.on_factory_setup)
        factory.connect("bind", self.on_factory_bind)

        list_view = Gtk.ListView.new(selection_model, factory)
        list_view.add_css_class("workspace")
        list_view.add_css_class("sidebar-list")

        self.box.append(list_view)

    #
    #   SET THE WORKSPACE
    #

    def set_workspace_folder(self, *args):
        asyncio.create_task(self._on_set_workspace_folder())

    async def _on_set_workspace_folder(self):
        file_dialog = Gtk.FileDialog(
            accept_label="Choose Workspace Folder",
            modal=True
        )

        try:
            folder = await file_dialog.select_folder(self.get_root())
        except Exception as e:
            print(e)
            return

        folder_path = folder.get_path()

        self.workspace_root.children = []

        for node in os.listdir(folder_path):
            if os.path.isdir(folder_path):
                self.add_folder(
                    self.workspace_root, os.path.join(folder_path, node))
            elif os.path.isfile(folder_path):
                self.workspace_root.children.append(
                    TreeNode(folder_path, NodeType.FILE))

    #
    #   ADD FILES/FOLDERS (only in other files)
    #

    def on_add_file(self, *args):
        asyncio.create_task(self._on_add_file())

    async def _on_add_file(self):
        file_dialog = Gtk.FileDialog(
            accept_label="Open Files",
            modal=True
        )

        try:
            result = await file_dialog.open_multiple(self.get_root())
        except Exception as e:
            print(e)
            return

        for file in result:
            self.files_root.children.append(
                TreeNode(file.get_path(), NodeType.FILE))

    def on_add_folder(self, *args):
        asyncio.create_task(self._on_add_folder())

    async def _on_add_folder(self):
        file_dialog = Gtk.FileDialog(
            accept_label="Open Folders",
            modal=True
        )

        try:
            result = await file_dialog.select_multiple_folders(self.get_root())
        except Exception as e:
            print(e)
            return

        for folder in result:
            self.add_folder(self.files_root, folder.get_path())

    #
    # IMPORT FILES/FOLDERS (in the workspace)
    #

    def on_import_file(self, *args):
        asyncio.create_task(self._on_import_file())

    async def _on_import_file(self):
        file_dialog = Gtk.FileDialog(
            accept_label="Import Files",
            modal=True
        )

        try:
            result = await file_dialog.open_multiple(self.get_root())
        except Exception as e:
            print(e)
            return

        for file in result:
            self.workspace_root.children.append(
                TreeNode(file.get_path(), NodeType.FILE))
            # TODO Actually import the files in the workspace folder

    def on_import_folder(self, *args):
        asyncio.create_task(self._on_import_folder())

    async def _on_import_folder(self):
        file_dialog = Gtk.FileDialog(
            accept_label="Open Folders",
            modal=True
        )

        try:
            result = await file_dialog.select_multiple_folders(self.get_root())
        except Exception as e:
            print(e)
            return

        for folder in result:
            self.add_folder(self.workspace_root, folder.get_path())
            # TODO Actually import the folders asynchronously

    #
    #
    #

    def add_folder(self, root, folder_path):
        def add_node(node_path, parent):
            if os.path.isdir(node_path):
                folder = TreeNode(node_path, NodeType.FOLDER)
                parent.children.append(folder)
                for node in os.listdir(node_path):
                    add_node(os.path.join(node_path, node), folder)
            elif os.path.isfile(node_path):
                parent.children.append(TreeNode(node_path, NodeType.FILE))

        add_node(folder_path, root)

    def on_copy_path_action(self, action, variant):
        clipboard = Gdk.Display().get_default().get_clipboard()
        clipboard.set(variant.get_string())

    def on_new_file_action(self, action, variant):
        pass

    def on_new_folder_action(self, action, variant):
        pass

    def new_folder_menu(self, node_path):
        folder_menu = Gio.Menu()

        menu_item = Gio.MenuItem()
        menu_item.set_label("Copy Path")
        menu_item.set_action_and_target_value(
            "workspace.copy-path", GLib.Variant('s', node_path))
        folder_menu.append_item(menu_item)

        menu_item = Gio.MenuItem()
        menu_item.set_label("New File")
        menu_item.set_action_and_target_value(
            "workspace.new-file", GLib.Variant('s', node_path))
        folder_menu.append_item(menu_item)

        menu_item = Gio.MenuItem()
        menu_item.set_label("New Folder")
        menu_item.set_action_and_target_value(
            "workspace.new-folder", GLib.Variant('s', node_path))
        folder_menu.append_item(menu_item)

        return folder_menu

    def new_file_menu(self, node_path):
        file_menu = Gio.Menu()

        menu_item = Gio.MenuItem()
        menu_item.set_label("Copy Path")
        menu_item.set_action_and_target_value(
            "workspace.copy-path", GLib.Variant('s', node_path))
        file_menu.append_item(menu_item)

        menu_item = Gio.MenuItem()
        menu_item.set_label("Open")
        menu_item.set_action_and_target_value(
            "win.open-file", GLib.Variant('s', node_path))
        file_menu.append_item(menu_item)

        open_with_menu = Gio.Menu()

        menu_item = Gio.MenuItem()
        menu_item.set_label("Text")
        menu_item.set_action_and_target_value(
            "win.open-file-with-text", GLib.Variant('s', node_path))
        open_with_menu.append_item(menu_item)

        menu_item = Gio.MenuItem()
        menu_item.set_label("Browser")
        menu_item.set_action_and_target_value(
            "win.new-browser-page", GLib.Variant('s', "file://" + node_path))
        open_with_menu.append_item(menu_item)

        file_menu.append_submenu("Open With", open_with_menu)

        return file_menu

    def create_model_func(self, item):
        if item.node_type in [NodeType.FOLDER, NodeType.ROOT]:
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
            widget.set_icon_name("view-list-symbolic")
            if item.menu_model:
                widget.set_menu_model(item.menu_model)
            widget.set_text(item.display_name)

        elif item.node_type == NodeType.FOLDER:
            widget.set_icon_name("folder-symbolic")
            widget.set_menu_model(self.new_folder_menu(item.node_path))
            widget.set_text(item.display_name)

        elif item.node_type == NodeType.FILE:
            widget.set_icon_name(get_mime_icon(item.node_path))
            widget.set_menu_model(self.new_file_menu(item.node_path))
            widget.set_text(item.display_name)
            widget.set_click_action(ClickAction.ACTIVATE)
            widget.set_activate_action_and_target(
                "win.open-file", GLib.Variant('s', item.node_path))

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
