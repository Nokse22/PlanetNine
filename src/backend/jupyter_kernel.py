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

from gi.repository import GObject, GLib, Gio

import json
import asyncio
import jupyter_client
import traceback
import re

from pprint import pprint


class Variable(GObject.GObject):
    __gtype_name__ = 'Variable'

    name = GObject.Property(type=str)
    type = GObject.Property(type=str)
    value = GObject.Property(type=str)

    def __init__(self, _name, _type, _value):
        super().__init__()

        self.name = _name
        self.type = _type
        self.value = _value


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

    __gsignals__ = {
        'status-changed': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    name = GObject.Property(type=str, default='')
    kernel_id = GObject.Property(type=str, default='')
    connections = GObject.Property(type=Gio.ListStore)

    def __init__(self, _kernel_info, _kernel_id, _search_path):
        super().__init__()

        self.name = _kernel_info.name
        self.display_name = _kernel_info.display_name
        self.language = _kernel_info.language

        self.connections = Gio.ListStore()

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

        self.kernel_id = _kernel_id
        self.status = ""

        self.shell_futures = {}

        self._running = False

        self._variables = Gio.ListStore()

        self.messages = []

        self.kernel_client = jupyter_client.AsyncKernelClient()

        self.conn_file_dir = _search_path

        self._connect()

        self.executing = False

        self.execution_queue = {}

        self.exec_msg_id = ""
        self.exec_msg_callback = None
        self.exec_msg_arguments = None

        self.comp_msg_id = ""
        self.comp_msg_callback = None
        self.comp_msg_arguments = None

        asyncio.create_task(self._get_control_msg())
        asyncio.create_task(self._get_iopub_msg())
        # asyncio.create_task(self._get_stdin_msg())
        asyncio.create_task(self._get_shell_msg())

    def _connect(self):
        try:
            connection_file_path = jupyter_client.connect.find_connection_file(
                filename=f'kernel-{self.kernel_id}.json',
                path=self.conn_file_dir)
        except Exception as error:
            print(error)
            return

        with open(connection_file_path) as f:
            connection_info = json.load(f)

        self.kernel_client = jupyter_client.AsyncKernelClient()
        self.kernel_client.load_connection_info(connection_info)
        self.kernel_client.start_channels()

        self._running = True

        print(f"Kernel Started: \n{self.kernel_client.comm_info()}")

    async def _get_control_msg(self):
        while self._running:
            try:
                msg = await self.kernel_client.get_control_msg()
                print("CONTROL MSG:")
                pprint(msg)

            except Exception as e:
                print(f"Exception while getting control msg:\n{e}")

    async def _get_iopub_msg(self):
        while self._running:
            try:
                msg = await self.kernel_client.get_iopub_msg()
                print("IOPUB MSG:")
                pprint(msg)
                self.process_iopub_msg(msg)

            except Exception as e:
                print(f"Exception while getting iopub msg: {e}")
                traceback.print_exc()

    def process_iopub_msg(self, msg):
        if not msg:
            return

        msg = self.extract_variables(msg)

        msg_type = msg['header']['msg_type']
        msg_content = msg['content']
        if 'msg_id' in msg['parent_header']:
            msg_id = msg['parent_header']['msg_id']
        else:
            msg_id = ''

        if msg_type == 'stream':
            self.messages.append(msg_content['text'])
        elif msg_type == 'execute_input':
            start = f"In [{msg_content['execution_count']}]"
            self.messages.append(
                f"\033[32;1m{start}\033[0m Code Executed")
        elif msg_type == 'error':
            self.messages.append("\n".join(msg_content['traceback']))
        elif msg_type == 'status':
            self.status = msg['content']['execution_state']
            self.emit("status-changed", self.status)

        if msg_id in self.execution_queue:
            print("Matching ID\n")
            callback, *args = self.execution_queue[msg_id]
            callback(msg, *args)

    #
    #
    #

    async def _get_shell_msg(self):
        while self._running:
            try:
                msg = await self.kernel_client.get_shell_msg()
                parent_id = msg['parent_header'].get('msg_id')
                if parent_id in self.shell_futures:
                    future = self.shell_futures[parent_id]
                    if not future.done():
                        future.set_result(msg)
            except Exception as e:
                print(f"Error in shell handler: {e}")
                await asyncio.sleep(0.1)

    async def _get_stdin_msg(self):
        while self._running:
            try:
                msg = await self.kernel_client.get_stdin_msg()
                print("STDIN MSG:")
                pprint(msg)

            except Exception as e:
                print(f"Exception while getting stdin msg:\n{e}")

    def execute(self, code, callback, *args):
        print("EXECUTE: ", self.executing, len(self.execution_queue), code)

        asyncio.create_task(self._execute(code, callback, *args))

    async def _execute(self, code, callback, *args):
        if self.language == "python":
            code += '\n%whos'  # added %whos to get the variables
            # FIXME if it's not ipykernel it should not be used

        msg_id = self.kernel_client.execute(code)

        self.execution_queue[msg_id] = (callback, *args)

    def extract_variables(self, msg):
        if msg['header']['msg_type'] != 'stream':
            return msg

        empty_pattern = re.compile(r'Interactive namespace is empty.')

        msg['content']['text'] = empty_pattern.sub('', msg['content']['text'])

        whos_pattern = re.compile(
            r'Variable\s+Type\s+Data\/Info\n[-]+\n((?:\S+ +\S+ +[^\n]+\n?)+)\Z')
        whos_match = whos_pattern.search(msg['content']['text'])
        if whos_match:
            variable_pattern = re.compile(r'(\S+ +\S+ +[^\n]+)\n')
            variables_match = variable_pattern.findall(whos_match.group(1))
            self.reset_variables()
            for variable in variables_match:
                variable_info_patt = re.compile(
                    r'(\S+)\s+(\S+)\s+([^\n]+)$')
                parts = variable_info_patt.search(variable)
                var = Variable(parts.group(1), parts.group(2), parts.group(3))
                self.add_variable(var)
            msg['content']['text'] = whos_pattern.sub(
                '', msg['content']['text'])
            if msg['content']['text'] == "":
                return None
        return msg

    def get_variables(self):
        return self._variables

    def reset_variables(self):
        self._variables.remove_all()

    def add_variable(self, variable):
        self._variables.append(variable)

    def reset(self):
        self.exec_msg_id = ""
        self.exec_msg_callback = None
        self.exec_msg_arguments = None

        self.executing = False
        self.execution_queue = {}

        self.reset_variables()

    async def wait_for_idle(self):
        while self.status != "idle":
            pass
        return

    def get_messages(self):
        return self.messages

    async def complete(self, code, cursor_pos=None):
        """Get code completion with proper response handling"""

        msg_id = self.kernel_client.complete(code, cursor_pos)

        future = asyncio.Future()
        self.shell_futures[msg_id] = future

        try:
            response = await asyncio.wait_for(future, timeout=5.0)
            return response['content']
        finally:
            self.shell_futures.pop(msg_id, None)
