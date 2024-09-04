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


class PlanetnineApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id='io.github.nokse22.PlanetNine',
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.create_action('quit', lambda *_: self.quit(), ['<primary>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('preferences', self.on_preferences_action, ['<primary>comma'])
        self.create_action('run', self.on_run_action, ['<primary>Escape'])

        self.create_action('save', self.on_save_action, ['<primary>s'])
        self.create_action('save-all', self.on_save_all_action, ['<primary><shift>s'])

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        self.win = self.props.active_window
        if not self.win:
            self.win = PlanetnineWindow(application=self)
        self.win.present()

        self.win.connect("close-request", self.on_shutdown)

    def on_run_action(self, *args):
        self.props.active_window.run_selected_cell()

    def on_save_action(self, *args):
        self.props.active_window.save_viewed()

    def on_save_all_action(self, *args):
        self.props.active_window.save_viewed()

    def on_about_action(self, *args):
        """Callback for the app.about action."""
        about = Adw.AboutWindow(application_name='planetnine',
                                application_icon='io.github.nokse22.PlanetNine',
                                developer_name='Nokse',
                                version='0.1.0',
                                developers=['Nokse'],
                                copyright='© 2024 Nokse')
        # Translators: Replace "translator-credits" with your name/username, and optionally an email or URL.
        about.set_translator_credits(_('translator-credits'))
        about.present(self.props.active_window)

    def on_preferences_action(self, widget, _):
        """Callback for the app.preferences action."""
        print('app.preferences action activated')

        preferences = Preferences()

        self.settings.bind('code-vim', preferences.code_vim_switch, 'active', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('code-line-number', preferences.code_line_number_switch, 'active', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('code-highlight-row', preferences.code_highlight_row_switch, 'active', Gio.SettingsBindFlags.DEFAULT)

        preferences.present(self.props.active_window)

    def on_shutdown(self, *args):
        return self.win.close()

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    """The application's entry point."""
    app = PlanetnineApplication()
    return app.run(sys.argv)
