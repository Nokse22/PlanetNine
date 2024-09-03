# window.py
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

from gi.repository import Gio
from gi.repository import GObject

import asyncio


class CommandLine(GObject.GObject):
    __gtype_name__ = 'CommandLine'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run_command(self, commands, callback, *args):
        asyncio.create_task(self.__run_command(commands, callback, *args))

    async def __run_command(self, commands, callback, *args):
        process = Gio.Subprocess.new(
            commands,
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_MERGE
        )

        stdout = process.get_stdout_pipe()
        stdout_stream = Gio.DataInputStream.new(stdout)

        while True:
            line, _ = await stdout_stream.read_line_async(0)
            line = line.decode('utf-8')

            if line == '':
                break

            callback(line, *args)
