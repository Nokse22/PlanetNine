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

from gi.repository import GLib
from gi.repository import Gio
from gi.repository import GObject
from gi.events import GLibEventLoopPolicy

import subprocess
import re
import threading
import time
import json
import os

import asyncio

import requests
import jupyter_client

from pprint import pprint

class JupyterKernel(GObject.GObject):
    __gtype_name__ = 'JupyterKernel'

    sandboxed = GObject.Property(type=bool, default=True)

    name = GObject.Property(type=str, default='')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.thread = None
        self.address = ""
        self.token = ""

        self.sandboxed = True

        self.kernel_client = jupyter_client.AsyncKernelClient()

        self.data_dir = os.environ["XDG_DATA_HOME"]

    def connect_to_kernel(self, kernel_id):
        connection_file_path = f"{self.data_dir}/jupyter/runtime/kernel-{kernel_id}.json"

        with open(connection_file_path) as f:
            connection_info = json.load(f)

        self.kernel_client = jupyter_client.AsyncKernelClient()
        self.kernel_client.load_connection_info(connection_info)
        self.kernel_client.start_channels()

    def restart_kernel(self, kernel_id, callback, *args):
        asyncio.create_task(self.__restart_kernel(kernel_id, callback, *args))

    async def __restart_kernel(self, kernel_id, callback, *args):
        callback(False, kernel_id, *args)

    def shutdown_kernel(self, kernel_id, callback, *args):
        asyncio.create_task(self.__shutdown_kernel(kernel_id, callback, *args))

    async def __shutdown_kernel(self, kernel_id, callback, *args):
        callback(False, kernel_id, *args)

    def run_code(self, code, callback, *args):
        asyncio.create_task(self.__run_code(code, callback, *args))

    async def __run_code(self, code, callback, *args):

        await self.kernel_client.wait_for_ready()

        msg_id = self.kernel_client.execute(code)

        while True:
            msg = await self.kernel_client.get_iopub_msg()

            if msg['header']['msg_type'] == 'status':
                status = msg['content']['execution_state']
                if status == "idle":
                    callback(msg, *args)
                    return

            callback(msg, *args)
