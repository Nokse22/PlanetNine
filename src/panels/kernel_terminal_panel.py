# kernel_terminal_panel.py
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
from .terminal_panel import TerminalPanel


class KernelTerminalPanel(TerminalPanel):
    __gtype_name__ = 'KernelTerminalPanel'

    def __init__(self):
        super().__init__()

        self.kernel = None

    def set_kernel(self, kernel):
        """Handles setting the kernel"""
        if not kernel:
            self.vte_terminal.reset(True, True)
        elif kernel != self.kernel:
            self.change_kernel(kernel)

    def change_kernel(self, kernel):
        """Handles changing the viewed page so the kernel too"""
        self.vte_terminal.reset(True, True)
        for msg in kernel.get_messages():
            for line in msg.splitlines():
                self.vte_terminal.feed([ord(char) for char in line + "\r\n"])
