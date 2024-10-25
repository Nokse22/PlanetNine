# no_save_delegate.py
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

from gi.repository import Panel, Gtk, GObject, Gio, GLib

from gettext import gettext as _


class NoSaveDelegate(Panel.SaveDelegate):
    __gtype_name__ = "NoSaveDelegate"

    def __init__(self):
        super().__init__()
        self.set_is_draft(False)

    def do_close(self):
        print("do close")

    def do_discard(self):
        print("do discard")

    def do_save_async(self, cancellable, callback, user_data):
        print("do save async")

    def do_save_finish(self, result):
        return True
