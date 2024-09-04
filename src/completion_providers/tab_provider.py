# tab_provider.py
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

from gi.repository import GObject, GtkSource, Gio
import asyncio


class Proposal(GObject.GObject, GtkSource.CompletionProposal):

    string = ""

    def __init__(self, _string):
        super().__init__()

        self.string = _string


class TabCompletionProvider(GObject.Object, GtkSource.CompletionProvider):
    __g_name__ = "TabCompletionProvider"

    notebook = None

    def __init__(self, _notebook):
        super().__init__()
        self.notebook = _notebook

    def do_get_name(self):
        return "Jupyter Tab Completion"

    def do_get_priority(self, *args):
        return 200

    def do_match(self, context):
        return True

    def do_populate_async(self, context, cancellable, callback, user_data):
        pass

    def do_activate_proposal(self, context, proposal):
        return True

    def do_display(self, context, proposal, cell):
        if cell.get_column() == GtkSource.CompletionColumn.TYPED_TEXT:
            cell.set_text(proposal.string)

    def register(self, buffer):
        pass

    def unregister(self, buffer):
        pass
