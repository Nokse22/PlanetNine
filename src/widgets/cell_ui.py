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

from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import GtkSource, Spelling
from gi.repository import Gdk

import os

from ..models.cell import Cell, CellType
from ..others.style_manager import StyleManager
from ..others.output_loader import OutputLoader


@Gtk.Template(resource_path='/io/github/nokse22/PlanetNine/gtk/cell.ui')
class CellUI(Gtk.Box):
    __gtype_name__ = 'CellUI'

    __gsignals__ = {
        'request-delete': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    source_view = Gtk.Template.Child()
    code_buffer = Gtk.Template.Child()
    output_scrolled_window = Gtk.Template.Child()
    count_label = Gtk.Template.Child()
    markdown_text_view = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    output_box = Gtk.Template.Child()
    right_click_menu = Gtk.Template.Child()
    drag_source = Gtk.Template.Child()
    click_gesture = Gtk.Template.Child()
    count_stack = Gtk.Template.Child()

    cell = None

    _cell_type = CellType.CODE

    cache_dir = os.environ["XDG_CACHE_HOME"]

    images_path = os.path.join(cache_dir, "g_images")
    html_path = os.path.join(cache_dir, "g_html")

    def __init__(self, cell):
        super().__init__()

        self.settings = Gio.Settings.new('io.github.nokse22.PlanetNine')

        self.actions_signals = []
        self.bindings = []
        self.providers = []

        self.code_buffer.connect("changed", self.on_source_changed)
        self.drag_source.connect("prepare", self.on_drag_source_prepare)
        self.drag_source.connect("drag-begin", self.on_drag_source_begin)
        self.drag_source.connect("drag-end", self.delete_cell)
        self.click_gesture.connect("released", self.on_click_released)
        self.markdown_text_view.connect("changed", self.on_source_changed)

        self.cell = cell

        lm = GtkSource.LanguageManager()
        lang = lm.get_language("python3")
        self.code_buffer.set_language(lang)
        self.code_buffer.set_highlight_syntax(True)

        self.style_manager = StyleManager()
        self.style_manager.connect("style-changed", self.update_style_scheme)
        self.update_style_scheme()

        self.output_loader = OutputLoader(self.output_box)

        # ENABLE SPELL CHECK

        checker = Spelling.Checker.get_default()
        adapter = Spelling.TextBufferAdapter.new(self.code_buffer, checker)
        extra_menu = adapter.get_menu_model()

        self.source_view.set_extra_menu(extra_menu)
        self.source_view.insert_action_group('spelling', adapter)

        adapter.set_enabled(True)

        self.text_buffer = self.markdown_text_view.get_buffer()

        self.drag_source.set_actions(Gdk.DragAction.MOVE)

        self.cell_type = self.cell.cell_type
        self.set_content(self.cell.source)
        for output in self.cell.outputs:
            self.add_output(output)
        self.set_execution_count(self.cell.execution_count)

        self.action_group = Gio.SimpleActionGroup()

        self.create_action('delete', self.delete_cell)
        self.create_action('change_type', self.on_change_type)
        self.create_action(
            'toggle_output_expand', self.on_toggle_output_expand)

        self.insert_action_group("cell", self.action_group)

        self.bindings.append(self.bind_property("source", self.cell, "source"))
        self.bindings.append(
            self.bind_property("cell_type", self.cell, "cell_type"))

        self.cell.connect(
            "execution-count-changed", self.on_execution_count_changed)
        self.cell.connect("output-added", self.on_add_output)
        self.cell.connect("output-reset", self.on_reset_output)
        self.cell.connect("notify::executing", self.on_executing_changed)

        self.settings.bind(
            'notebook-line-number',
            self.source_view,
            'show-line-numbers',
            Gio.SettingsBindFlags.DEFAULT
        )

        # POPOVER
        self.popover = Gtk.PopoverMenu(
            menu_model=self.right_click_menu,
            has_arrow=False,
            halign=1,
        )

    def update_style_scheme(self, *args):
        scheme = self.style_manager.get_current_scheme()
        self.code_buffer.set_style_scheme(scheme)

    @GObject.Property(type=str, default="")
    def source(self):
        return self.get_content()

    @source.setter
    def source(self, value):
        self.set_content(value)

    @GObject.Property(type=int, default=0)
    def cell_type(self):
        return self._cell_type

    @cell_type.setter
    def cell_type(self, value):
        content = self.get_content()

        if value == CellType.TEXT:
            self.stack.set_visible_child_name("text")
            self.count_stack.set_visible(False)
            self.output_scrolled_window.set_visible(False)
        elif value == CellType.CODE:
            self.stack.set_visible_child_name("code")
            self.count_stack.set_visible(True)

        self._cell_type = value

        self.set_content(content)

    def add_provider(self, provider):
        provider.register(self.code_buffer)
        self.source_view.get_completion().add_provider(provider)

        self.providers.append(provider)

    def set_content(self, value):
        if self._cell_type == CellType.TEXT:
            self.text_buffer.set_text(value)

        elif self._cell_type == CellType.CODE:
            self.code_buffer.set_text(value)

    def get_content(self):
        if self.cell.cell_type == CellType.TEXT:
            start = self.text_buffer.get_start_iter()
            end = self.text_buffer.get_end_iter()
            return self.text_buffer.get_text(start, end, True)

        elif self.cell.cell_type == CellType.CODE:
            start = self.code_buffer.get_start_iter()
            end = self.code_buffer.get_end_iter()
            return self.code_buffer.get_text(start, end, True)

    def set_execution_count(self, value):
        self.count_label.set_label(str(value or 0))

    def on_executing_changed(self, *args):
        if self.cell.executing:
            self.count_stack.set_visible_child_name("spinner")
        else:
            self.count_stack.set_visible_child_name("number")

    def add_output(self, output):
        self.output_scrolled_window.set_visible(True)
        self.output_loader.add_output(output)

    def reset_output(self):
        self.output_scrolled_window.set_visible(False)

        child = self.output_box.get_first_child()
        while child:
            self.output_box.remove(child)
            child = self.output_box.get_first_child()

    def on_click_released(self, gesture, n_press, click_x, click_y):
        if n_press != 1:
            return

        widget = gesture.get_widget()

        position = Gdk.Rectangle()
        position.x = click_x
        position.y = click_y
        self.popover.set_parent(widget)
        self.popover.set_pointing_to(position)
        self.popover.popup()

        return True

    def on_toggle_output_expand(self, *args):
        _, vscrollbar_policy = self.output_scrolled_window.get_policy()

        if vscrollbar_policy == Gtk.PolicyType.AUTOMATIC:
            self.output_scrolled_window.set_policy(
                Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        else:
            self.output_scrolled_window.set_policy(
                Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    def on_change_type(self, *args):
        if self.cell_type == CellType.TEXT:
            self.cell_type = CellType.CODE
        elif self.cell_type == CellType.CODE:
            self.cell_type = CellType.TEXT

    def create_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.action_group.add_action(action)
        self.actions_signals.append((action, callback))
        return action

    def on_source_changed(self, buffer, *args):
        self.notify("source")

    def on_drag_source_prepare(self, source, x, y):
        value = GObject.Value()
        value.init(Cell)
        value.set_object(self.cell.copy())

        return Gdk.ContentProvider.new_for_value(value)

    def on_drag_source_begin(self, source, drag):
        builder = Gtk.Builder.new_from_resource(
            '/io/github/nokse22/PlanetNine/gtk/cell_drag.ui')
        drag_widget = builder.get_object('drag_widget')

        builder.get_object('count').set_label(self.count_label.get_label())
        builder.get_object('code').set_label(self.get_content()[:20] + '...')

        icon = Gtk.DragIcon.get_for_drag(drag)
        icon.set_child(drag_widget)

        drag.set_hotspot(0, 0)

    def delete_cell(self, *args):
        self.popover.popdown()
        self.emit("request-delete")

    def on_reset_output(self, cell):
        self.reset_output()

    def on_execution_count_changed(self, cell, value):
        self.set_execution_count(value)

    def on_add_output(self, cell, output):
        self.add_output(output)

    #
    #   Implement Disconnectable Interface
    #

    def disconnect(self, *args):
        self.style_manager.disconnect_by_func(self.update_style_scheme)
        self.cell.disconnect_by_func(self.on_execution_count_changed)
        self.cell.disconnect_by_func(self.on_add_output)
        self.cell.disconnect_by_func(self.on_reset_output)
        self.cell.disconnect_by_func(self.on_executing_changed)
        self.code_buffer.disconnect_by_func(self.on_source_changed)
        self.drag_source.disconnect_by_func(self.on_drag_source_prepare)
        self.drag_source.disconnect_by_func(self.on_drag_source_begin)
        self.drag_source.disconnect_by_func(self.delete_cell)
        self.click_gesture.disconnect_by_func(self.on_click_released)
        self.markdown_text_view.disconnect_by_func(self.on_source_changed)

        for action, callback in self.actions_signals:
            action.disconnect_by_func(callback)
        del self.actions_signals

        for binding in self.bindings:
            binding.unbind()
        del self.bindings

        for provider in self.providers:
            provider.unregister(self.code_buffer)
            self.source_view.get_completion().remove_provider(provider)

        print(f"closing: {self}")

        del self.cell

    def __del__(self):
        print(f"DELETING {self}")
