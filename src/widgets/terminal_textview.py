# window.py
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

from gi.repository import Gtk, Pango

import re


class TerminalTextView(Gtk.TextView):
    __gtype_name__ = 'TerminalTextView'

    ESCAPE_SEQUENCE_RE = re.compile(r'\033\[(\d+(;\d+)*)m')

    STYLE_MAP = {
        '0': {'foreground': None, 'background': None, 'weight': Pango.Weight.NORMAL, 'style': Pango.Style.NORMAL, 'underline': Pango.Underline.NONE},  # Reset
        '1': {'weight': Pango.Weight.BOLD},  # Bold
        '3': {'style': Pango.Style.ITALIC},  # Italic
        '4': {'underline': Pango.Underline.SINGLE},  # Underline
        '7': {'inverse': True},  # Inverse (swap foreground and background)
        '22': {'weight': Pango.Weight.NORMAL},  # Normal color or intensity
        '23': {'style': Pango.Style.NORMAL},  # Reset italic
        '24': {'underline': Pango.Underline.NONE},  # Reset underline
        '27': {'inverse': False},  # Reset inverse

        # Foreground colors
        '30': {'foreground': 'black'},
        '31': {'foreground': 'red'},
        '32': {'foreground': 'green'},
        '33': {'foreground': 'yellow'},
        '34': {'foreground': 'blue'},
        '35': {'foreground': 'magenta'},
        '36': {'foreground': 'cyan'},
        '37': {'foreground': 'white'},
        '90': {'foreground': 'gray'},  # Bright black (usually gray)

        # Background colors
        '40': {'background': 'black'},
        '41': {'background': 'red'},
        '42': {'background': 'green'},
        '43': {'background': 'yellow'},
        '44': {'background': 'blue'},
        '45': {'background': 'magenta'},
        '46': {'background': 'cyan'},
        '47': {'background': 'white'},
        '100': {'background': 'gray'},  # Bright black (usually gray)
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_wrap_mode(Gtk.WrapMode.WORD)
        self.set_editable(False)
        self.set_cursor_visible(False)
        self.set_css_classes(["output-text-view"])
        self.set_monospace(True)
        self.set_wrap_mode(Gtk.WrapMode.CHAR)
        self.set_input_purpose(Gtk.InputPurpose.TERMINAL)

        self.current_tags = {
            'foreground': None,
            'background': None,
            'weight': None,
            'style': None,
            'underline': None,
        }
        self.inverse = False

    def insert_with_escapes(self, text):
        buffer = self.get_buffer()
        iter = buffer.get_end_iter()

        last_end = 0

        for match in self.ESCAPE_SEQUENCE_RE.finditer(text):
            start, end = match.span()
            if start > last_end:
                buffer.insert_with_tags(iter, text[last_end:start], *self.get_current_tags(buffer))

            codes = match.group(1).split(';')
            for code in codes:
                style = self.STYLE_MAP.get(code, {})
                if 'foreground' in style:
                    self.current_tags['foreground'] = style['foreground']
                if 'background' in style:
                    self.current_tags['background'] = style['background']
                if 'weight' in style:
                    self.current_tags['weight'] = style['weight']
                if 'style' in style:
                    self.current_tags['style'] = style['style']
                if 'underline' in style:
                    self.current_tags['underline'] = style['underline']
                if 'inverse' in style:
                    self.inverse = style['inverse']
                    if self.inverse:
                        self.current_tags['foreground'], self.current_tags['background'] = (
                            self.current_tags['background'],
                            self.current_tags['foreground'],
                        )

            last_end = end

        if last_end < len(text):
            buffer.insert_with_tags(iter, text[last_end:], *self.get_current_tags(buffer))

    def get_current_tags(self, buffer):
        tags = []
        if self.current_tags['foreground']:
            tags.append(buffer.create_tag(foreground=self.current_tags['foreground']))
        if self.current_tags['background']:
            tags.append(buffer.create_tag(background=self.current_tags['background']))
        if self.current_tags['weight']:
            tags.append(buffer.create_tag(weight=self.current_tags['weight']))
        if self.current_tags['style']:
            tags.append(buffer.create_tag(style=self.current_tags['style']))
        if self.current_tags['underline'] is not None:
            tags.append(buffer.create_tag(underline=self.current_tags['underline']))
        return tags
