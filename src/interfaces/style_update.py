# cursor.py
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

from ..others.style_manager import StyleManager


class IStyleUpdate:
    def __init__(self, **kwargs):
        self.style_manager = StyleManager()
        self.style_manager.connect("style-changed", self.update_style_scheme)
        self.update_style_scheme()

    def update_style_scheme(self, *args):
        scheme = self.style_manager.get_current_scheme()
        self.buffer.set_style_scheme(scheme)
