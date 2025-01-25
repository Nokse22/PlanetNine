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

from gi.repository import Gtk, Gio, GObject, GLib, Gdk, Adw, Xdp
from gi.repository import Panel

from enum import IntEnum
import os
import asyncio

from ..backend.jupyter_server import JupyterServer

from ..utils.converters import get_mime_icon


class NodeWidget(Adw.Bin):
    def __init__(self):
        super().__init__()

        box = Gtk.Box(
            spacing=6,
            margin_start=9,
            margin_end=10,
            margin_top=6,
            margin_bottom=6
        )

        self.label = Gtk.Label(
            xalign=0,
            ellipsize=3,
        )

        self.image = Gtk.Image(margin_end=6)

        self.menu_model = None
        self.show_menu = True

        box.append(self.image)
        box.append(self.label)

        self.click_controller = Gtk.GestureClick(button=0)
        self.click_controller.connect("released", self.on_click_released)
        self.add_controller(self.click_controller)

        self.node = None

        self.action = ""
        self.target = None

        self.set_child(box)

    def set_node(self, node):
        self.node = node

        self.action = "win.open-file"
        self.target = GLib.Variant('s', self.node.node_path)

        self.label.set_label(self.node.display_name)

        if self.node.node_type == NodeType.FOLDER:
            self.image.set_from_icon_name("folder-symbolic")
            self.show_menu = False
        else:
            self.image.set_from_icon_name(get_mime_icon(self.node.mimetype))
            self.setup_file_menu()

    def setup_file_menu(self):
        self.menu_model = Gio.Menu()

        menu_item = Gio.MenuItem()
        menu_item.set_label("Copy Path")
        menu_item.set_action_and_target_value(
            "workspace.copy-path", GLib.Variant('s', self.node.node_path))
        self.menu_model.append_item(menu_item)

        menu_item = Gio.MenuItem()
        menu_item.set_label("Open")
        menu_item.set_action_and_target_value(
            "win.open-file", GLib.Variant('s', self.node.node_path))
        self.menu_model.append_item(menu_item)

        open_with_menu = Gio.Menu()

        menu_item = Gio.MenuItem()
        menu_item.set_label("Text")
        menu_item.set_action_and_target_value(
            "win.open-file-with-text", GLib.Variant('s', self.node.node_path))
        open_with_menu.append_item(menu_item)

        menu_item = Gio.MenuItem()
        menu_item.set_label("Browser")
        menu_item.set_action_and_target_value(
            "win.new-browser-page",
            GLib.Variant('s', "file://" + self.node.node_path))
        open_with_menu.append_item(menu_item)

        self.menu_model.append_submenu("Open With", open_with_menu)

    def on_click_released(self, gesture, n_press, click_x, click_y):
        if gesture.get_current_button() == 3 and self.show_menu:
            if n_press != 1:
                return

            widget = gesture.get_widget()
            popover = Gtk.PopoverMenu(position=1, menu_model=self.menu_model)
            popover.set_parent(widget)
            popover.popup()

            return True
        elif gesture.get_current_button() == 1:
            if self.node.node_type == NodeType.FOLDER:
                self.activate_action("workspace.set-base-path", self.target)
            else:
                self.activate_action(self.action, self.target)
                print(self.action, self.target)

    def set_activate_action_and_target(self, action, target):
        self.action = action
        self.target = target

    def disconnect(self, *_args):
        self.click_controller.disconnect_by_func(self.on_click_released)


class NodeType(IntEnum):
    FILE = 0
    FOLDER = 1


class Node(GObject.Object):
    def __init__(self, node_path, node_mime, node_type):
        super().__init__()
        self.node_path = node_path
        self.node_type = node_type
        self.mimetype = node_mime

        self.display_name = os.path.basename(self.node_path)


@Gtk.Template(
    resource_path='/io/github/nokse22/PlanetNine/gtk/workspace_view.ui')
class WorkspacePanel(Panel.Widget):
    __gtype_name__ = 'WorkspacePanel'

    box = Gtk.Template.Child()

    workspace_list_view = Gtk.Template.Child()

    path_label = Gtk.Template.Child()

    workspace_menu = Gtk.Template.Child()
    other_menu = Gtk.Template.Child()

    settings = Gio.Settings.new('io.github.nokse22.PlanetNine')
    portal = Xdp.Portal()

    data_dir = os.environ["XDG_DATA_HOME"]

    base_path = "/"

    def __init__(self):
        super().__init__()

        self.server = JupyterServer()

        # self.sandboxed = self.portal.running_under_sandbox()
        # self.use_external = self.settings.get_boolean("use-external-server") or not self.sandboxed
        # self.flatpak_spawn = self.sandboxed and self.use_external

        self.set_base_path("/")

        self.explorer_file_list = Gio.ListStore()

        selection_model = Gtk.NoSelection(model=self.explorer_file_list)
        self.workspace_list_view.set_model(selection_model)

        self.action_group = Gio.SimpleActionGroup()
        self.box.insert_action_group("workspace", self.action_group)

        self.create_action_with_target(
            'set-base-path',
            GLib.VariantType.new("s"), self.on_set_base_path_action)

        self.create_action(
            'navigate-up', self.on_navigate_up_action)

        self.create_action_with_target(
            'copy-path', GLib.VariantType.new("s"), self.on_copy_path_action)

        self.create_action_with_target(
            'new-file', GLib.VariantType.new("s"), self.on_new_file_action)

        self.create_action_with_target(
            'new-folder', GLib.VariantType.new("s"), self.on_new_folder_action)

        GLib.timeout_add_seconds(3, self.update_files)

    def set_base_path(self, value):
        self.path_label.set_label("~/ " + value.replace("/", " / "))
        self.base_path = value

    def update_files(self):
        asyncio.create_task(self.update_files_async())

        return False

    async def update_files_async(self):
        succ, result = await self.server.get_path_content(self.base_path)

        if not succ:
            return

        content = result.get("content", None)

        if content is None:
            return

        for obj in content:
            node_name = obj.get("name")
            node_path = obj.get("path")
            node_mime = obj.get("mimetype")
            node_type = NodeType.FOLDER if obj.get("type") == "directory" else NodeType.FILE
            if node_name and node_path:
                node = Node(node_path, node_mime, node_type)
                self.explorer_file_list.append(node)

    #
    #
    #

    def on_navigate_up_action(self, *args):
        self.set_base_path(os.path.dirname(self.base_path))
        self.explorer_file_list.remove_all()
        self.update_files()

    def on_set_base_path_action(self, action, variant):
        print("SET BASE: ", variant.get_string())
        self.set_base_path(variant.get_string())
        self.explorer_file_list.remove_all()
        self.update_files()

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

    @Gtk.Template.Callback("on_setup")
    def on_factory_setup(self, factory, list_item):
        list_item.set_child(NodeWidget())

    @Gtk.Template.Callback("on_bind")
    def on_factory_bind(self, factory, list_item):
        item = list_item.get_item()
        widget = list_item.get_child()

        widget.set_node(item)

        print("node widget set", widget, item)

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
