# save_delegate.py
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
import asyncio

from gettext import gettext as _


class GenericSaveDelegate(Panel.SaveDelegate):
    __gtype_name__ = 'GenericSaveDelegate'

    def __init__(self, page):
        super().__init__()
        self.bindings = []

        self.page = page

        self.bindings.append(
            self.bind_property("title", self.page, "title"))
        self.bindings.append(
            self.bind_property("icon-name", self.page, "icon-name"))

        self.set_title("")

        self.update_draft_status()

    def disconnect_all(self):
        for binding in self.bindings:
            binding.unbind()
        del self.bindings

        del self.page

    def update_draft_status(self):
        self.set_is_draft(bool(self.page.get_path()))

    def do_close(self):
        print("do close")

    def do_discard(self):
        print("do discard")
        self.page.force_close()
        self.emit("close")

    def do_save_async(self, cancellable, callback, user_data):
        print("DRAFT: ", self.get_is_draft())
        if self.get_is_draft():
            asyncio.create_task(
                self._do_save_async()
            )
        else:
            asyncio.create_task(
                self._save_content(
                    self.page.get_path(),
                    self.page.get_content()
                )
            )

    async def _do_save_async(self):
        dialog = Gtk.FileDialog(
            title=_("Save")
        )

        try:
            file = await dialog.save(self.page.get_root())

            page_path = file.get_path()
            self.page.set_path(page_path)

            await self._save_content(page_path, self.page.get_content())

            self.set_is_draft(False)

        except Exception as e:
            print(e)

    def do_save_finish(self, result):
        return result.propagate_boolean()

    async def _show_save_dialog(self):
        dialog = Gtk.FileDialog(title="Save")
        try:
            return await dialog.save(self.page.get_root())
        except GObject.GError:
            return None

    async def _save_content(self, file_path, content):
        file = Gio.File.new_for_path(file_path)

        try:
            if isinstance(content, str):
                content = content.encode('utf-8')

            output_stream = await file.replace_async(
                etag=None,
                make_backup=True,
                flags=Gio.FileCreateFlags.NONE,
                io_priority=GLib.PRIORITY_DEFAULT,
                cancellable=None
            )

            bytes_written = await output_stream.write_bytes_async(
                GLib.Bytes.new(content),
                io_priority=GLib.PRIORITY_DEFAULT,
                cancellable=None
            )

            await output_stream.close_async(
                io_priority=GLib.PRIORITY_DEFAULT,
                cancellable=None
            )

            print(f"File written successfully: {file_path}")

            self.page.set_modified(False)

            return bytes_written
        except Exception as e:
            print(f"Error writing file: {e}")
            return None

