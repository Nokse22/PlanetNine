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

from gi.repository import Gtk, Gio, GLib
from gi.repository import Panel

from .notebook import Notebook
from .jupyter_server import Session
from .jupyter_kernel import JupyterKernel, JupyterKernelInfo


class RowWidget(Gtk.TreeExpander):
    def __init__(self):
        super().__init__()

        self.controller_added = False

        self.box = Gtk.Box(
            margin_start=12,
            margin_end=12,
            margin_top=6,
            margin_bottom=6
        )
        self.click_controller = Gtk.GestureClick(button=3)
        self.click_controller.connect("released", self.on_click_released)
        self.label = Gtk.Label(
            xalign=0,
            ellipsize=3,
        )
        self.image = Gtk.Image(icon_name="python-symbolic", margin_end=6)
        self.box.append(self.image)
        self.box.append(self.label)
        self.set_child(self.box)

        self.set_indent_for_depth(True)

    def hide_image(self):
        self.image.set_visible(False)

    def indent(self, much):
        self.box.set_margin_start(12 + 12 * much)

    def set_text(self, text):
        self.label.set_text(text)

    def set_icon_name(self, icon_name):
        self.image.set_icon_name(icon_name)

    def set_menu_model(self, model):
        if not self.controller_added:
            self.add_controller(self.click_controller)
            self.controller_added = True
        self.menu_model = model

    def on_click_released(self, gesture, n_press, click_x, click_y):
        if n_press != 1:
            return

        widget = gesture.get_widget()
        popover = Gtk.PopoverMenu(position=1, menu_model=self.menu_model)
        popover.set_parent(widget)
        popover.popup()

        return True

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

        root_model = Gio.ListStore.new(Gtk.StringObject)
        root_model.append(Gtk.StringObject.new("Available Kernels"))
        tree_list_model = Gtk.TreeListModel.new(root_model, True, True, self.create_avalaible_kernels_sub_model)
        selection_model = Gtk.NoSelection(model=tree_list_model)
        self.avalaible_kernels_list_view.set_model(selection_model)

        root_model = Gio.ListStore.new(Gtk.StringObject)
        root_model.append(Gtk.StringObject.new("Running Kernels"))
        tree_list_model = Gtk.TreeListModel.new(root_model, True, True, self.create_running_kernels_sub_model)
        selection_model = Gtk.NoSelection(model=tree_list_model)
        self.running_kernels_list_view.set_model(selection_model)

        self.default_kernel_name = ""

    def create_avalaible_kernels_sub_model(self, item):
        if isinstance(item, Gtk.StringObject):
            return self.avalaible_kernels_model

    def create_running_kernels_sub_model(self, item):
        if isinstance(item, Gtk.StringObject):
            return self.running_kernels_model

        elif isinstance(item, Session):
            return Gtk.TreeListModel.new(item.notebook_store, False, True, self.create_running_kernels_sub_model)

        elif isinstance(item, Notebook):
            return None

    @Gtk.Template.Callback("on_setup")
    def on_setup(self, factory, list_item):
        list_item.set_child(RowWidget())

    @Gtk.Template.Callback("on_bind")
    def on_bind(self, factory, list_item):
        item = list_item.get_item()
        widget = list_item.get_child()

        print("ITEM: ", item)

        if isinstance(item, Gtk.StringObject):
            widget.set_text(item.get_string())
            widget.hide_image()

        elif isinstance(item, JupyterKernelInfo):
            widget.set_text(item.display_name)
            widget.indent(1)

            menu_model = Gio.Menu()
            menu_item = Gio.MenuItem()
            menu_item.set_label("New Notebook from Kernel")
            menu_item.set_action_and_target_value("win.new-notebook")
            menu_model.append_item(menu_item)
            menu_item = Gio.MenuItem()
            menu_item.set_label("New Console from Kernel")
            menu_item.set_action_and_target_value("win.new-console")
            menu_model.append_item(menu_item)
            widget.set_menu_model(menu_model)

        elif isinstance(item, JupyterKernel):
            widget.set_text(item.name)
            widget.indent(1)
            menu_model = Gio.Menu()
            menu_item = Gio.MenuItem()
            menu_item.set_label("New Notebook from Kernel")
            menu_item.set_action_and_target_value("win.new-notebook")
            menu_model.append_item(menu_item)
            menu_item = Gio.MenuItem()
            menu_item.set_label("New Console from Kernel")
            menu_item.set_action_and_target_value("win.new-console")
            menu_model.append_item(menu_item)
            menu_item = Gio.MenuItem()
            menu_item.set_label("Restart")
            menu_item.set_action_and_target_value("win.restart-kernel", GLib.Variant("s", item.kernel_id))
            menu_model.append_item(menu_item)
            menu_item = Gio.MenuItem()
            menu_item.set_label("Shutdown")
            menu_item.set_action_and_target_value("win.shutdown-kernel", GLib.Variant("s", item.kernel_id))
            menu_model.append_item(menu_item)
            widget.set_menu_model(menu_model)

        elif isinstance(item, Notebook):
            widget.set_text(item.name)

        else:
            widget.set_text("Unknown")
