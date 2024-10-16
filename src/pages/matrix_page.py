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
from gi.repository import Panel

from ..others.save_delegate import GenericSaveDelegate

from ..widgets.matrix_viewer import MatrixViewer, MatrixRow, Matrix

from ..interfaces.cursor import ICursor
from ..interfaces.saveable import ISaveable

import os
import csv
import io


class MatrixPage(Panel.Widget, ISaveable, ICursor):
    __gtype_name__ = 'MatrixPage'

    path = GObject.Property(type=str, default="")

    def __init__(self, _path=None):
        super().__init__()

        self.connect("unrealize", self.__on_unrealized)

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

        # SET UP

        self.matrix_viewer = MatrixViewer()
        self.matrix_viewer.set_vexpand(True)
        self.matrix_viewer.set_hexpand(True)

        self.scrolled_window = Gtk.ScrolledWindow()

        self.scrolled_window.set_child(self.matrix_viewer)

        self.set_child(self.scrolled_window)

        self.set_title("Matrix.odt")
        self.set_icon_name("table-symbolic")

        # ADD SAVE DELEGATE

        self.save_delegate = GenericSaveDelegate(self)
        self.set_save_delegate(self.save_delegate)

        if not _path:
            self.save_delegate.set_is_draft(True)

        # LOAD File

        if _path:
            gfile = Gio.File.new_for_path(_path)

            file_info = gfile.query_info("standard::content-type", 0, None)
            mime_type = file_info.get_content_type()

            match mime_type:
                case "text/csv":
                    matrix = self.matrix_from_csv(gfile)

            self.matrix_viewer.set_matrix(matrix)

            self.set_path(_path)

    def on_text_changed(self, *args):
        self.set_modified(True)

    def matrix_from_csv(self, file):
        # Open the file for reading
        file_input_stream = file.read()
        data_input_stream = Gio.DataInputStream.new(file_input_stream)

        # Read the entire file into memory as a single string
        csv_content = ""
        while True:
            line = data_input_stream.read_line_utf8()[0]
            if line is None:
                break
            csv_content += line + "\n"

        # Close streams
        data_input_stream.close()
        file_input_stream.close()

        # Use io.StringIO to wrap csv_content and csv.reader to handle parsing
        matrix = Matrix()

        # Use io.StringIO to read the CSV content as a file-like object
        csv_file = io.StringIO(csv_content)
        csv_reader = csv.reader(csv_file)

        # Read the first line to determine the columns
        try:
            column_names = next(csv_reader)
            for column_name in column_names:
                matrix.add_column(column_name.strip())
        except StopIteration:
            return matrix  # Return an empty matrix if the file is empty

        # Read the remaining lines for data
        row_number = 1
        for cells in csv_reader:
            row = MatrixRow()
            for cell in cells:
                row.append(cell.strip())  # Add each cell to the row
            row.set_number(row_number)
            matrix.append(row)
            row_number += 1

        return matrix

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

    def disconnect(self, *args):
        self.save_delegate.disconnect_all()

        print(f"closing: {self}")

    def __del__(self, *args):
        print(f"DELETING {self}")
