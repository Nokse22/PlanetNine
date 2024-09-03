# test_import_export.py
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

from src.models.notebook import Notebook

import os
import nbformat
import difflib


def test_import_export(monkeypatch):

    directory = './data'

    for file_name in os.listdir(directory):
        full_path = os.path.join(directory, file_name)

        if os.path.isdir(full_path):
            continue

        notebook = Notebook.new_from_file(full_path)

        output = nbformat.writes(notebook.get_notebook_node())

        with open(full_path, 'r') as file:
            file_content = file.read()[:-1]
            try:
                assert output == file_content
            except AssertionError:
                html_diff = difflib.HtmlDiff()
                diff_html = html_diff.make_file(
                    file_content.splitlines(),
                    output.splitlines(),
                    fromdesc='Original File',
                    todesc='Exported Output'
                )

                diff_file_path = os.path.join('./', 'diffs', f'{file_name.split(".")[0]}-diff.html')
                with open(diff_file_path, 'w') as diff_file:
                    diff_file.write(diff_html)

                print(f"Diff has been written to {diff_file_path}")

                raise AssertionError
