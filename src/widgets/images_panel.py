# images_panel.py
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

from gi.repository import Gtk, Panel, GLib, Gio

import os


@Gtk.Template(
    resource_path='/io/github/nokse22/PlanetNine/gtk/images_panel.ui')
class ImagesPanel(Panel.Widget):
    __gtype_name__ = 'ImagesPanel'

    main_picture = Gtk.Template.Child()
    list_view = Gtk.Template.Child()
    view_stack = Gtk.Template.Child()

    cache_dir = os.environ["XDG_CACHE_HOME"]
    images_path = os.path.join(cache_dir, "g_images")

    os.makedirs(images_path, exist_ok=True)

    def __init__(self):
        super().__init__()

        self.current_images = []

        self.images = Gio.ListStore()

        self.selection_model = Gtk.SingleSelection(model=self.images)
        self.selection_model.connect(
            "notify::selected", self.on_image_selected)

        self.list_view.set_model(self.selection_model)

        GLib.timeout_add(500, self.check_for_new_images)

    def check_for_new_images(self):
        if not os.path.exists(self.images_path):
            return True

        updated_images = os.listdir(self.images_path)

        if updated_images != []:
            self.view_stack.set_visible_child_name("images_page")
        else:
            self.view_stack.set_visible_child_name("no_images_page")

        if updated_images == self.current_images:
            return True

        new_images = []
        for img in updated_images:
            if img not in self.current_images:
                new_images.append(img)

        for image_path in new_images:
            image_file = Gio.File.new_for_path(
                os.path.join(self.images_path, image_path))
            self.images.append(image_file)

        self.current_images = updated_images

        self.selection_model.set_selected(
            self.selection_model.get_n_items() - 1)

        return True

    @Gtk.Template.Callback("factory_setup")
    def factory_setup(self, _factory, list_item):
        picture = Gtk.Picture(
            margin_top=6,
            margin_bottom=6,
            height_request=60
        )
        list_item.set_child(picture)

    @Gtk.Template.Callback("factory_bind")
    def factory_bind(self, _factory, list_item):
        picture = list_item.get_child()
        image = list_item.get_item()

        picture.set_file(image)

    def on_image_selected(self, *args):
        self.main_picture.set_file(self.selection_model.get_selected_item())

    @Gtk.Template.Callback("on_click_released")
    def on_click_released(self, gesture, n_clicks, x, y):
        if n_clicks == 2:
            if self.main_picture.get_size_request() == (-1, -1):
                self.main_picture.set_size_request(500, 600)
            else:
                self.main_picture.set_size_request(-1, -1)
        # elif n_clicks == 1:
