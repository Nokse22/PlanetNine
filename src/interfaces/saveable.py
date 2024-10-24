# saveable_page.py
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
from gi.repository import GObject
from ..others.save_delegate import GenericSaveDelegate
import os


# The ISaveable interface is used for all pages that have a content that
#       has to be saved before closing
class ISaveable:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.path = GObject.Property(type=str, default="")

    def __init__(self, **kwargs):
        self.save_delegate = GenericSaveDelegate(self)
        self.set_save_delegate(self.save_delegate)

        self.buffer.connect("changed", self.on_text_changed)

    def on_text_changed(self, *args):
        self.set_modified(True)

    def set_path(self, _path):
        self.path = _path
        self.set_title(
            os.path.basename(self.path) if self.path else "Untitled")
        self.save_delegate.set_subtitle(_path)
        if not _path:
            self.save_delegate.set_is_draft(True)
        else:
            self.save_delegate.set_is_draft(False)

    def get_path(self):
        return self.path

    def get_content(self):
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        return self.buffer.get_text(start, end, True)
