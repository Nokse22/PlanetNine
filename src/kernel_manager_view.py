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

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject, Gio
from gi.repository import Panel

from .notebook import Notebook

class KernelSession(GObject.GObject):
    __gtype_name__ = 'KernelSession'

    name = ""

    notebook_store = None

    def __init__(self, _name=""):
        super().__init__()

        self.name = _name

        self.notebook_store = Gio.ListStore.new(Notebook)

class KernelInfo(GObject.GObject):
    __gtype_name__ = 'KernelInfo'

    name = ""
    display_name = ""
    language = ""
    interrupt_mode = ""

    session_store = None

    def __init__(self):
        super().__init__()

        self.name = ""
        self.display_name = ""
        self.language = ""
        self.interrupt_mode = ""

        self.session_store = Gio.ListStore.new(KernelSession)

        self.session_store.append(KernelSession("prova"))
        self.session_store.append(KernelSession("prova 2"))

    @classmethod
    def new_from_specs(cls, specs):
        instance = cls()

        print("SPEK: ", specs)

        instance.name = specs['name']
        instance.display_name = specs['spec']['display_name']
        instance.language = specs['spec']['language']
        instance.interrupt_mode = specs['spec']['interrupt_mode']

        return instance

@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/kernel_manager_view.ui')
class KernelManager(Panel.Widget):
    __gtype_name__ = 'KernelManager'

    __gsignals__ = {
        # 'changed': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.TextBuffer,)),
    }

    default_kernel_name = ""

    def __init__(self):
        super().__init__()

        self.set_css_name("kernelmanager")

        self.kernels_model = Gio.ListStore.new(KernelInfo)

        self.tree_list_model = Gtk.TreeListModel.new(self.kernels_model, False, True, self.create_sub_model)

        self.selection_model = Gtk.NoSelection(model=self.tree_list_model)

        self.list_view = Gtk.ListView.new(self.selection_model, self.create_item_factory())

        self.set_child(self.list_view)

        self.default_kernel_name = ""

    def create_sub_model(self, item):
        if isinstance(item, KernelInfo):
            return Gtk.TreeListModel.new(item.session_store, False, True, self.create_sub_model)

        elif isinstance(item, KernelSession):
            return Gtk.TreeListModel.new(item.notebook_store, False, True, self.create_sub_model)

        elif isinstance(item, Notebook):
            return Gio.ListStore.new(Gtk.StringObject)

    def create_item_factory(self):
        factory = Gtk.SignalListItemFactory()

        factory.connect("setup", self.on_setup)
        factory.connect("bind", self.on_bind)

        return factory

    def on_setup(self, factory, list_item):
        label = Gtk.Label(xalign=0)
        label.set_margin_start(10)
        label.set_margin_end(10)
        label.set_margin_top(5)
        label.set_margin_bottom(5)
        list_item.set_child(label)

    def on_bind(self, factory, list_item):
        item = list_item.get_item().get_item()
        label = list_item.get_child()

        print("ITEM: ", item)

        if isinstance(item, KernelInfo):
            label.set_text(item.display_name)

        elif isinstance(item, KernelSession):
            label.set_text(item.name)

        elif isinstance(item, Notebook):
            label.set_text(item.name)

        else:
            label.set_text("Unknown")

    def parse(self, spes_json):
        # print(spes_json)

        for kernel_name, kernel_spec in spes_json['kernelspecs'].items():
            kernel_info = KernelInfo.new_from_specs(kernel_spec)
            self.kernels_model.append(kernel_info)
