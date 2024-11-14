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
from gi.repository import GObject, Gio, Panel
from ..others.save_delegate import GenericSaveDelegate
from .language import ILanguage
from gettext import gettext as _
import os


# The ISaveable interface is used for all pages that have a content that
#       has to be saved before closing
class ISaveable:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.path = GObject.Property(type=str, default="")

    def __init__(self, override=False):
        if not override:
            self.save_delegate = GenericSaveDelegate(self)
            self.set_save_delegate(self.save_delegate)

            self.buffer.connect("changed", self.on_text_changed)

        if isinstance(self, Panel.Widget):
            menu = Gio.Menu()

            menu_item = Gio.MenuItem.new(_("Save"), "app.save")
            menu.append_item(menu_item)

            menu_item = Gio.MenuItem.new(_("Save As"), "app.save-as")
            menu.append_item(menu_item)

            menu_item = Gio.MenuItem.new(_("Reopen As"), "win.reopen-as")
            menu.append_item(menu_item)

            self.get_menu_model().append_section(None, menu)

    async def load_file(self, file_path):
        """Handles loading the file in the buffer"""

        try:
            file = Gio.File.new_for_path(file_path)

            success, contents, _ = await file.load_contents_async(None)

            if success:
                self.buffer.set_text(contents.decode('utf-8'))
                self.set_modified(False)
            else:
                return

        except Exception as e:
            print(e)
            return

        self.set_path(file_path)

        if isinstance(self, ILanguage):
            language = self.language_manager.guess_language(
                file_path, None)
            if language:
                self.set_language(language.get_id())

    def on_text_changed(self, *_args):
        """Used to set the page to modified when the buffer changes"""

        self.set_modified(True)

    def set_path(self, _path):
        """Sets the page file path

        :param str path: the page file path
        """

        self.path = _path
        self.set_title(os.path.basename(self.path)
                       if self.path else "Untitled")
        self.save_delegate.set_subtitle(_path)
        if not _path:
            self.save_delegate.set_is_draft(True)
        else:
            self.save_delegate.set_is_draft(False)

    def get_path(self):
        """Get the page path

        :returns: the page path
        :rtype: str
        """

        return self.path

    def get_content(self):
        """Get the page content

        :returns: the page content
        :rtype: str
        """

        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        return self.buffer.get_text(start, end, True)
