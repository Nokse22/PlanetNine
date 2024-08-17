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

from .jupyter_kernel import JupyterKernel, JupyterKernelInfo

class Session(GObject.GObject):
    __gtype_name__ = 'Session'

    name = ""
    kernel = None
    notebook_store = None

    def __init__(self, _name=""):
        super().__init__()

        self.name = _name
        self.notebook_store = Gio.ListStore.new(Notebook)

class JupyterServer(GObject.GObject):
    __gtype_name__ = 'JupyterServer'

    __gsignals__ = {
        'started': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'new-line': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    sandboxed = GObject.Property(type=bool, default=True)

    avalaible_kernels = Gio.ListStore()
    kernels = Gio.ListStore()
    default_kernel_name = GObject.Property(type=str, default="")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.thread = None
        self.address = ""
        self.token = ""

        self.sandboxed = True

        self.sessions = Gio.ListStore.new(Session)
        self.kernels = Gio.ListStore.new(JupyterKernel)
        self.avalaible_kernels = Gio.ListStore.new(JupyterKernelInfo)
        self.default_kernel_name = ""

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
        try:
            response = await asyncio.to_thread(
                requests.post,
                f'{self.address}/api/kernels',
                params={"token": self.token},
                json={"name": kernel_name if kernel_name != "" else self.default_kernel_name}
            )
        except:
            callback(False, None, *args)
            return

        if response.status_code == 201:
            kernel_info = response.json()
            kernel = JupyterKernel(kernel_info['name'], kernel_info['id'])
            self.kernels.append(kernel)
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
        try:
            response = await asyncio.to_thread(
                requests.get,
                f'{self.address}/api/kernelspecs',
                params={"token": self.token}
            )
        except:
            callback(False, None, *args)
            return

        if response.status_code == 200:
            kernel_specs = response.json()
            pprint(kernel_specs)
            self.default_kernel_name = kernel_specs['default']
            for name, kernel_spec in kernel_specs['kernelspecs'].items():
                kernel_info = JupyterKernelInfo.new_from_specs(kernel_spec)
                print(kernel_info)
                self.avalaible_kernels.append(kernel_info)
            callback(True, kernel_specs, *args)
        else:
            callback(False, None, *args)

    def get_sessions(self, callback, *args):
        asyncio.create_task(self.__get_sessions(callback, *args))

    async def __get_sessions(self, callback, *args):
        try:
            response = await asyncio.to_thread(
                requests.get,
                f'{self.address}/api/sessions',
                params={"token": self.token}
            )
        except:
            callback(False, None, *args)
            return

        if response.status_code == 200:
            sessions = response.json()
            callback(True, sessions, *args)
        else:
            callback(False, None, *args)

    def new_session(self, kernel_name, session_name, callback, *args):
        asyncio.create_task(
            self.__new_session(kernel_name, session_name, callback, *args)
        )

    async def __new_session(self, kernel_name, session_name, notebook_path, callback, *args):
        response = await asyncio.to_thread(
            requests.post,
            f'{self.address}/api/sessions',
            params={"token": self.token},
            json={
                "kernel": {
                    "name": kernel_name
                },
                "name": session_name,
                "path": notebook_path,
                "type": "notebook"
            }
        )

        if response.status_code == 201:
            session = response.json()
            location_url = response.headers.get('Location', None)
            callback(True, session, *args)
        else:
            callback(False, None, *args)

    def get_kernel_info(self, kernel_id, callback, *args):
        asyncio.create_task(
            self.__get_kernel_info(kernel_id, callback, *args)
        )

    async def __get_kernel_info(self, kernel_id, callback, *args):
        response = await asyncio.to_thread(
            requests.get,
            f'{self.address}/api/kernels/{kernel_id}',
            params={"token": self.token}
        )

        if response.status_code == 200:
            sessions = response.json()
            callback(True, sessions, *args)
        else:
            callback(False, None, *args)

    def shutdown_kernel(self, kernel_id, callback, *args):
        asyncio.create_task(
            self.__shutdown_kernel(kernel_id, callback, *args)
        )

    async def __shutdown_kernel(self, kernel_id, callback, *args):
        response = await asyncio.to_thread(
            requests.delete,
            f'{self.address}/api/kernels/{kernel_id}',
            params={"token": self.token}
        )

        if response.status_code == 200:
            for index, kernel in enumerate(self.kernels):
                if kernel.kernel_id == kernel_id:
                    self.kernels.remove(index)
            callback(True, *args)
        else:
            callback(False, *args)

    def restart_kernel(self, kernel_id, callback, *args):
        asyncio.create_task(
            self.__restart_kernel(kernel_id, callback, *args)
        )

    async def __restart_kernel(self, kernel_id, callback, *args):
        response = await asyncio.to_thread(
            requests.post,
            f'{self.address}/api/kernels/{kernel_id}/restart',
            params={"token": self.token}
        )

        if response.status_code == 200:
            callback(True, *args)
        else:
            callback(False, *args)

    def interrupt_kernel(self, kernel_id, callback, *args):
        asyncio.create_task(
            self.__interrupt_kernel(kernel_id, callback, *args)
        )

    async def __interrupt_kernel(self, kernel_id, callback, *args):
        response = await asyncio.to_thread(
            requests.post,
            f'{self.address}/api/kernels/{kernel_id}/interrupt',
            params={"token": self.token}
        )

        if response.status_code == 200:
            callback(True, *args)
        else:
            callback(False, *args)
