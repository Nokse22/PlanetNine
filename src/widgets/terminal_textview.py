# terminal_textview.py
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

from gi.repository import Gtk, Pango
from ..interfaces.style_update import IStyleUpdate
from ..interfaces.disconnectable import IDisconnectable
import re


class TerminalTextView(Gtk.TextView, IStyleUpdate):
    __gtype_name__ = "TerminalTextView"

    ESCAPE_SEQUENCE_RE = re.compile(r"\033\[(\d+(;\d+)*)m")

    STYLE_MAP = {
        "0": ["reset"],  # Reset all attributes
        "1": ["sgr_1"],  # Bold
        "3": ["sgr_3"],  # Italic
        "4": ["sgr_4"],  # Underline
        "7": ["sgr_7"],  # Inverse
        "22": ["reset_weight"],  # Normal weight
        "23": ["reset_style"],  # Reset italic
        "24": ["reset_underline"],  # Reset underline
        "27": ["reset_inverse"],  # Reset inverse
        # Foreground colors
        "30": ["fg_30"],  # Black
        "31": ["fg_31"],  # Red
        "32": ["fg_32"],  # Green
        "33": ["fg_33"],  # Yellow
        "34": ["fg_34"],  # Blue
        "35": ["fg_35"],  # Magenta
        "36": ["fg_36"],  # Cyan
        "37": ["fg_37"],  # White
        "90": ["fg_90"],  # Bright Black (Gray)
        "91": ["fg_91"],  # Bright Red
        "92": ["fg_92"],  # Bright Green
        "93": ["fg_93"],  # Bright Yellow
        "94": ["fg_94"],  # Bright Blue
        "95": ["fg_95"],  # Bright Magenta
        "96": ["fg_96"],  # Bright Cyan
        "97": ["fg_97"],  # Bright White
        # Background colors
        "40": ["bg_40"],  # Black
        "41": ["bg_41"],  # Red
        "42": ["bg_42"],  # Green
        "43": ["bg_43"],  # Yellow
        "44": ["bg_44"],  # Blue
        "45": ["bg_45"],  # Magenta
        "46": ["bg_46"],  # Cyan
        "47": ["bg_47"],  # White
        "100": ["bg_100"],  # Bright Black (Gray)
        "101": ["bg_101"],  # Bright Red
        "102": ["bg_102"],  # Bright Green
        "103": ["bg_103"],  # Bright Yellow
        "104": ["bg_104"],  # Bright Blue
        "105": ["bg_105"],  # Bright Magenta
        "106": ["bg_106"],  # Bright Cyan
        "107": ["bg_107"],  # Bright White
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        IDisconnectable.__init__(self)

        self.set_wrap_mode(Gtk.WrapMode.WORD)
        self.set_editable(False)
        self.set_cursor_visible(False)
        self.set_css_classes(["output-text-view"])
        self.set_monospace(True)
        self.set_wrap_mode(Gtk.WrapMode.CHAR)
        self.set_input_purpose(Gtk.InputPurpose.TERMINAL)
        self.set_size_request(-1, 18)

        self.current_tags = set()
        self.buffer = self.get_buffer()
        self._create_tags()

        IStyleUpdate.__init__(self)

    def _create_tags(self):
        # Standard foreground colors (30-37)
        self.buffer.create_tag("fg_30", foreground="#000000")  # Black
        self.buffer.create_tag("fg_31", foreground="#FF0000")  # Red
        self.buffer.create_tag("fg_32", foreground="#00FF00")  # Green
        self.buffer.create_tag("fg_33", foreground="#FFFF00")  # Yellow
        self.buffer.create_tag("fg_34", foreground="#0000FF")  # Blue
        self.buffer.create_tag("fg_35", foreground="#FF00FF")  # Magenta
        self.buffer.create_tag("fg_36", foreground="#00FFFF")  # Cyan
        self.buffer.create_tag("fg_37", foreground="#FFFFFF")  # White

        # Bright foreground colors (90-97)
        self.buffer.create_tag("fg_90", foreground="#808080")  # Bright Black
        self.buffer.create_tag("fg_91", foreground="#FF8080")  # Bright Red
        self.buffer.create_tag("fg_92", foreground="#80FF80")  # Bright Green
        self.buffer.create_tag("fg_93", foreground="#FFFF80")  # Bright Yellow
        self.buffer.create_tag("fg_94", foreground="#8080FF")  # Bright Blue
        self.buffer.create_tag("fg_95", foreground="#FF80FF")  # Bright Magenta
        self.buffer.create_tag("fg_96", foreground="#80FFFF")  # Bright Cyan
        self.buffer.create_tag("fg_97", foreground="#FFFFFF")  # Bright White

        # Standard background colors (40-47)
        self.buffer.create_tag("bg_40", background="#000000")  # Black
        self.buffer.create_tag("bg_41", background="#FF0000")  # Red
        self.buffer.create_tag("bg_42", background="#00FF00")  # Green
        self.buffer.create_tag("bg_43", background="#FFFF00")  # Yellow
        self.buffer.create_tag("bg_44", background="#0000FF")  # Blue
        self.buffer.create_tag("bg_45", background="#FF00FF")  # Magenta
        self.buffer.create_tag("bg_46", background="#00FFFF")  # Cyan
        self.buffer.create_tag("bg_47", background="#FFFFFF")  # White

        # Bright background colors (100-107)
        self.buffer.create_tag("bg_100", background="#808080")  # Bright Black
        self.buffer.create_tag("bg_101", background="#FF8080")  # Bright Red
        self.buffer.create_tag("bg_102", background="#80FF80")  # Bright Green
        self.buffer.create_tag("bg_103", background="#FFFF80")  # Bright Yellow
        self.buffer.create_tag("bg_104", background="#8080FF")  # Bright Blue
        self.buffer.create_tag("bg_105", background="#FF80FF")  # Bright Magenta
        self.buffer.create_tag("bg_106", background="#80FFFF")  # Bright Cyan
        self.buffer.create_tag("bg_107", background="#FFFFFF")  # Bright White

        # Style tags
        self.buffer.create_tag("reset")  # Empty tag for reset
        self.buffer.create_tag("sgr_1", weight=Pango.Weight.BOLD)
        self.buffer.create_tag("sgr_3", style=Pango.Style.ITALIC)
        self.buffer.create_tag("sgr_4", underline=Pango.Underline.SINGLE)
        self.buffer.create_tag("sgr_7")
        self.buffer.create_tag("sgr_9", strikethrough=True)

        # Reset tags
        self.buffer.create_tag("reset_weight", weight=Pango.Weight.NORMAL)
        self.buffer.create_tag("reset_style", style=Pango.Style.NORMAL)
        self.buffer.create_tag(
            "reset_underline", underline=Pango.Underline.NONE
        )
        self.buffer.create_tag("reset_inverse")

    def insert_with_escapes(self, text):
        buffer = self.get_buffer()
        end_iter = buffer.get_end_iter()

        text = re.sub(r"\x1b\[2K|\x1b\[(\?25h|\?25l)", "", text)

        segments = []
        current_segment = ""
        i = 0
        while i < len(text):
            if text[i] == "\r":
                if i + 1 < len(text) and text[i + 1] == "\n":
                    current_segment += "\r\n"
                    i += 2
                else:
                    segments.append(current_segment)
                    current_segment = ""
                    i += 1
            else:
                current_segment += text[i]
                i += 1

        if current_segment:
            segments.append(current_segment)

        if segments:
            self._insert_segment(segments[0], buffer, end_iter)

        for segment in segments[1:]:
            end_iter = buffer.get_end_iter()
            start_iter = end_iter.copy()
            start_iter.set_line_offset(0)

            if not segment.startswith("\n"):
                buffer.delete(start_iter, end_iter)

            self._insert_segment(segment, buffer, buffer.get_end_iter())

    def _insert_segment(self, text, buffer, end_iter):
        last_end = 0

        for match in self.ESCAPE_SEQUENCE_RE.finditer(text):
            start, end = match.span()

            if start > last_end:
                self._insert_text_with_current_tags(
                    end_iter, text[last_end:start])

            codes = match.group(1).split(";")
            for code in codes:
                if code == "0":
                    self.current_tags.clear()
                elif code in self.STYLE_MAP:
                    new_tags = set(self.STYLE_MAP[code])
                    for new_tag in new_tags:
                        if new_tag.startswith("fg_"):
                            self.current_tags = {
                                text_tag
                                for text_tag in self.current_tags
                                if not text_tag.startswith("fg_")
                            }
                        elif new_tag.startswith("bg_"):
                            self.current_tags = {
                                text_tag
                                for text_tag in self.current_tags
                                if not text_tag.startswith("bg_")
                            }
                    self.current_tags.update(new_tags)

            last_end = end

        if last_end < len(text):
            self._insert_text_with_current_tags(end_iter, text[last_end:])

    def _insert_text_with_current_tags(self, end_iter, text):
        if not self.current_tags:
            self.buffer.insert(end_iter, text)
            return

        text_tags = []
        for tag_name in self.current_tags:
            text_tag = self.buffer.get_tag_table().lookup(tag_name)
            if text_tag:
                text_tags.append(text_tag)

        self.buffer.insert_with_tags(
            end_iter, text, *text_tags
        )

    def reset(self):
        buffer = self.get_buffer()
        buffer.set_text("")
        self.current_tags.clear()

    def update_style_scheme(self, *_args):
        colors = self.style_manager.get_current_colors()

        for i in range(0, 16):
            fg_base = 3 if i < 8 else 9
            fg_tag = self.buffer.get_tag_table().lookup(f"fg_{fg_base}{i}")
            if fg_tag:
                fg_tag.set_property("foreground", colors[f"color{i}"])

            bg_base = 4 if i < 8 else 10
            bg_tag = self.buffer.get_tag_table().lookup(f"bg_{bg_base}{i}")
            if bg_tag:
                bg_tag.set_property("background", colors[f"color{i}"])

    def disconnect(self, *_args):
        IDisconnectable.disconnect(self)
        IStyleUpdate.disconnect(self)
