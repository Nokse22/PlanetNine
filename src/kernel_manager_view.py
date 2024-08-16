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

class KernelInfo(GObject.GObject):
    name = ""
    display_name = ""
    language = ""
    interrupt_mode = ""

    def __init__(self):
        super().__init__()

        self.name = ""
        self.display_name = ""
        self.language = ""
        self.interrupt_mode = ""

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

    # web_kit_view = Gtk.Template.Child()
    # uri_entry = Gtk.Template.Child()
    avalaible_kernel_list_box = Gtk.Template.Child()

    default_kernel_name = ""

    def __init__(self):
        super().__init__()

        self.set_css_name("kernelmanager")

        self.avalaible_kernel_model = Gio.ListStore()

        self.avalaible_kernel_list_box.bind_model(
            self.avalaible_kernel_model,
            self.create_kernel_widgets
        )

        self.default_kernel_name = ""

    def create_kernel_widgets(self, kernel_info):
        return Gtk.Label(label=kernel_info.name)

    def parse(self, spes_json):
        # print(spes_json)

        for kernel_name, kernel_spec in spes_json['kernelspecs'].items():
            kernel_info = KernelInfo.new_from_specs(kernel_spec)
            self.avalaible_kernel_model.append(kernel_info)
