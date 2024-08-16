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

from .jupyter_kernel import JupyterKernel

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
            kernel = JupyterKernel()
            kernel.name = kernel_name
            kernel.connect_to_kernel(kernel_info['id'])
            callback(True, kernel, *args)
        else:
            callback(False, None, *args)

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
            GLib.idle_add(callback, True, kernel_specs, *args)
        else:
            GLib.idle_add(callback, False, None, *args)

    def get_sessions(self, callback, *args):
        asyncio.create_task(self.__get_sessions(callback, *args))

    async def __get_sessions(self, callback, *args):
        response = requests.get(f'{self.address}/api/sessions', params={"token": self.token})

        if response.status_code == 200:
            sessions = response.json()
            GLib.idle_add(callback, True, sessions, *args)
        else:
            GLib.idle_add(callback, False, None, *args)

    def new_session(self, kernel_name, session_name, callback, *args):
        asyncio.create_task(self.__new_session(kernel_name, session_name, callback, *args))

    async def __new_session(self, kernel_name, session_name, callback, *args):
        response = requests.post(
            f'{self.address}/api/sessions',
            params={"token": self.token},
            json={
                "kernel": {
                    "name": kernel_name
                },
                "name": session_name,
                "path": f"/",
                "type": "notebook"
            }
        )

        if response.status_code == 201:
            session = response.json()
            location_url = response.headers.get('Location', None)
            print("Location URL:", location_url)
            GLib.idle_add(callback, True, session, *args)
        else:
            GLib.idle_add(callback, False, None, *args)

    def get_kernel_info(self, kernel_id, callback, *args):
        asyncio.create_task(self.__get_kernel_info(kernel_id, callback, *args))

    async def __get_kernel_info(self, kernel_id, callback, *args):
        response = requests.get(f'{self.address}/api/kernels/{kernel_id}', params={"token": self.token})

        if response.status_code == 200:
            sessions = response.json()
            GLib.idle_add(callback, True, sessions, *args)
        else:
            GLib.idle_add(callback, False, None, *args)
