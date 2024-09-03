# utilities.py
#
# Copyright 2024 Nokse22
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os


def get_next_filepath(folder_path, base_name, extension):
    os.makedirs(folder_path, exist_ok=True)

    files = os.listdir(folder_path)

    new_file_name = f"{base_name}{extension}"

    if new_file_name in files:
        counter = 1
        while True:
            new_file_name = f"{base_name}{counter}{extension}"
            if new_file_name not in files:
                break
            counter += 1

    new_file_path = os.path.join(folder_path, new_file_name)

    return new_file_path


def format_json(json_string):
    json_string = json_string.replace("'", '"')
    json_string = json_string.replace('True', 'true')
    json_string = json_string.replace('False', 'false')
    json_string = json_string.replace('None', 'null')

    return json_string
