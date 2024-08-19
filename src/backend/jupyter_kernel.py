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

from gi.repository import GObject

import json
import os
import asyncio
import jupyter_client


class JupyterKernelInfo(GObject.GObject):
    __gtype_name__ = 'JupyterKernelInfo'

    name = ""
    display_name = ""
    language = ""
    interrupt_mode = ""

    def __init__(self, _display_name=""):
        super().__init__()

        self.name = ""
        self.display_name = _display_name
        self.language = ""
        self.interrupt_mode = ""
        self.kernel_id = ""

    @classmethod
    def new_from_specs(cls, specs):
        instance = cls()

        instance.name = specs['name']
        instance.display_name = specs['spec']['display_name']
        instance.language = specs['spec']['language']
        instance.interrupt_mode = specs['spec']['interrupt_mode']

        return instance


class JupyterKernel(GObject.GObject):
    __gtype_name__ = 'JupyterKernel'

    sandboxed = GObject.Property(type=bool, default=True)
    name = GObject.Property(type=str, default='')
    kernel_id = GObject.Property(type=str, default='')

    def __init__(self, name, kernel_id):
        super().__init__()

        self.name = name
        self.kernel_id = kernel_id

        self.thread = None
        self.address = ""
        self.token = ""

        self.sandboxed = True

        self.kernel_client = jupyter_client.AsyncKernelClient()

        self.data_dir = os.environ["XDG_DATA_HOME"]

        self.__connect()

    def __connect(self):
        connection_file_path = f"{self.data_dir}/jupyter/runtime/kernel-{self.kernel_id}.json"

        with open(connection_file_path) as f:
            connection_info = json.load(f)

        self.kernel_client = jupyter_client.AsyncKernelClient()
        self.kernel_client.load_connection_info(connection_info)
        self.kernel_client.start_channels()

    def run_code(self, code, callback, *args):
        asyncio.create_task(self.__run_code(code, callback, *args))

    async def __run_code(self, code, callback, *args):

        await self.kernel_client.wait_for_ready()

        msg_id = self.kernel_client.execute(code)

        while True:
            try:
                msg = await self.kernel_client.get_iopub_msg()
            except:
                callback(msg, *args)
                return

            if msg['header']['msg_type'] == 'status':
                status = msg['content']['execution_state']
                if status == "idle":
                    callback(msg, *args)
                    return

            callback(msg, *args)
