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
import shutil


#   Setup

def setup_module(module):
    diff_path = './diffs'

    if os.path.exists(diff_path):
        shutil.rmtree(diff_path)

    os.makedirs(diff_path)


#   Import Export Tests Start

def test_images_url_display(monkeypatch):
    __test_file('./data/images_url_display.ipynb')


def test_json_display(monkeypatch):
    __test_file('./data/json_display.ipynb')


def test_markdown_cell(monkeypatch):
    __test_file('./data/markdown_cell.ipynb')


def test_markdown_display(monkeypatch):
    __test_file('./data/markdown_display.ipynb')


def test_png_file_display(monkeypatch):
    __test_file('./data/png_file_display.ipynb')


def test_png_graph_display(monkeypatch):
    __test_file('./data/png_graph_display.ipynb')


def test_stream_output(monkeypatch):
    __test_file('./data/stream_output.ipynb')


def test_text_output(monkeypatch):
    __test_file('./data/text_output.ipynb')


#   Tear down

def teardown_module(module):
    pass


# Test

def __test_file(full_path):
    if os.path.isdir(full_path):
        return

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

            file_name = os.path.basename(full_path).split(".")[0]

            diff_path = f'./diffs/{file_name}-diff.html'
            with open(diff_path, 'w') as diff_file:
                diff_file.write(diff_html)

            print(f"Diff has been written to {diff_path}")

            raise AssertionError
