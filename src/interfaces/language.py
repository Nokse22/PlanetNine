# language.py
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

from gi.repository import GObject, GtkSource


# The ILanguage interface is used for any page that has a set language to
#       display the language name in the UI
class ILanguage:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.language_changed = GObject.Signal('language-changed')
        cls.language = GObject.Property(type=str, default="")

    def __init__(self, **kwargs):
        self.language = ""
        self.language_manager = GtkSource.LanguageManager()

    def get_language(self):
        return self.language

    def set_language(self, _language):
        self.language = _language
        lang = self.language_manager.get_language(self.language)
        self.buffer.set_language(lang)
        self.buffer.set_highlight_syntax(True)

        self.emit('language-changed')

    def get_is_language_settable(self):
        return False  # By default the language is not settable
