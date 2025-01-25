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

from gi.repository import Gio, Xdp, GLib
from gi.repository import GObject

from .jupyter_kernel import JupyterKernel, JupyterKernelInfo
from pprint import pprint

import re
import os
import asyncio
import requests
import uuid


class KernelSession(GObject.GObject):
    __gtype_name__ = 'KernelSession'

    name = ""
    kernel_id = None
    session_type = None
    file_path = ""

    def __init__(self, session_json=""):
        super().__init__()

        self.name = session_json.get("name")
        self.session_id = session_json.get("id")
        self.session_type = session_json.get("type")
        self.file_path = session_json.get("path")

        kernel = session_json.get("kernel")
        self.kernel_id = kernel.get("id")


class JupyterServer(GObject.GObject):
    __gtype_name__ = 'JupyterServer'

    __gsignals__ = {
        'started': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'new-line': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'kernel-info-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    avalaible_kernels = Gio.ListStore.new(JupyterKernelInfo)
    kernels = Gio.ListStore.new(JupyterKernel)

    default_kernel_name = GObject.Property(type=str, default="")

    data_dir = os.environ["XDG_DATA_HOME"]

    settings = Gio.Settings.new('io.github.nokse22.PlanetNine')
    portal = Xdp.Portal()

    jupyter_process = None

    address = GObject.Property(type=str, default="")
    token = GObject.Property(type=str, default="")

    is_running = GObject.Property(type=bool, default=False)
    sandboxed = GObject.Property(type=bool, default=False)
    use_external = GObject.Property(type=bool, default=False)
    flatpak_spawn = GObject.Property(type=bool, default=False)
    conn_file_dir = GObject.Property(type=str, default="")

    address_pattern = r'(http[s]?://\S+?)\?token=([\w-]+)'

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JupyterServer, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.kernels.connect("items-changed", self.on_kernel_status_changed)

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
            ['jupyter-server', 'list']
            if not self.flatpak_spawn else
            ['flatpak-spawn', '--host', 'jupyter-server', 'list'],
            Gio.SubprocessFlags.STDOUT_PIPE
        )

        succ, output_buf, err_buff = await list_servers_process.communicate_async()

        if succ:
            output_str = output_buf.get_data().decode('utf-8')
            if self._get_address(output_str):
                return

        self.jupyter_process = Gio.Subprocess.new(
            ['jupyter-server']
            if not self.flatpak_spawn else
            ['flatpak-spawn', '--host', 'jupyter-server'],
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

            GLib.timeout_add(500, self.update_kernels)

            asyncio.create_task(self.on_server_stated())
            return True
        return False

    def update_kernels(self):
        asyncio.create_task(self._update_kernels())
        return True

    async def _update_kernels(self):
        succ, new_kernels = await self.get_running_kernels()
        if not succ:
            return

        succ, kernel_specs = await self.get_kernel_specs()
        if not succ:
            return

        new_kernel_ids = [k['id'] for k in new_kernels]

        # Remove kernels not in new_kernels
        i = 0
        while i < self.kernels.get_n_items():
            kernel = self.kernels.get_item(i)
            if kernel.kernel_id not in new_kernel_ids:
                self.kernels.remove(i)
                kernel.disconnect_by_func(self.on_kernel_status_changed)
            else:
                i += 1

        # Add new kernels if they don't exist
        for new_kernel in new_kernels:
            kernel_exists = any(
                self.kernels.get_item(i).kernel_id == new_kernel['id']
                for i in range(self.kernels.get_n_items())
            )
            if not kernel_exists:
                for kernel_info in self.avalaible_kernels:
                    if kernel_info.name == new_kernel['name']:
                        kernel = JupyterKernel(
                            kernel_info,
                            new_kernel['id'],
                            self.conn_file_dir
                        )
                if kernel:
                    kernel.connect(
                        "status-changed", self.on_kernel_status_changed)
                    self.kernels.append(kernel)

        succ, sessions = await self.get_sessions()
        if not succ:
            return

        new_session_ids = {s['id']: s for s in sessions}

        # Update kernel connections
        for i in range(self.kernels.get_n_items()):
            kernel = self.kernels.get_item(i)
            relevant_sessions = [
                s for s in sessions if s['kernel']['id'] == kernel.kernel_id]

            # Remove old connections not in new sessions
            j = 0
            while j < kernel.connections.get_n_items():
                session = kernel.connections.get_item(j)
                if session.session_id not in new_session_ids:
                    kernel.connections.remove(j)
                else:
                    j += 1

            # Add new sessions if they don't exist
            for new_session in relevant_sessions:
                session_exists = any(
                    kernel.connections.get_item(k).session_id == new_session['id']
                    for k in range(kernel.connections.get_n_items())
                )
                if not session_exists:
                    kernel.connections.append(KernelSession(new_session))

    def stop(self):
        if self.jupyter_process:
            self.jupyter_process.send_signal(15)
            print("STOPPING")

            self.is_running = False

    def get_is_running(self):
        return self.is_running

    async def on_server_stated(self):
        while True:
            success, kernel_specs = await self.get_kernel_specs()
            if success:
                pprint(kernel_specs)
                self.default_kernel_name = kernel_specs['default']
                for name, kernel_spec in kernel_specs['kernelspecs'].items():
                    kernel_info = JupyterKernelInfo.new_from_specs(kernel_spec)
                    self.avalaible_kernels.append(kernel_info)

                return

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
            kernel.connect("status-changed", self.on_kernel_status_changed)
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
            return True, sessions
        else:
            return False, None

    async def get_running_kernels(self):
        if self.address == "":
            return False, None
        try:
            response = await asyncio.to_thread(
                requests.get,
                f'{self.address}/api/kernels',
                params={"token": self.token}
            )
        except Exception as e:
            print(e)
            return False, None

        if response.status_code == 200:
            new_kernels = response.json()
            return True, new_kernels
        else:
            return False, None

    async def new_session(self, session_name, page_path, **kwargs):
        print("new session", self.address)
        if self.address == "":
            return False, None

        kernel_name = kwargs.get("kernel_name", str(uuid.uuid4()))
        kernel_id = kwargs.get("kernel_id", str(uuid.uuid4()))
        page_id = kwargs.get("page_id", str(uuid.uuid4()))
        page_type = kwargs.get("page_type", "notebook")

        pprint({
            "kernel": {
                "name": kernel_name,
                "id": kernel_id
            },
            "name": session_name,
            "path": page_path,
            "type": page_type,
            "id": page_id
        })

        try:
            response = await asyncio.to_thread(
                requests.post,
                f'{self.address}/api/sessions',
                params={"token": self.token},
                json={
                    "kernel": {
                        "name": kernel_name,
                        "id": kernel_id
                    },
                    "name": session_name,
                    "path": page_path,
                    "type": page_type,
                    "id": page_id
                }
            )
        except Exception as e:
            print(e)
            return False, None

        if response.status_code == 201:
            session = response.json()
            print(session)
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

    def on_kernel_status_changed(self, *_args):
        self.emit("kernel-info-changed")

    async def shutdown_all(self):
        ids = [kernel.kernel_id for kernel in self.kernels]
        result = True
        for kernel_id in ids:
            succ = await self.shutdown_kernel(kernel_id)
            if not succ:
                result = False

        return result

    async def get_path_content(self, path):
        if self.address == "":
            return False, None
        try:
            response = await asyncio.to_thread(
                requests.get,
                f'{self.address}/api/contents/{path}',
                params={"token": self.token}
            )
        except Exception as e:
            print(e)
            return False, None

        if response.status_code == 200:
            return True, response.json()
        else:
            return False, None

    async def set_path_content(self, path, content):
        if self.address == "":
            return False, None
        try:
            response = await asyncio.to_thread(
                requests.get,
                f'{self.address}/api/contents/{path}',
                params={"token": self.token}
            )
        except Exception as e:
            print(e)
            return False, None

        if response.status_code == 200:
            return True, response.json()
        else:
            return False, None
