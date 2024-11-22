# main.py
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

import sys
import asyncio

from gi.repository import Gio, Adw, GObject, GtkSource
from gi.repository import Vte
from gi.events import GLibEventLoopPolicy
from gi.repository import Panel

from .window import PlanetnineWindow
from .preferences import Preferences

from gettext import gettext as _

GtkSource.init()
Panel.init()

GObject.type_register(Vte.Terminal)
GObject.type_register(GtkSource.View)
GObject.type_register(GtkSource.Buffer)
GObject.type_register(GtkSource.StyleSchemePreview)
GObject.type_register(Panel.Dock)
GObject.type_register(Panel.Grid)
GObject.type_register(Panel.Paned)
GObject.type_register(Panel.OmniBar)
GObject.type_register(Panel.Statusbar)
GObject.type_register(Panel.ToggleButton)

asyncio.set_event_loop_policy(GLibEventLoopPolicy())


class PlanetnineApplication(Panel.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id='io.github.nokse22.PlanetNine',
                         flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.create_action(
            'quit', lambda *_: self.quit(), ['<primary>q'])
        self.create_action(
            'about', self.on_about_action)
        self.create_action(
            'preferences', self.on_preferences_action, ['<primary>comma'])
        self.create_action(
            'run', self.on_run_action)
        self.create_action(
            'search', self.on_search_action, ['<primary>f'])

        self.create_action(
            'save', self.on_save_action, ['<primary>s'])
        self.create_action(
            'save-as', self.on_save_action)
        self.create_action(
            'save-all', self.on_save_all_action, ['<primary><shift>s'])

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

        self.preferences = None

    def do_open(self, files, n_files, hint):
        if not self.win:
            self.win = PlanetnineWindow(application=self)
            self.win.present()

        for file in files:
            file_path = file.get_path()
            self.win.open_file(file_path)

    def do_activate(self):
        self.win = self.props.active_window
        if not self.win:
            self.win = PlanetnineWindow(application=self)
        self.win.present()

        self.preferences = Preferences()

        self.win.connect("close-request", self.on_shutdown)

    def on_run_action(self, *_args):
        self.win.run_selected_cell()

    def on_save_action(self, *_args):
        self.win.save_viewed()

    def on_save_all_action(self, *_args):
        self.win.save_viewed()

    def on_about_action(self, *_args):
        about = Adw.AboutDialog(
            application_name='Planet Nine',
            application_icon='io.github.nokse22.PlanetNine',
            developer_name='Nokse',
            version='0.1.0',
            developers=['Nokse'],
            copyright='© 2024 Nokse')
        # Translators: Replace "translator-credits" with your name/username,
        # and optionally an email or URL.
        about.set_translator_credits(_('translator-credits'))
        about.present(self.win)

    def on_preferences_action(self, widget, _):
        print('app.preferences action activated')

        if self.preferences:
            self.preferences.present(self.win)
            return

        self.preferences = Preferences()

        self.preferences.present(self.win)

    def on_search_action(self, *_args):
        self.win.search_visible_page()

    def on_shutdown(self, *_args):
        return self.win.close()

    def create_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    app = PlanetnineApplication()
    return app.run(sys.argv)
