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

        self._variables = Gio.ListStore()

        self.messages = []

        self.kernel_client = jupyter_client.AsyncKernelClient()

        self.data_dir = GLib.getenv("XDG_DATA_HOME")

        self.__connect()

        self.executing = False

        self.execution_queue = []

        self.exec_msg_id = ""
        self.exec_msg_callback = None
        self.exec_msg_arguments = None

        asyncio.create_task(self.__get_control_msg())
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

                if not msg:
                    return

                msg = self.extract_variables(msg)

                msg_type = msg['header']['msg_type']
                msg_content = msg['content']
                if 'msg_id' in msg['parent_header']:
                    msg_id = msg['parent_header']['msg_id']
                else:
                    msg_id = ''

                print(f"\nReceived {msg_type} MSG with ID: {msg_id}")
                print(f"Queued message ID is: {self.exec_msg_id}")
                print("IOPUB MSG:")
                pprint(msg)

                if msg_type == 'stream':
                    self.messages.append(msg_content['text'])

                elif msg_type == 'execute_input':
                    code = msg_content['code']
                    start = f"In [{msg_content['execution_count']}]"
                    code_modified = "\n".join(
                        " " * len(start) + ln for ln in code.splitlines())

                    self.messages.append(
                        f"\033[32;1m{start}\033[0m\n{code_modified}")

                elif msg_type == 'error':
                    self.messages.append("\n".join(msg_content['traceback']))

                if msg_id in self.exec_msg_id:
                    print("Matching ID\n")
                    if self.exec_msg_callback:
                        self.exec_msg_callback(
                            msg, *self.exec_msg_arguments)

                if msg_type == 'status':
                    self.status = msg['content']['execution_state']
                    print(f"STATUS: {self.status}")
                    self.emit("status-changed", self.status)

                    if self.status == "idle":
                        self.executing = False
                        if not len(self.execution_queue) == 0:
                            self.execution_queue.pop(0)
                        if len(self.execution_queue) >= 1:
                            code, callback, *args = self.execution_queue[0]
                            asyncio.create_task(
                                self._execute(code, callback, *args))

            except Exception as e:
                print(f"Exception while getting iopub msg: {e}")
                traceback.print_exc()

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
        self.execution_queue.append((code, callback, *args))

        print("EXECUTE: ", self.executing, len(self.execution_queue), code)

        if not self.executing:
            self.executing = True
            asyncio.create_task(self._execute(code, callback, *args))

    async def _execute(self, code, callback, *args):
        print("AWAITING READY")
        # await self.wait_for_idle()
        await self.kernel_client.wait_for_ready()

        code += '\n%whos'  # added %whos to get the variables
        # FIXME if it's not ipykernel it should not be used

        msg_id = self.kernel_client.execute(code)

        print(f"Executing with ID: {msg_id}")

        self.exec_msg_id = msg_id
        self.exec_msg_callback = callback
        self.exec_msg_arguments = args

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
        self.execution_queue = []

        self.reset_variables()

    async def wait_for_idle(self):
        while self.status != "idle":
            pass
        return

    def get_messages(self):
        return self.messages
