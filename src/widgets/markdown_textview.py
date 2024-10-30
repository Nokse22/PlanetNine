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

from gi.repository import Gtk, Pango, GObject
from ..interfaces.style_update import IStyleUpdate
from ..interfaces.disconnectable import IDisconnectable

import sys
import re


class MarkdownTextView(Gtk.TextView, IStyleUpdate, IDisconnectable):
    __gtype_name__ = 'MarkdownTextView'

    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.TextBuffer,)),
    }

    def __init__(self):
        super().__init__()
        self.buffer = self.get_buffer()

        self.set_css_name("markdownview")

        self.set_wrap_mode(Gtk.WrapMode.WORD)
        self.set_monospace(True)

        self.set_size_request(-1, 18)

        self.foreground_accent_tags = []

        for scale in range(1, 7):
            self.foreground_accent_tags.append(
                self.buffer.create_tag(
                    f"h{scale}",
                    weight=Pango.Weight.BOLD,
                    scale=2.0-(scale-1)/5)
            )

        self.buffer.create_tag(
            "bold", weight=Pango.Weight.BOLD)
        self.buffer.create_tag(
            "italic", style=Pango.Style.ITALIC)
        self.buffer.create_tag(
            "bold_italic", weight=Pango.Weight.BOLD, style=Pango.Style.ITALIC)

        self.link_tag = self.buffer.create_tag(
            "link", underline=Pango.Underline.SINGLE)
        self.quote_tag = self.buffer.create_tag(
            "quote", style=Pango.Style.ITALIC,
            left_margin=20)
        self.code_tag = self.buffer.create_tag(
            "code", style=Pango.Style.OBLIQUE)
        self.block_code_tag = self.buffer.create_tag(
            "block_code", family="Monospace")

        self.full_line_tags = [
            ("# ", "h1"),
            ("## ", "h2"),
            ("### ", "h3"),
            ("#### ", "h4"),
            ("##### ", "h5"),
            ("###### ", "h6"),
        ]

        self.in_line_tags = [
            ("**", "bold"),
            ("***", "bold_italic"),
            ("___", "bold_italic"),
            ("*", "italic"),
            ("_", "italic"),
            ("`", "code"),
        ]

        self.buffer.connect("changed", self.on_text_changed)
        self.buffer.connect_after("insert-text", self.on_text_inserted)
        self.buffer.connect("delete-range", self.on_text_deleted)

        IStyleUpdate.__init__(self)

    def set_text(self, text):
        self.buffer.set_text(text)
        self.update_all()

    def update_all(self):
        start_iter = self.buffer.get_start_iter()
        end_iter = self.buffer.get_end_iter()

        text = self.buffer.get_text(start_iter, end_iter, True)

        # Remove all tags first
        self.buffer.remove_all_tags(start_iter, end_iter)

        # Apply full line tags
        for line_start, line_tag in self.full_line_tags:
            pattern = re.compile(
                f'^({re.escape(line_start)}.*)$', re.MULTILINE)
            for match in pattern.finditer(text):
                start_pos = match.start(1)
                end_pos = match.end(1)
                iter_start = self.buffer.get_iter_at_offset(start_pos)
                iter_end = self.buffer.get_iter_at_offset(end_pos)
                self.buffer.apply_tag_by_name(line_tag, iter_start, iter_end)

        # Apply in-line tags
        for inline_tag, tag_name in self.in_line_tags:
            pattern = re.compile(
                f'({re.escape(inline_tag)}.*?{re.escape(inline_tag)})')
            for match in pattern.finditer(text):
                start_pos = match.start(1)
                end_pos = match.end(1)
                iter_start = self.buffer.get_iter_at_offset(start_pos)
                iter_end = self.buffer.get_iter_at_offset(end_pos)
                self.buffer.apply_tag_by_name(tag_name, iter_start, iter_end)

        # Apply multi-line code block tags
        block_code_pattern = re.compile(r'(```.*?```)', re.DOTALL)
        for match in block_code_pattern.finditer(text):
            start_pos = match.start(1)
            end_pos = match.end(1)
            iter_start = self.buffer.get_iter_at_offset(start_pos)
            iter_end = self.buffer.get_iter_at_offset(end_pos)
            self.buffer.apply_tag_by_name("block_code", iter_start, iter_end)

        # Apply link tags
        link_pattern = re.compile(r'\[(.*?)\]\((.*?)\)')
        for match in link_pattern.finditer(text):
            link_text_start = match.start(1)
            link_text_end = match.end(1)
            iter_start = self.buffer.get_iter_at_offset(link_text_start)
            iter_end = self.buffer.get_iter_at_offset(link_text_end)
            self.buffer.apply_tag_by_name("link", iter_start, iter_end)

    def on_text_changed(self, buffer):
        self.emit("changed", buffer)

        self.update_all()
        return

        cursor_iter = buffer.get_iter_at_mark(buffer.get_insert())
        line_start_iter = cursor_iter.copy()
        line_start_iter.set_line_offset(0)
        line_end_iter = cursor_iter.copy()
        line_end_iter.forward_to_line_end()

        line_text = buffer.get_text(line_start_iter, line_end_iter, False)

        for tag, tag_name in self.full_line_tags:
            if line_text.startswith(tag):
                buffer.apply_tag_by_name(
                    tag_name, line_start_iter, line_end_iter)
            else:
                buffer.remove_tag_by_name(
                    tag_name, line_start_iter, line_end_iter)

        start_iter = cursor_iter.copy()
        start_iter.backward_chars(2)

        text = buffer.get_text(start_iter, cursor_iter, False)

        for tag, tag_name in self.in_line_tags:
            if text.endswith(tag):
                start_search_iter = cursor_iter.copy()
                start_search_iter.backward_chars(len(tag))

                start_iter.backward_chars(200)

                if start_search_iter.backward_search(
                        tag, Gtk.TextSearchFlags.TEXT_ONLY):
                    match_start, match_end = start_search_iter.backward_search(
                        tag, Gtk.TextSearchFlags.TEXT_ONLY)
                    if (len(buffer.get_text(match_start, cursor_iter, False))
                            != 2 * len(tag)):
                        buffer.apply_tag_by_name(
                            tag_name, match_start, cursor_iter)
                        break

    def on_text_deleted(self, buffer, start, end):
        self.update_all()
        return

        deleted_text = buffer.get_text(start, end, False)

        for tag, tag_name in self.in_line_tags:
            if deleted_text in tag or tag in deleted_text:
                cursor_iter = start.copy()
                if cursor_iter.backward_search(
                        tag, Gtk.TextSearchFlags.TEXT_ONLY, None):
                    match_start, match_end = cursor_iter.backward_search(
                        tag, Gtk.TextSearchFlags.TEXT_ONLY)

                    # Remove the corresponding text tag
                    buffer.remove_tag_by_name(tag_name, match_end, start)
                    break

    def on_text_inserted(self, buffer, loc, text, length):
        if text == '\n':
            start_iter = loc.copy()
            start_iter.backward_char()
            start_iter.set_line_offset(0)

            end_iter = start_iter.copy()
            end_iter.forward_chars(2)
            chars = buffer.get_text(start_iter, end_iter, False)

            simple_regex_pattern = r'^[-+*] $'
            if re.match(simple_regex_pattern, chars):
                bullet = chars[0]
                line_end = loc.copy()
                line_end.backward_char()
                if line_end.get_line_offset() == 2:
                    start_iter.set_line_offset(0)
                    buffer.delete(start_iter, loc)
                else:
                    buffer.insert(loc, bullet + ' ', -1)
            else:
                search_limit = start_iter.copy()
                search_end = start_iter.copy()
                search_limit.forward_chars(10)

                def is_space(ch, _):
                    return ch == ' '

                search_end.forward_find_char(is_space, search_limit)
                search_end.forward_char()
                chars = buffer.get_text(start_iter, search_end, False)

                ordered_regex_pattern = r'^\d+\. $'
                if re.match(ordered_regex_pattern, chars):
                    current_order = int(chars[:-2])
                    new_order = current_order + 1
                    new_order_bullet = f'{new_order}. '
                    line_end = loc.copy()
                    line_end.backward_char()

                    if (line_end.get_line_offset()
                            == len(str(current_order)) + 2):
                        start_iter.set_line_offset(0)
                        buffer.delete(start_iter, loc)
                    else:
                        buffer.insert(loc, new_order_bullet, -1)

    def update_style_scheme(self, *_args):
        """Updates the accent color"""

        accent_color = self.style_manager.get_accent_color()
        if self.style_manager.get_dark():
            bg_color = "#3F3F3F"
        else:
            bg_color = "#E0E0E0"

        self.link_tag.set_property("foreground", accent_color)
        self.quote_tag.set_property("background", bg_color)
        self.code_tag.set_property("background", bg_color)
        self.block_code_tag.set_property("background", bg_color)

        for tag in self.foreground_accent_tags:
            tag.set_property("foreground", accent_color)

    def disconnect(self, *_args):
        self.buffer.disconnect_by_func(self.on_text_changed)
        self.buffer.disconnect_by_func(self.on_text_inserted)
        self.buffer.disconnect_by_func(self.on_text_deleted)

        self.style_manager.disconnect_by_func(self.update_style_scheme)

        print("unrealize:", sys.getrefcount(self))

    def __del__(self, *_args):
        print(f"DELETING {self}")
