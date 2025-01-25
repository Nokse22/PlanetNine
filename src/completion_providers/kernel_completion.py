# kernel_completion.py
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

from gi.repository import GObject, GtkSource, Gio, Gtk
import asyncio


class Proposal(GObject.GObject, GtkSource.CompletionProposal):
    string = ""

    def __init__(self, _string):
        super().__init__()
        self.string = _string


class ProposalFilter(Gtk.Filter):
    def __init__(self):
        super().__init__()
        self.word = ""

    def set_word(self, word):
        self.word = word or ""
        self.emit("changed", Gtk.FilterChange.DIFFERENT)

    def do_match(self, item):
        return item.string.startswith(self.word)


class KernelCompletionProvider(GObject.Object, GtkSource.CompletionProvider):
    __g_name__ = "KernelCompletionProvider"
    page = None

    def __init__(self, _page):
        super().__init__()
        self.page = _page
        self.store = Gio.ListStore.new(GtkSource.CompletionProposal.__gtype__)
        self.filter = ProposalFilter()
        self.filtered_model = Gtk.FilterListModel.new(self.store, self.filter)

    def do_get_name(self):
        """Returns the name of the completion provider"""

        return "Jupyter Completion Provider"

    def do_get_priority(self, *_args):
        """Returns the priority of the completion provider"""

        return 200

    def do_match(self, context):
        return True

    def do_populate_async(self, context, cancellable, callback, user_data):
        """Starts to fetch the possible completions"""

        word = context.get_word()
        asyncio.create_task(self._do_completion(word, context))

    async def _do_completion(self, word, context):
        """Fetches possible completions and makes a new model"""

        if self.page.get_kernel() is None:
            return

        reply = await self.page.get_kernel().complete(word, len(word))

        self.store.remove_all()

        for match in reply.get('matches', []):
            proposal = Proposal(match)
            self.store.append(proposal)

        self.filter.set_word(word)

        context.set_proposals_for_provider(self, self.filtered_model)

    def do_refilter(self, context, model):
        """Filters the model"""

        word = context.get_word()
        self.filter.set_word(word)

    def do_activate(self, context, proposal):
        """Used to replace what's written with the selected completion"""

        succ, begin, end = context.get_bounds()
        if not succ:
            return
        if not begin or not end:
            return False

        buffer = begin.get_buffer()
        word = proposal.string

        if not end.ends_line() and not end.ends_word():
            word_end = end.copy()
            if word_end.forward_word_end():
                text = buffer.get_text(end, word_end, False)
                if word.endswith(text):
                    word = word[:-len(text)]

        buffer.begin_user_action()
        buffer.delete(begin, end)
        buffer.insert(begin, word)
        buffer.end_user_action()

        return True

    def do_display(self, context, proposal, cell):
        """Used to display the suggested completions"""

        if cell.get_column() == GtkSource.CompletionColumn.TYPED_TEXT:
            cell.set_text(proposal.string)

    def register(self, buffer):
        """Used to register a new buffer, empty because all suggestions are
        provided by the kernel"""

        pass

    def unregister(self, buffer):
        """Used to unregister a new buffer, empty because all suggestions are
        provided by the kernel"""

        pass
