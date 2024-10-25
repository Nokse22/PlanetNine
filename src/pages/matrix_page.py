# matrix_page.py
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

from gi.repository import Gtk, GObject, Gio
from gi.repository import Panel, GLib

from ..others.save_delegate import GenericSaveDelegate

from ..widgets.matrix_viewer import MatrixViewer, MatrixRow, Matrix

from ..interfaces.saveable import ISaveable
from ..interfaces.language import ILanguage

import os
import csv
import io
import asyncio


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/matrix_page.ui')
class MatrixPage(Panel.Widget, ISaveable, ILanguage):
    __gtype_name__ = 'MatrixPage'

    matrix_viewer = Gtk.Template.Child()
    stack = Gtk.Template.Child()

    path = GObject.Property(type=str, default="")

    def __init__(self, _path=None):
        super().__init__()

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

        # SET UP

        self.language = "csv"

        self.matrix = Matrix()

        # ADD SAVE DELEGATE

        self.save_delegate = GenericSaveDelegate(self)
        self.set_save_delegate(self.save_delegate)

        if not _path:
            self.save_delegate.set_is_draft(True)

        # LOAD File

        self.set_path(_path)

        asyncio.create_task(self._load_file(_path))

    def on_text_changed(self, *_args):
        self.set_modified(True)

    async def _load_file(self, file_path):
        if file_path:
            gfile = Gio.File.new_for_path(file_path)

            file_info = gfile.query_info("standard::content-type", 0, None)
            mime_type = file_info.get_content_type()

            match mime_type:
                case "text/csv":
                    await self._matrix_from_csv(gfile)

            self.matrix_viewer.set_matrix(self.matrix)
            self.stack.set_visible_child_name("matrix")

    async def _matrix_from_csv(self, file):
        file_input_stream = file.read()
        data_input_stream = Gio.DataInputStream.new(file_input_stream)

        if data_input_stream is None:
            return

        csv_content = ""
        while True:
            line, _ = await data_input_stream.read_line_async(0)
            line = line.decode('utf-8')
            if line == '':
                break
            csv_content += line + "\n"

        data_input_stream.close()
        file_input_stream.close()

        csv_file = io.StringIO(csv_content)
        csv_reader = csv.reader(csv_file)

        try:
            column_names = next(csv_reader)
            for column_name in column_names:
                self.matrix.add_column(column_name.strip())
        except Exception as e:
            print(e)

        row_number = 1
        for cells in csv_reader:
            row = MatrixRow()
            for cell in cells:
                row.append(cell.strip())
            row.set_number(row_number)
            self.matrix.append(row)
            row_number += 1

    #
    #   Implement Language Interface
    #

    def set_language(self, _language):
        self.language = _language

        self.emit('language-changed')

    #
    #   Implement Saveable Page Interface
    #

    def get_path(self):
        return self.path

    def set_path(self, _path):
        self.path = _path
        self.set_title(
            os.path.basename(self.path) if self.path else "Untitled")

    def get_content(self):
        return ""

    #
    #   Implement Disconnectable Interface
    #

    def disconnect(self, *_args):
        self.save_delegate.disconnect_all()
        self.matrix_viewer.disconnect()

        print(f"Disconnected:  {self}")

    def __del__(self, *_args):
        print(f"DELETING {self}")
