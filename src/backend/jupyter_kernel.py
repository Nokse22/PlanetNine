# jupyter_kernel.py
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

from pprint import pprint


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

    name = GObject.Property(type=str, default='')
    kernel_id = GObject.Property(type=str, default='')

    def __init__(self, _name, _kernel_id, _language):
        super().__init__()

        self.name = _name
        self.display_name = _name.title() + " " + _kernel_id[:5]
        self.language = _language
        self.kernel_id = _kernel_id
        self.status = ""

        self.thread = None
        self.address = ""
        self.token = ""

        self.kernel_client = jupyter_client.AsyncKernelClient()

        self.data_dir = "/home/lorenzo/.local/share/" # os.environ["XDG_DATA_HOME"]

        self.__connect()

        self.msg_callbacks = {}

        # asyncio.create_task(self.__get_control_msg())
        asyncio.create_task(self.__get_iopub_msg())
        # asyncio.create_task(self.__get_stdin_msg())
        # asyncio.create_task(self.__get_shell_msg())

    def __connect(self):
        connection_file_path = f"{self.data_dir}/jupyter/runtime/kernel-{self.kernel_id}.json"

        print(connection_file_path)

        with open(connection_file_path) as f:
            connection_info = json.load(f)

        self.kernel_client = jupyter_client.AsyncKernelClient()
        self.kernel_client.load_connection_info(connection_info)
        self.kernel_client.start_channels()

        print(f"Kernel Started: \n{self.kernel_client.comm_info()}")

    async def __get_control_msg(self):
        while True:
            try:
                msg = await self.kernel_client.get_control_msg()
                print("CONTROL MSG:")
                pprint(msg)

            except Exception as e:
                print(f"Exception while getting control msg:\n{e}")

    async def __get_iopub_msg(self):
        while True:
            try:
                msg = await self.kernel_client.get_iopub_msg()
                print("IOPUB MSG:")
                pprint(msg)

                msg_type = msg['header']['msg_type']
                msg_id = msg['parent_header']['msg_id']

                print("MSG ID: ", msg_id)

                if msg_type == 'status':
                    self.status = msg['content']['execution_state']

                else:
                    if msg_id in self.msg_callbacks:
                        self.msg_callbacks[msg_id][0](msg, self.msg_callbacks[msg_id][1])

            except Exception as e:
                print(f"Exception while getting iopub msg: {e}")

    async def __get_shell_msg(self):
        while True:
            try:
                msg = await self.kernel_client.get_shell_msg()
                print("SHELL MSG:")
                pprint(msg)

            except Exception as e:
                print(f"Exception while getting shell msg:\n{e}")

    async def __get_stdin_msg(self):
        while True:
            try:
                msg = await self.kernel_client.get_stdin_msg()
                print("STDIN MSG:")
                pprint(msg)

            except Exception as e:
                print(f"Exception while getting stdin msg:\n{e}")

    def execute(self, code, callback, *args):
        asyncio.create_task(self.__execute(code, callback, *args))

    async def __execute(self, code, callback, *args):
        await self.kernel_client.wait_for_ready()

        msg_id = self.kernel_client.execute(code)

        self.msg_callbacks[msg_id] = [callback, *args]
