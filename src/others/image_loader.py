# image_loader.py
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

from gi.repository import Gtk, Panel, GLib, Gio, Gdk, GObject, GdkPixbuf

from gettext import gettext as _

import os
import base64
import hashlib


class ImageLoader(GObject.GObject):
    __gtype_name__ = "ImageLoader"

    cache_dir = os.environ["XDG_CACHE_HOME"]

    def __init__(self):
        super().__init__()

    def load_from_base64(self, mime, image_content):
        image_data = base64.b64decode(image_content["data"]["image/png"])
        sha256_hash = hashlib.sha256(image_data).hexdigest()

        image_path = os.path.join(
            self.cache_dir,
            "g_images",
            f"{sha256_hash}.png")
        with open(image_path, "wb") as f:
            f.write(image_data)
