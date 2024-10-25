# text_page.py
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

from gi.repository import Gtk, GObject, Gio
from gi.repository import Panel, GtkSource
from gi.repository import Spelling

from ..utils.converters import get_language_highlight_name

from ..interfaces.saveable import ISaveable
from ..interfaces.disconnectable import IDisconnectable
from ..interfaces.cursor import ICursor
from ..interfaces.language import ILanguage
from ..interfaces.style_update import IStyleUpdate

import asyncio

GObject.type_register(GtkSource.Map)
GObject.type_register(GtkSource.VimIMContext)


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/text_page.ui')
class TextPage(
        Panel.Widget, ISaveable, IDisconnectable, ICursor, ILanguage,
        IStyleUpdate):
    __gtype_name__ = 'TextPage'

    path = GObject.Property(type=str, default="")

    source_view = Gtk.Template.Child()
    buffer = Gtk.Template.Child()

    def __init__(self, file_path="", **kwargs):
        super().__init__(**kwargs)
        ICursor.__init__(self, **kwargs)
        ILanguage.__init__(self, **kwargs)
        ISaveable.__init__(self, **kwargs)
        IStyleUpdate.__init__(self, **kwargs)

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

        # ENABLE SPELL CHECK

        checker = Spelling.Checker.get_default()
        adapter = Spelling.TextBufferAdapter.new(self.buffer, checker)
        extra_menu = adapter.get_menu_model()

        self.source_view.set_extra_menu(extra_menu)
        self.source_view.insert_action_group('spelling', adapter)

        adapter.set_enabled(True)

        # LOAD File

        asyncio.create_task(self._load_file(file_path))

    async def _load_file(self, file_path):
        print("Loading: ", file_path)
        try:
            file = Gio.File.new_for_path(file_path)

            success, contents, _ = await file.load_contents_async(None)

            if success:
                text = contents.decode('utf-8')
                self.buffer.set_text(text)

                language = self.language_manager.guess_language(
                    file_path, None)
                if language:
                    self.set_language(language.get_id())

        except Exception as e:
            print(e)

        self.set_path(file_path)

    #
    #   Implement Disconnectable Interface
    #

    def disconnect(self, *_args):
        self.style_manager.disconnect_by_func(self.update_style_scheme)
        self.buffer.disconnect_by_func(self.on_text_changed)
        self.buffer.disconnect_by_func(self.on_cursor_position_changed)

        self.save_delegate.disconnect_all()

        print(f"Disconnected:  {self}")

    def __del__(self, *_args):
        print(f"DELETING {self}")
