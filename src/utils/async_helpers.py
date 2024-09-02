# async_helpers.py
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

import asyncio


async def dialog_choose_async(window, dialog):
    loop = asyncio.get_running_loop()
    dialog_future = loop.create_future()

    def __callback(dialog, result):
        dialog_future.set_result(dialog.choose_finish(result))

    dialog.choose(window, None, __callback)

    return await dialog_future
