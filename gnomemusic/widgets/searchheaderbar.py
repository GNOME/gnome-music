# Copyright 2019 The GNOME Music developers
#
# GNOME Music is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# GNOME Music is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with GNOME Music; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# The GNOME Music authors hereby grant permission for non-GPL compatible
# GStreamer plugins to be used and distributed together with GStreamer
# and GNOME Music.  This permission is above and beyond the permissions
# granted by the GPL license by which GNOME Music is covered.  If you
# modify this code, you may extend this exception to your version of the
# code, but you are not obligated to do so.  If you do not wish to do so,
# delete this exception statement from your version.

from __future__ import annotations
from enum import IntEnum
import typing

from gi.repository import Adw, GObject, Gtk

from gnomemusic.search import Search
from gnomemusic.widgets.headerbar import HeaderBar, SelectionBarMenuButton
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


@Gtk.Template(resource_path="/org/gnome/Music/ui/SearchHeaderBar.ui")
class SearchHeaderBar(Adw.Bin):
    """SearcnHeaderbar of the application"""

    class State(IntEnum):
        """States the SearchHeaderbar can have"""
        MAIN = 0
        CHILD = 1
        SEARCH = 2
        EMPTY = 3

    __gtype_name__ = "SearchHeaderBar"

    _headerbar = Gtk.Template.Child()
    _search_button = Gtk.Template.Child()
    _select_button = Gtk.Template.Child()
    _cancel_button = Gtk.Template.Child()

    search_mode_active = GObject.Property(type=bool, default=False)
    search_state = GObject.Property(type=int, default=Search.State.NONE)
    selected_songs_count = GObject.Property(type=int, default=0, minimum=0)
    selection_mode_allowed = GObject.Property(type=bool, default=True)
    stack = GObject.Property(type=Adw.ViewStack)

    def __init__(self, application):
        super().__init__()

        self._coregrilo = application.props.coregrilo
        self._selection_mode = False

        self._entry = Gtk.SearchEntry()
        self._entry.props.halign = Gtk.Align.CENTER
        self._entry.props.visible = True
        self._entry.props.width_request = 500

        self._selection_menu = SelectionBarMenuButton()

        self.bind_property(
            "selection-mode", self._headerbar, "show-end-title-buttons",
            GObject.BindingFlags.INVERT_BOOLEAN
            | GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "selection-mode", self._cancel_button, "visible")
        self.bind_property(
            "selection-mode", self._select_button, "visible",
            GObject.BindingFlags.INVERT_BOOLEAN)
        self.bind_property(
            "selection-mode", self._select_button, "active",
            GObject.BindingFlags.BIDIRECTIONAL)
        self.bind_property(
            "selected-songs-count", self._selection_menu,
            "selected-songs-count")
        self.bind_property(
            "search-mode-active", self._search_button, "active",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "selection-mode", self._search_button, "visible",
            GObject.BindingFlags.INVERT_BOOLEAN
            | GObject.BindingFlags.SYNC_CREATE)

        self.connect(
            "notify::selection-mode-allowed",
            self._on_selection_mode_allowed_changed)

        self.connect(
            "notify::search-mode-active", self._on_search_mode_changed)
        self.connect("notify::search-state", self._search_state_changed)

        self._entry.connect("search-changed", self._search_entry_changed)

        self._win_id = application.connect(
            "notify::window", self._on_window_ready)

    def _on_window_ready(
            self, application: Application,
            value: GObject.ParamSpecObject) -> None:
        self._entry.set_key_capture_widget(application.props.window)
        application.disconnect(self._win_id)
        self._win_id = 0

    @GObject.Property(type=bool, default=False)
    def selection_mode(self):
        """Selection mode

        :returns: Selection mode
        :rtype: bool
        """
        return self._selection_mode

    @selection_mode.setter  # type: ignore
    def selection_mode(self, mode):
        """Set the selection mode

        :param bool value: Selection mode
        """
        self._selection_mode = mode

        if mode:
            self.get_style_context().add_class("selection-mode")
        else:
            self.get_style_context().remove_class("selection-mode")
            self._select_button.props.active = False

        self._update()

    @GObject.Property
    def state(self):
        """State of the widget

        :returns: Widget state
        :rtype: HeaderBar.State
        """
        return self._state

    @state.setter  # type: ignore
    def state(self, value):
        """Set state of the of widget

        This influences the look and functionality of the headerbar.

        :param HeaderBar.State value: Widget state
        """
        self._state = value
        self._update()

        search_visible = self.props.state != HeaderBar.State.SEARCH
        self._search_button.props.visible = search_visible

        if value == HeaderBar.State.EMPTY:
            self._search_button.props.sensitive = False
            self._select_button.props.sensitive = False
            self._entry.props.visible = False
        else:
            self._search_button.props.sensitive = True
            self._select_button.props.sensitive = True
            self._entry.props.visible = False

    @Gtk.Template.Callback()
    def _on_cancel_button_clicked(self, button):
        self.props.selection_mode = False

    def _update(self):
        if self.props.selection_mode:
            self._headerbar.props.title_widget = self._selection_menu
        else:
            self._headerbar.props.title_widget = self._entry

    def _on_selection_mode_allowed_changed(self, widget, data):
        if self.props.selection_mode_allowed:
            self._select_button.props.sensitive = True
        else:
            self._select_button.props.sensitive = False

    def _search_entry_changed(self, widget: Gtk.SearchEntry) -> bool:
        search_term = self._entry.get_text()
        if search_term != "":
            self.props.stack.set_visible_child_name("search")
            self._coregrilo.search(search_term)
        else:
            self._set_error_style(False)

        return False

    def _on_search_mode_changed(self, klass, data):
        if self.props.search_mode_active:
            self._entry.grab_focus()

    def _search_state_changed(self, klass, data):
        search_state = self.props.search_state

        if search_state == Search.State.NO_RESULT:
            self._set_error_style(True)
            self.props.stack.props.visible_child_name = "emptyview"
        elif search_state == Search.State.RESULT:
            self._set_error_style(False)
            self.props.stack.props.visible_child_name = "search"
        elif search_state == Search.State.NONE:
            self._entry.props.text = ""

    def _set_error_style(self, error):
        """Adds error state to the search entry.

        :param bool error: Whether to add error state
        """
        style_context = self._entry.get_style_context()
        if error:
            style_context.add_class("error")
        else:
            style_context.remove_class("error")
