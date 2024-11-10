# converters.py
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

import os


def get_mime_icon(filename):
    ext_to_icon = {
        ".py": "text-x-python-symbolic",

        ".ipynb": "notepad-symbolic",

        ".png": "image-symbolic",
        ".jpg": "image-symbolic",
        ".jpeg": "image-symbolic",
        ".gif": "image-symbolic",
        ".bmp": "image-symbolic",
        ".svg": "image-symbolic",

        ".md": "text-markdown-symbolic",

        ".txt": "text-symbolic",

        ".csv": "table-symbolic",

        ".json": "text-json-symbolic",
        ".geojson": "text-json-symbolic",

        ".html": "text-html-symbolic",
        ".htm": "text-html-symbolic",

        ".tex": "text-x-tex-symbolic",

        ".xml": "text-xml-symbolic",

        ".js": "text-javascript-symbolic",

        ".yaml": "text-yaml-symbolic",
        ".yml": "text-yaml-symbolic",

        ".pdf": "application-pdf-symbolic",
    }

    _, ext = os.path.splitext(filename)

    return ext_to_icon.get(ext.lower(), "paper-symbolic")


def get_language_icon(lang):
    languages_to_icon = {
        "python": "text-x-python-symbolic",
        "octave": "octave-symbolic",
        "julia": "julia-symbolic",
        "R": "r-symbolic",
    }

    return languages_to_icon.get(lang, "processor-symbolic")


def get_language_highlight_name(lang):
    languages_to_name = {
        "python": "python3",
        "octave": "octave",
    }

    return languages_to_name.get(lang, "python3")


def is_mime_displayable(mime_type):
    text_mimetypes = [
        'application/json',
        'application/xml',
        'application/javascript',
        'application/x-www-form-urlencoded',
        'application/sql',
        'application/x-zerosize'
    ]

    if mime_type.startswith('text/') or mime_type in text_mimetypes:
        return True
    return False
