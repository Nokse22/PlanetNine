# image_viewer.py
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

from gi.repository import Gtk, GObject, Gdk


class ImageView(Gtk.Picture):
    __gtype_name__ = 'ImageView'

    __gsignals__ = {
        # 'changed': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.TextBuffer,)),
    }

    def __init__(self):
        super().__init__()

        self.set_css_name("imageview")

        self.drag_source = Gtk.DragSource(
            actions=Gdk.DragAction.COPY,
        )

        self.add_controller(self.drag_source)

        self.drag_source.connect("prepare", self.on_drag_source_prepare)
        self.drag_source.connect("drag-begin", self.on_drag_source_begin)
        self.drag_source.connect("drag-end", self.on_drag_source_end)

    def on_drag_source_prepare(self, source, x, y):
        value = GObject.Value()
        value.init(Gdk.Pixbuf)
        value.set_object()

        return Gdk.ContentProvider.new_for_value(value)

    def on_drag_source_begin(self, source, drag):
        drag_widget = Gtk.Image()

        icon = Gtk.DragIcon.get_for_drag(drag)
        icon.set_child(drag_widget)

        drag.set_hotspot(0, 0)

    def on_drag_source_end(self, source, drag, delete_data):
        print("how do i delete", source, drag, delete_data)

    def disconnect(self, *_args):
        pass

    def __del__(self, *_args):
        print(f"DELETING {self}")
