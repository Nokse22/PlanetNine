# kernel_page.py
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

from gi.repository import GObject, GLib, Gio, Panel
from ..backend.jupyter_server import JupyterServer
from .language import ILanguage
from gettext import gettext as _
import random
import string


# The IKernel interface is used for any page that has a kernel associated
#       with it
class IKernel:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.kernel_info_changed = GObject.Signal("kernel-info-changed")
        cls.page_id = GObject.Property(type=str)
        cls.kernel_id = GObject.Property(type=str)
        cls.kernel_name = GObject.Property(type=str)

    def __init__(self, **kwargs):
        self.page_id = "".join(random.choices(string.ascii_letters, k=10))
        self.jupyter_server = JupyterServer()

        if "kernel_id" in kwargs.keys():
            self.kernel_id = kwargs["kernel_id"]
        elif "kernel_name" in kwargs.keys():
            self.kernel_name = kwargs["kernel_name"]

        if isinstance(self, Panel.Widget):
            menu = Gio.Menu()

            menu_item = Gio.MenuItem()
            menu_item.set_label(_("Change Kernel"))
            menu_item.set_action_and_target_value(
                "win.change-kernel", GLib.Variant('s', ""))
            menu.append_item(menu_item)

            self.get_menu_model().append_section(None, menu)

    def start_kernel(self):
        """Starts a kernel for this page

        To be run when the page has been initalized so that a kernel can be
        started.
        """

        if self.kernel_name:
            self.activate_action(
                "win.request-kernel-name",
                GLib.Variant("(ss)", (self.page_id, self.kernel_name)))
        elif self.kernel_id:
            self.activate_action(
                "win.request-kernel-id",
                GLib.Variant("(ss)", (self.page_id, self.kernel_id)))
        else:
            self.activate_action(
                "win.change-kernel",
                GLib.Variant("s", self.page_id))

    def get_kernel(self):
        """Get the page kernel

        :returns: the page kernel
        :rtype: JupyterKernel
        """

        succ, kernel = self.jupyter_server.get_kernel_by_id(self.kernel_id)

        if succ:
            return kernel

        return None

    def set_kernel(self, kernel_id):
        """Sets the page kernel

        :param JupyterKernel jupyter_kernel: the new page kernel
        """

        self.kernel_id = kernel_id

        jupyter_kernel = self.get_kernel()

        if isinstance(self, ILanguage):
            self.set_language(jupyter_kernel.language)

        # if self.jupyter_kernel:
        #     self.jupyter_kernel.disconnect_by_func(self.on_kernel_info_changed)

        # self.jupyter_kernel = jupyter_kernel
        # self.jupyter_kernel.connect(
        #     "status-changed",
        #     self.on_kernel_info_changed)

        # self.emit("kernel-info-changed")

    def on_kernel_info_changed(self, *_args):
        """Emits the signal kernel-info-changed

        Run whenever the status or the kernel itself changes
        """

        self.emit("kernel-info-changed")
