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

from gi.repository import Gio, Xdp
from gi.repository import GObject

import re
import os
import asyncio
import requests

from pprint import pprint

from .jupyter_kernel import JupyterKernel, JupyterKernelInfo
from ..models.notebook import Notebook


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

    avalaible_kernels = Gio.ListStore()
    kernels = Gio.ListStore()
    default_kernel_name = GObject.Property(type=str, default="")

    data_dir = os.environ["XDG_DATA_HOME"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')
        self.portal = Xdp.Portal()

        self.jupyter_process = None

        self.thread = None
        self.address = ""
        self.token = ""

        self.is_running = False
        self.sandboxed = None
        self.use_external = None
        self.flatpak_spawn = None
        self.conn_file_dir = None

        self.sessions = Gio.ListStore.new(Session)
        self.kernels = Gio.ListStore.new(JupyterKernel)
        self.avalaible_kernels = Gio.ListStore.new(JupyterKernelInfo)
        self.default_kernel_name = ""

        self.address_pattern = r'(http[s]?://\S+?)\?token=([\w-]+)'

    def start(self):
        self.sandboxed = self.portal.running_under_sandbox()
        self.use_external = self.settings.get_boolean("use-external-server") or not self.sandboxed
        self.flatpak_spawn = self.sandboxed and self.use_external

        if self.use_external:
            self.conn_file_dir = self.settings.get_string("jupyter-path")
        else:
            self.conn_file_dir = f"{self.data_dir}/jupyter/runtime/"

        asyncio.create_task(self._start())

    async def _start(self):
        list_servers_process = Gio.Subprocess.new(
            ['jupyter-server', 'list'] if not self.flatpak_spawn else ['flatpak-spawn', '--host', 'jupyter-server', 'list'],
            Gio.SubprocessFlags.STDOUT_PIPE
        )

        succ, output_buf, err_buff = await list_servers_process.communicate_async()

        if succ:
            output_str = output_buf.get_data().decode('utf-8')
            if self._get_address(output_str):
                return

        self.jupyter_process = Gio.Subprocess.new(
            ['jupyter-server'] if not self.flatpak_spawn else ['flatpak-spawn', '--host', 'jupyter-server'],
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_MERGE
        )

        # if not self.jupyter_process.get_successful():
        #     return

        stdout = self.jupyter_process.get_stdout_pipe()
        stdout_stream = Gio.DataInputStream.new(stdout)

        while True:
            line, _ = await stdout_stream.read_line_async(0)

            if line is None or line == b'':
                return

            line = line.decode('utf-8')

            self.emit("new-line", line)

            if self.address == "":
                self._get_address(line)


    def _get_address(self, string):
        addresses = re.findall(self.address_pattern, string)

        print("ADRESSES: ", addresses)

        if addresses != []:
            self.address = addresses[0][0]
            self.token = addresses[0][1]
            self.emit("started")
            self.is_running = True

            asyncio.create_task(self.on_kernel_stated())
            return True
        return False

    def stop(self):
        if self.jupyter_process:
            self.jupyter_process.send_signal(15)
            print("STOPPING")

            self.is_running = False

    def get_is_running(self):
        return self.is_running

    async def on_kernel_stated(self):
        while True:
            success, kernel_specs = await self.get_kernel_specs()
            if success:
                break

    async def start_kernel_by_name(self, kernel_name):
        if self.address == "":
            return False, None
        try:
            response = await asyncio.to_thread(
                requests.post,
                f'{self.address}/api/kernels',
                params={"token": self.token},
                json={"name": kernel_name if kernel_name != "" else self.default_kernel_name}
            )
        except Exception as e:
            print(e)
            return False, None

        if response.status_code == 201:
            kernel_info = response.json()

            kernel_language = ""
            for av_kernel_info in self.avalaible_kernels:
                if kernel_name == av_kernel_info.name:
                    kernel_language = av_kernel_info.language
                    break

            kernel = JupyterKernel(
                kernel_info['name'],
                kernel_info['id'],
                kernel_language,
                self.conn_file_dir
            )

            self.kernels.append(kernel)

            return True, kernel
        else:
            return False, None

    async def get_kernel_specs(self):
        if self.address == "":
            return False, None
        try:
            response = await asyncio.to_thread(
                requests.get,
                f'{self.address}/api/kernelspecs',
                params={"token": self.token}
            )
        except Exception as e:
            print(e)
            return False, None

        if response.status_code == 200:
            kernel_specs = response.json()
            pprint(kernel_specs)
            self.default_kernel_name = kernel_specs['default']
            for name, kernel_spec in kernel_specs['kernelspecs'].items():
                kernel_info = JupyterKernelInfo.new_from_specs(kernel_spec)
                self.avalaible_kernels.append(kernel_info)
            return True, kernel_specs
        else:
            return False, None

    async def get_sessions(self):
        if self.address == "":
            return False, None
        try:
            response = await asyncio.to_thread(
                requests.get,
                f'{self.address}/api/sessions',
                params={"token": self.token}
            )
        except Exception as e:
            print(e)
            return False, None

        if response.status_code == 200:
            sessions = response.json()
            print("SESSIONS: ", sessions)
            for session in sessions:
                kernel = JupyterKernel(
                    session['kernel']['name'],
                    session['kernel']['id'],
                    "python",
                    self.conn_file_dir
                )
                self.kernels.append(kernel)
            return True, sessions
        else:
            return False, None

    async def new_session(self, kernel_name, session_name, notebook_path):
        if self.address == "":
            return False, None
        try:
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
        except Exception as e:
            print(e)
            return False, None

        if response.status_code == 201:
            session = response.json()
            return True, session
        else:
            return False, None

    async def get_kernel_info(self, kernel_id):
        if self.address == "":
            return False, None
        try:
            response = await asyncio.to_thread(
                requests.get,
                f'{self.address}/api/kernels/{kernel_id}',
                params={"token": self.token}
            )
        except Exception as e:
            print(e)
            return False, None

        if response.status_code == 200:
            sessions = response.json()
            return True, sessions
        else:
            return False, None

    async def shutdown_kernel(self, kernel_id):
        if self.address == "":
            return False
        try:
            response = await asyncio.to_thread(
                requests.delete,
                f'{self.address}/api/kernels/{kernel_id}',
                params={"token": self.token}
            )
        except Exception as e:
            print(e)
            return False

        if response.status_code == 204:
            for index, kernel in enumerate(self.kernels):
                if kernel.kernel_id == kernel_id:
                    self.kernels.remove(index)
                    break
            return True
        else:
            return False

    async def restart_kernel(self, kernel_id):
        if self.address == "":
            return False
        try:
            response = await asyncio.to_thread(
                requests.post,
                f'{self.address}/api/kernels/{kernel_id}/restart',
                params={"token": self.token}
            )
        except Exception as e:
            print(e)
            return False

        if response.status_code == 200:
            success, kernel = self.get_kernel_by_id(kernel_id)
            if success:
                kernel.reset()
                return True
            else:
                return False
        else:
            return False

    async def interrupt_kernel(self, kernel_id):
        if self.address == "":
            return False
        try:
            response = await asyncio.to_thread(
                requests.post,
                f'{self.address}/api/kernels/{kernel_id}/interrupt',
                params={"token": self.token}
            )
        except Exception as e:
            print(e)
            return False

        if response.status_code == 200:
            return True
        else:
            return False

    def get_kernel_by_id(self, kernel_id):
        for kernel in self.kernels:
            if kernel.kernel_id == kernel_id:
                return True, kernel

        return False, None
