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

from gi.repository import Gtk, Gio, GLib, GObject
from gi.repository import Panel

from .notebook import Notebook
from .jupyter_server import Session
from .jupyter_kernel import JupyterKernel, JupyterKernelInfo
from .tree_row_widget import TreeWidget
from enum import IntEnum

from .converters import get_language_icon


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


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/kernel_manager_view.ui')
class KernelManagerView(Panel.Widget):
    __gtype_name__ = 'KernelManagerView'

    default_kernel_name = ""

    avalaible_kernels_list_view = Gtk.Template.Child()
    running_kernels_list_view = Gtk.Template.Child()

    avalaible_kernels_model = Gio.ListStore()
    running_kernels_model = Gio.ListStore()

    def __init__(self, _avalaible_kernels_model, _running_kernels_model):
        super().__init__()

        self.avalaible_kernels_model = _avalaible_kernels_model
        self.running_kernels_model = _running_kernels_model

        self.avalaible_kernels_root = TreeNode("Available Kernels", NodeType.ROOT, [])
        self.running_kernels_root = TreeNode("Running Kernels", NodeType.ROOT, [])

        root_model = Gio.ListStore()
        root_model.append(self.avalaible_kernels_root)
        tree_list_model = Gtk.TreeListModel.new(root_model, False, True, self.create_avalaible_kernels_sub_model)
        selection_model = Gtk.NoSelection(model=tree_list_model)
        self.avalaible_kernels_list_view.set_model(selection_model)

        root_model = Gio.ListStore()
        root_model.append(self.running_kernels_root)
        tree_list_model = Gtk.TreeListModel.new(root_model, False, True, self.create_running_kernels_sub_model)
        selection_model = Gtk.NoSelection(model=tree_list_model)
        self.running_kernels_list_view.set_model(selection_model)

        self.default_kernel_name = ""

    def create_avalaible_kernels_sub_model(self, item):
        if isinstance(item, TreeNode):
            return self.avalaible_kernels_model
        return None

    def create_running_kernels_sub_model(self, item):
        if isinstance(item, TreeNode):
            return self.running_kernels_model

        elif isinstance(item, Session):
            return Gtk.TreeListModel.new(item.notebook_store, False, True, self.create_running_kernels_sub_model)

        elif isinstance(item, Notebook):
            return None

    @Gtk.Template.Callback("on_setup")
    def on_setup(self, factory, list_item):
        list_item.set_child(TreeWidget())

    @Gtk.Template.Callback("on_bind")
    def on_bind(self, factory, list_item):
        print("BIND")
        list_row = list_item.get_item()
        widget = list_item.get_child()
        item = list_item.get_item().get_item()

        widget.expander.set_list_row(list_row)
        print(list_row)

        print("ITEM: ", item)

        if isinstance(item, TreeNode):
            widget.set_icon_name("view-list-symbolic")
            widget.set_show_menu(False)
            widget.set_text(item.name)

        elif isinstance(item, JupyterKernelInfo):
            widget.set_text(item.display_name)
            widget.set_icon_name(get_language_icon(item.language))

            menu_model = Gio.Menu()

            menu_item = Gio.MenuItem()
            menu_item.set_label("New Notebook from Kernel")
            menu_item.set_action_and_target_value("win.new-notebook-name", GLib.Variant("s", item.name))
            menu_model.append_item(menu_item)

            menu_item = Gio.MenuItem()
            menu_item.set_label("New Console from Kernel")
            menu_item.set_action_and_target_value("win.new-console-name", GLib.Variant("s", item.name))
            menu_model.append_item(menu_item)

            menu_item = Gio.MenuItem()
            menu_item.set_label("New Code from Kernel")
            menu_item.set_action_and_target_value("win.new-code-name", GLib.Variant("s", item.name))
            menu_model.append_item(menu_item)

            widget.set_menu_model(menu_model)

        elif isinstance(item, JupyterKernel):
            widget.set_text(item.display_name)
            widget.set_icon_name(get_language_icon(item.language))

            menu_model = Gio.Menu()
            menu_item = Gio.MenuItem()
            menu_item.set_label("New Notebook from Kernel")
            menu_item.set_action_and_target_value("win.new-notebook-id", GLib.Variant("s", item.kernel_id))
            menu_model.append_item(menu_item)

            menu_item = Gio.MenuItem()
            menu_item.set_label("New Console from Kernel")
            menu_item.set_action_and_target_value("win.new-console-id", GLib.Variant("s", item.kernel_id))
            menu_model.append_item(menu_item)

            menu_item = Gio.MenuItem()
            menu_item.set_label("Restart")
            menu_item.set_action_and_target_value("win.restart-kernel-id", GLib.Variant("s", item.kernel_id))
            menu_model.append_item(menu_item)

            menu_item = Gio.MenuItem()
            menu_item.set_label("Shutdown")
            menu_item.set_action_and_target_value("win.shutdown-kernel-id", GLib.Variant("s", item.kernel_id))
            menu_model.append_item(menu_item)

            widget.set_menu_model(menu_model)

        elif isinstance(item, Notebook):
            widget.set_text(item.name)

        else:
            widget.set_text("Unknown")
