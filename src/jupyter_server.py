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

import subprocess
import re
import threading
import time
import json
import os

import requests
import jupyter_client

from pprint import pprint

class JupyterServer(GObject.GObject):
    __gtype_name__ = 'JupyterServer'

    __gsignals__ = {
        'started': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'new-line': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.thread = None
        self.address = ""
        self.token = ""

        self.client = jupyter_client.BlockingKernelClient()

        self.data_dir = os.environ["XDG_DATA_HOME"]

    def start(self):
        self.thread = threading.Thread(target=self.jupyter_server, daemon=True)
        self.thread.start()

    def jupyter_server(self):
        process = Gio.Subprocess.new(
            ['jupyter-server', '--debug'],
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_MERGE
        )

        stdout = process.get_stdout_pipe()
        stdout_stream = Gio.DataInputStream.new(stdout)

        while True:
            line, _ = stdout_stream.read_line_utf8(None)
            if line is None:
                continue

            self.emit("new-line", line)

            if self.address == "":
                match = re.search(r'(http[s]?://\S+?)(\?token=([\w-]+))', line)
                if match:
                    self.address = match.group(1)
                    self.token = match.group(3)
                    self.emit("started")
                    print(line)

    def start_default_kernel(self):
        response = requests.post(
            f'{self.address}/api/kernels',
            params={"token": self.token},
            json={"name": "python3"}
        )

        if response.status_code == 201:
            kernel_info = response.json()
            print("Kernel started successfully:")
        else:
            print(f"Failed to start kernel: {response.status_code}")

        connection_file_path = f"{self.data_dir}/jupyter/runtime/kernel-{kernel_info['id']}.json"

        with open(connection_file_path) as f:
            connection_info = json.load(f)

        self.client.load_connection_info(connection_info)
        self.client.start_channels()

        self.client.wait_for_ready()

    def get_kernel_specs(self):
        response = requests.get(f'{self.address}/api/kernelspecs', params={"token": self.token})

        if response.status_code == 200:
            kernel_specs = response.json()
            pprint(kernel_specs)
            return kernel_specs
        else:
            print(f"Failed: {response.status_code}")
            return None

    def get_kernel_info(self, kernel_id):
        response = requests.get(f'{self.address}/api/kernels/{kernel_id}', params={"token": self.token})

        if response.status_code == 200:
            kernel_info = response.json()
            return kernel_info
        else:
            print(f"Failed to start kernel: {response.status_code}")
            print(response.text)

    def restart_kernel(self, kernel_id):
        print(f"restart kernel {kernel_id}")

    def run_code(self, code, block, **kwargs):
        callback = None
        finish_callback = None

        if "callback" in kwargs:
            callback = kwargs["callback"]
        if "finish_callback" in kwargs:
            finish_callback = kwargs["finish_callback"]

        self.client.wait_for_ready()

        msg_id = self.client.execute(code)

        th = threading.Thread(target=self.update_output, args=[callback, finish_callback, block], daemon=True)
        th.start()

    def update_output(self, callback, finish_callback, block):
        while True:
            msg = self.client.get_iopub_msg()
            msg_type = msg['header']['msg_type']
            stream_content = msg['content']

            if msg_type == 'status':
                status = msg['content']['execution_state']
                if status == "idle":
                    GLib.idle_add(finish_callback, block)
                    return

            GLib.idle_add(callback, msg_type, stream_content, block)
