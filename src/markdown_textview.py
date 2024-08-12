import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Pango

import re

class MarkdownTextView(Gtk.TextView):
    __gtype_name__ = 'MarkdownTextView'

    def __init__(self):
        super().__init__()
        self.set_wrap_mode(Gtk.WrapMode.WORD)
        self.set_monospace(True)

        # Set up the TextBuffer and connect to its "changed" signal
        self.buffer = self.get_buffer()

        self.buffer.create_tag("h1", weight=Pango.Weight.BOLD, scale=2.5)
        self.buffer.create_tag("h2", weight=Pango.Weight.BOLD, scale=2.2)
        self.buffer.create_tag("h3", weight=Pango.Weight.BOLD, scale=1.9)
        self.buffer.create_tag("h4", weight=Pango.Weight.BOLD, scale=1.6)
        self.buffer.create_tag("h5", weight=Pango.Weight.BOLD, scale=1.3)
        self.buffer.create_tag("h6", weight=Pango.Weight.BOLD, scale=1)

        self.buffer.create_tag("bold", weight=Pango.Weight.BOLD)
        self.buffer.create_tag("italic", style=Pango.Style.ITALIC)
        self.buffer.create_tag("code", style=Pango.Style.OBLIQUE)

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
            ("*", "italic"),
            ("`", "code"),
        ]

        self.buffer.connect("changed", self.on_text_changed)
        self.buffer.connect_after("insert-text", self.on_text_inserted)
        self.buffer.connect("delete-range", self.on_text_deleted)

    def on_text_changed(self, buffer):
        cursor_iter = buffer.get_iter_at_mark(buffer.get_insert())
        line_start_iter = cursor_iter.copy()
        line_start_iter.set_line_offset(0)
        line_end_iter = cursor_iter.copy()
        line_end_iter.forward_to_line_end()

        line_text = buffer.get_text(line_start_iter, line_end_iter, False)

        for tag, tag_name in self.full_line_tags:
            if line_text.startswith(tag):
                buffer.apply_tag_by_name(tag_name, line_start_iter, line_end_iter)
            else:
                buffer.remove_tag_by_name(tag_name, line_start_iter, line_end_iter)

        start_iter = cursor_iter.copy()
        start_iter.backward_chars(2)

        text = buffer.get_text(start_iter, cursor_iter, False)

        for tag, tag_name in self.in_line_tags:
            if text.endswith(tag):
                start_search_iter = cursor_iter.copy()
                start_search_iter.backward_chars(len(tag))

                start_iter.backward_chars(200)

                if start_search_iter.backward_search(tag, Gtk.TextSearchFlags.TEXT_ONLY):
                    match_start, match_end = start_search_iter.backward_search(tag, Gtk.TextSearchFlags.TEXT_ONLY)
                    if len(buffer.get_text(match_start, cursor_iter, False)) != 2 * len(tag):
                        buffer.apply_tag_by_name(tag_name, match_start, cursor_iter)
                        break

    def on_text_deleted(self, buffer, start, end):
        deleted_text = buffer.get_text(start, end, False)

        for tag, tag_name in self.in_line_tags:
            if deleted_text in tag or tag in deleted_text:
                cursor_iter = start.copy()
                if cursor_iter.backward_search(tag, Gtk.TextSearchFlags.TEXT_ONLY, None):
                    match_start, match_end = cursor_iter.backward_search(tag, Gtk.TextSearchFlags.TEXT_ONLY)

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

                    if line_end.get_line_offset() == len(str(current_order)) + 2:
                        start_iter.set_line_offset(0)
                        buffer.delete(start_iter, loc)
                    else:
                        buffer.insert(loc, new_order_bullet, -1)
