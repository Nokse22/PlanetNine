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

class JupyterServer(GObject.GObject):
    __gtype_name__ = 'JupyterServer'

    __gsignals__ = {
        'started': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'new-line': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    sandboxed = GObject.Property(type=bool, default=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.thread = None
        self.address = ""
        self.token = ""

        self.sandboxed = True

        self.client = jupyter_client.AsyncKernelClient()

        self.data_dir = os.environ["XDG_DATA_HOME"]

    def start(self):
        asyncio.create_task(self.__start())

    async def __start(self):
        process = Gio.Subprocess.new(
            ['jupyter-server', '--debug'] if self.sandboxed  else ['flatpak-spawn', '--host', 'jupyter-server', '--debug'],
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_MERGE
        )

        stdout = process.get_stdout_pipe()
        stdout_stream = Gio.DataInputStream.new(stdout)

        while True:
            line, _ = await stdout_stream.read_line_async(0)

            if line is None:
                continue

            line = line.decode('utf-8')

            self.emit("new-line", line)

            if self.address == "":
                match = re.search(r'(http[s]?://\S+?)(\?token=([\w-]+))', line)
                if match:
                    print(line)
                    self.address = match.group(1)
                    self.token = match.group(3)
                    self.emit("started")

    def start_kernel_by_name(self, kernel_name, callback, *args):
        asyncio.create_task(self.__start_kernel_by_name(kernel_name, callback, *args))

    async def __start_kernel_by_name(self, kernel_name, callback, *args):
        response = requests.post(
            f'{self.address}/api/kernels',
            params={"token": self.token},
            json={"name": kernel_name}
        )

        if response.status_code == 201:
            kernel_info = response.json()
            callback(True, kernel_info, *args)
        else:
            callback(False, None, *args)

        connection_file_path = f"{self.data_dir}/jupyter/runtime/kernel-{kernel_info['id']}.json"

        with open(connection_file_path) as f:
            connection_info = json.load(f)

        self.client.load_connection_info(connection_info)
        self.client.start_channels()

    def get_kernel_specs(self, callback, *args):
        """
        Returns data about the default kernel and avalaible kernels.

        callback(successful, kernel_specs, args)
        """
        asyncio.create_task(self.__get_kernel_specs(callback, *args))

    async def __get_kernel_specs(self, callback, *args):
        response = requests.get(f'{self.address}/api/kernelspecs', params={"token": self.token})

        if response.status_code == 200:
            kernel_specs = response.json()
            callback(True, kernel_specs, *args)
        else:
            callback(False, None, *args)

    def get_kernel_info(self, kernel_id, callback, *args):
        asyncio.create_task(self.__get_kernel_specs(kernel_id, callback, *args))

    async def __get_kernel_info(self, kernel_id, callback, *args):
        response = requests.get(f'{self.address}/api/kernels/{kernel_id}', params={"token": self.token})

        if response.status_code == 200:
            kernel_info = response.json()
            callback(False, kernel_info, *args)
        else:
            callback(True, None, *args)

    def restart_kernel(self, kernel_id, callback, *args):
        asyncio.create_task(self.__restart_kernel(kernel_id, callback, *args))

    async def __restart_kernel(self, kernel_id, callback, *args):
        callback(kernel_id, *args)

    def shutdown_kernel(self, kernel_id, callback, *args):
        asyncio.create_task(self.__shutdown_kernel(kernel_id, callback, *args))

    async def __shutdown_kernel(self, kernel_id, callback, *args):
        callback(kernel_id, *args)

    def run_code(self, code, callback, **kwargs):
        asyncio.create_task(self.__run_code(code, callback, **kwargs))

    async def __run_code(self, code, callback, **kwargs):
        finish_callback = None
        args = []

        if "args" in kwargs:
            args = kwargs["args"]
        if "finish_callback" in kwargs:
            finish_callback = kwargs["finish_callback"]

        await self.client.wait_for_ready()

        msg_id = self.client.execute(code)

        while True:
            msg = await self.client.get_iopub_msg()

            msg_type = msg['header']['msg_type']
            stream_content = msg['content']

            if msg_type == 'status':
                status = msg['content']['execution_state']
                if status == "idle":
                    finish_callback(*args)
                    return

            callback(msg_type, stream_content, *args)
