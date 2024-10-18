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

from gi.repository import Gtk, Panel, GLib, Gio, Gdk

from gettext import gettext as _

import os
import asyncio
import datetime


@Gtk.Template(
    resource_path='/io/github/nokse22/PlanetNine/gtk/images_panel.ui')
class ImagesPanel(Panel.Widget):
    __gtype_name__ = 'ImagesPanel'

    main_picture = Gtk.Template.Child()
    list_view = Gtk.Template.Child()
    view_stack = Gtk.Template.Child()
    scrolled_window = Gtk.Template.Child()

    cache_dir = os.environ["XDG_CACHE_HOME"]
    images_path = os.path.join(cache_dir, "g_images")

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

        if new_images == []:
            return

        for image_path in new_images:
            image_file = Gio.File.new_for_path(
                os.path.join(self.images_path, image_path))
            self.images.append(image_file)

        self.current_images = updated_images

        self.selection_model.set_selected(
            self.selection_model.get_n_items() - 1)

        vadj = self.scrolled_window.get_vadjustment()
        vadj.set_value(vadj.get_upper() - vadj.get_page_size())

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

    @Gtk.Template.Callback("on_save_clicked")
    def on_save_clicked(self, *args):
        asyncio.create_task(self._save_file())

    async def _save_file(self):
        source_file = self.selection_model.get_selected_item()

        file_dialog = Gtk.FileDialog(
            accept_label="Save Image",
            initial_name=_("Image.png"),
            modal=True
        )

        try:
            result = await file_dialog.save(self.get_root())
        except Exception as e:
            print(e)
            return

        destination_file = Gio.File.new_for_path(result.get_path())

        try:
            source_stream = await source_file.read_async(None)
        except GLib.Error as e:
            print(f"Error reading source file: {e.message}")
            return

        try:
            destination_stream = await destination_file.create_async(
                Gio.FileCreateFlags.REPLACE_DESTINATION, None)
        except GLib.Error as e:
            print(f"Error creating destination file: {e.message}")
            await source_stream.close_async()
            return

        try:
            while True:
                data = source_stream.read_bytes(8192, None)
                if data.get_size() == 0:
                    break
                destination_stream.write_bytes(data, None)
        except GLib.Error as e:
            print(f"Error writing to destination file: {e.message}")
        finally:
            await source_stream.close_async()
            await destination_stream.close_async()

    @Gtk.Template.Callback("on_copy_clicked")
    def on_copy_clicked(self, *args):
        asyncio.create_task(self._copy_file())

    async def _copy_file(self):
        source_file = self.selection_model.get_selected_item()

        try:
            stream = await source_file.read_async(None)
            content = await stream.read_bytes_async(
                source_file.query_info(
                    "*",
                    Gio.FileQueryInfoFlags.NONE,
                    None).get_size(),
                None)
            await stream.close_async()
        except GLib.Error as e:
            print(f"Error reading file: {e.message}")
            return

        content_provider = Gdk.ContentProvider.new_for_bytes(
            "image/png",
            GLib.Bytes(content.get_data()))
        clipboard = Gdk.Display().get_default().get_clipboard()
        clipboard.set_content(content_provider)

    @Gtk.Template.Callback("on_delete_clicked")
    def on_delete_clicked(self, *args):
        asyncio.create_task(self._delete_file())

    async def _delete_file(self):
        source_file = self.selection_model.get_selected_item()

        try:
            deleted = await source_file.delete_async(0)
            print(f"File '{source_file.get_path()}' deleted successfully.")
        except GLib.Error as e:
            print(f"Error deleting file: {e.message}")
            return

        if deleted:
            success, position = self.images.find(source_file)
            self.images.remove(position)

    @Gtk.Template.Callback("on_open_external_window_clicked")
    def on_open_external_window_clicked(self, *args):
        asyncio.create_task(self._open_file())

    async def _open_file(self):
        source_file = self.selection_model.get_selected_item()

        launcher = Gtk.FileLauncher.new(source_file)

        try:
            await launcher.launch(self.get_root(), None)
        except Exception as e:
            print(e)
