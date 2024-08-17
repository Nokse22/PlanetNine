# console_page.py
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

from gi.repository import Gtk, GObject, Adw
from gi.repository import Panel, GtkSource

GObject.type_register(Panel.Widget)

@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/console_page.ui')
class ConsolePage(Panel.Widget):
    __gtype_name__ = 'ConsolePage'

    code_buffer = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        lm = GtkSource.LanguageManager()
        lang = lm.get_language("python")
        self.code_buffer.set_language(lang)
        self.code_buffer.set_highlight_syntax(True)

        sm = GtkSource.StyleSchemeManager()
        scheme = sm.get_scheme("Adwaita-dark")
        self.code_buffer.set_style_scheme(scheme)

        style_manager = Adw.StyleManager.get_default()
        style_manager.connect("notify::dark", self.update_style_scheme)
        self.update_style_scheme()

    def set_kernel(self, jupyter_kernel):
        print(jupyter_kernel)

    def update_style_scheme(self, *args):
        scheme_name = "Adwaita"
        if Adw.StyleManager.get_default().get_dark():
            scheme_name += "-dark"
        sm = GtkSource.StyleSchemeManager()
        scheme = sm.get_scheme(scheme_name)
        self.code_buffer.set_style_scheme(scheme)

    @Gtk.Template.Callback("on_send_clicked")
    def on_send_clicked(self, *args):
        self.run_code()

    def run_code(self):
        content = self.get_content()

        if content.startswith("%"):
            # self.reset_output()
            # self.command_line.run_command(
            #     content[1:].split(" "),
            #     self.run_command_callback,
            #     cell
            # )
            pass
        elif self.notebook_model.jupyter_kernel:
            self.notebook_model.jupyter_kernel.run_code(
                content,
                self.run_code_callback,
                cell
            )

    # def run_command_callback(self, line, cell):
    #     output = Output(OutputType.STREAM)
    #     output.text = line + '\n'
    #     cell.add_output(output)

    def run_code_callback(self, msg, cell):
        msg_type = msg['header']['msg_type']
        content = msg['content']

        # if msg_type == 'stream':
        #     output = Output(OutputType.STREAM)
        #     output.parse(content)
        #     cell.add_output(output)

        #     self._kernel_status = "busy"
        #     self.emit("kernel-info-changed", self._kernel_name, self._kernel_status)

        # elif msg_type == 'execute_input':
        #     count = content['execution_count']
        #     cell.execution_count = int(count)
        #     cell.reset_output()

        # elif msg_type == 'display_data':
        #     output = Output(OutputType.DISPLAY_DATA)
        #     output.parse(content)
        #     cell.add_output(output)

        # elif msg_type == 'error':
        #     output = Output(OutputType.ERROR)
        #     output.parse(content)
        #     cell.add_output(output)

        # elif msg_type == 'status':
        #     status = content['execution_state']

        #     self._kernel_status = status
        #     self.emit("kernel-info-changed", self._kernel_name, self._kernel_status)

    def get_content(self):
        start = self.code_buffer.get_start_iter()
        end = self.code_buffer.get_end_iter()
        return self.code_buffer.get_text(start, end, True)

    def __on_unrealized(self, *args):
        pass

    def __del__(self, *args):
        print(f"DELETING {self}")
