# cells.py
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


# The ICells interface is used in NotebookPage and CodePage that
#       can be divided into cells and single cells can be executed
class ICells:
    def run_selected_cell(self):
        raise NotImplementedError

    def run_all_cells(self):
        raise NotImplementedError

    def run_selected_and_advance(self):
        raise NotImplementedError

    def add_cell(self, cell_type):
        raise NotImplementedError
