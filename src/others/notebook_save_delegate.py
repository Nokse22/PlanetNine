# notebook_save_delegate.py
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

from gi.repository import Panel, Gtk

import nbformat
import os
import asyncio


class NotebookSaveDelegate(Panel.SaveDelegate):
    __gtype_name__ = 'NotebookSaveDelegate'

    def __init__(self, page):
        super().__init__()

        self.page = page

        self.bind_property("title", self.page, "title")
        self.bind_property("icon-name", self.page, "icon-name")

    def do_save(self, task):
        print("save")

        return True

    def do_close(self):
        print("close")

        self.page.force_close()

    def do_discard(self):
        self.page.force_close()

    def do_save_async(self, cancellable, callback, *args):
        if self.get_is_draft():
            asyncio.create_task(self.__do_save_async())
        else:
            self.save()
            self.set_is_draft(False)

    async def __do_save_async(self):
        dialog = Gtk.FileDialog(
            title=_("Save")
        )

        try:
            file = await dialog.save(self.page.get_root())

            notebook_path = file.get_path()
            self.page.notebook_model.path = notebook_path

            self.save()

        except Exception as e:
            print(e)

    def do_save_finish(self, result, error):
        print("Async save completed.")

    def save(self):
        notebook = self.page.notebook_model

        notebook_path = self.page.notebook_model.path

        if notebook_path:
            nbformat.write(notebook.get_notebook_node(), notebook_path)
            self.page.set_modified(False)

