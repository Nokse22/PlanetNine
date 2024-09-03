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

from gi.repository import GObject

from enum import IntEnum

import nbformat


class OutputType(IntEnum):
    STREAM = 0
    DISPLAY_DATA = 1
    EXECUTE_RESULT = 2
    ERROR = 3


class DataType(IntEnum):
    TEXT = 1
    JSON = 2
    MARKDOWN = 3
    HTML = 4
    IMAGE_PNG = 5
    IMAGE_JPEG = 6
    IMAGE_SVG = 7


class Output(GObject.GObject):
    __gtype_name__ = 'Output'

    name = GObject.Property(type=str, default="")
    text = GObject.Property(type=str, default="")
    execution_count = GObject.Property(type=int, default=0)

    ename = GObject.Property(type=str, default="")
    evalue = GObject.Property(type=str, default="")
    traceback = GObject.Property(type=str, default="")

    data_type = GObject.Property(type=int, default=0)
    data_content = GObject.Property(type=str, default="")

    output_type = 0

    def __init__(self, _output_type):
        super().__init__()

        self.output_type = _output_type

        self.name = ""
        self.text = ""
        self.execution_count = 0

        self.ename = ""
        self.evalue = ""
        self.traceback = ""

        self.data_type = 0
        self.data_content = ""
        self.plain_content = None

        self.metadata = None

    @classmethod
    def new_from_json(cls, json_string):
        instance = cls()

        instance.parse(json_string)

        return instance

    def parse(self, json_dict):

        match self.output_type:
            case OutputType.STREAM:
                self.parse_stream(json_dict)
            case OutputType.DISPLAY_DATA:
                self.parse_display_data(json_dict)
            case OutputType.EXECUTE_RESULT:
                self.parse_execute_result(json_dict)
            case OutputType.ERROR:
                self.parse_error(json_dict)

    def parse_stream(self, json):
        self.name = json['name']
        self.text = json['text']

    def parse_display_data(self, json):
        if 'application/json' in json['data']:
            self.data_content = json['data']['application/json']
            self.data_type = DataType.JSON
        elif 'text/markdown' in json['data']:
            self.data_content = json['data']['text/markdown']
            self.data_type = DataType.MARKDOWN
        elif 'text/html' in json['data']:
            self.data_content = json['data']['text/html']
            self.data_type = DataType.HTML
        elif 'image/png' in json['data']:
            self.data_content = json['data']['image/png']
            self.data_type = DataType.IMAGE_PNG
        elif 'text/plain' in json['data']:
            self.data_content = json['data']['text/plain']
            self.data_type = DataType.TEXT

        if 'text/plain' in json['data']:
            self.plain_content = json['data']['text/plain']

        if 'metadata' in json['data']:
            self.metadata = json['data']['metadata']

    def parse_execute_result(self, json):
        self.parse_display_data(json)
        self.execution_count = json['execution_count']

    def parse_error(self, json):
        self.ename = json['ename']
        self.evalue = json['evalue']
        self.traceback = "\n".join(json['traceback'])

    def get_output_node(self):
        match self.output_type:
            case OutputType.STREAM:
                output_node = nbformat.v4.new_output('stream')
                output_node.text = self.text

            case OutputType.DISPLAY_DATA:
                output_node = nbformat.v4.new_output('display_data')
                type_name = self.get_type_name(self.data_type)
                output_node.data[type_name] = self.data_content
                if self.plain_content:
                    output_node.data['text/plain'] = self.plain_content

            case OutputType.EXECUTE_RESULT:
                output_node = nbformat.v4.new_output('execute_result')
                type_name = self.get_type_name(self.data_type)
                output_node.data[type_name] = self.data_content
                if self.plain_content:
                    output_node.data['text/plain'] = self.plain_content

            case OutputType.ERROR:
                output_node = nbformat.v4.new_output('error')
                output_node.ename = self.ename
                output_node.evalue = self.evalue
                output_node.traceback = self.traceback

        if self.metadata:
            output_node.metadata = self.metadata

        return output_node

    def get_type_name(self, data_type):
        mime_types = {
            DataType.JSON: "application/json",
            DataType.MARKDOWN: "text/markdown",
            DataType.HTML: "text/html",
            DataType.IMAGE_PNG: "image/png",
            DataType.IMAGE_JPEG: "image/jpeg",
            DataType.IMAGE_SVG: "image/svg+xml",
            DataType.TEXT: "text/plain",
        }

        return mime_types.get(data_type, "text/plain")