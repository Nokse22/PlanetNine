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


def get_mime_icon(mimetype):
    mime_to_icon = {
        "text/x-python": "text-x-python-symbolic",

        "application/x-ipynb+json": "notepad-symbolic",

        "image/png": "image-symbolic",
        "image/jpeg": "image-symbolic",
        "image/gif": "image-symbolic",
        "image/bmp": "image-symbolic",
        "image/svg+xml": "image-symbolic",

        "text/markdown": "text-markdown-symbolic",

        "text/plain": "text-symbolic",

        "text/csv": "table-symbolic",

        "application/json": "text-json-symbolic",
        "application/geo+json": "text-json-symbolic",

        "text/html": "text-html-symbolic",

        "application/x-tex": "text-x-tex-symbolic",

        "application/xml": "text-xml-symbolic",

        "application/javascript": "text-javascript-symbolic",

        "application/x-yaml": "text-yaml-symbolic",
        "text/yaml": "text-yaml-symbolic",

        "application/pdf": "application-pdf-symbolic",
    }

    if mimetype is None:
        return "paper-symbolic"

    return mime_to_icon.get(mimetype.lower(), "paper-symbolic")


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
