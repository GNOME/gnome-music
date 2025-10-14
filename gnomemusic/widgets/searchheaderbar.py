# Copyright 2025 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from typing import Any

from gettext import gettext as _
from gi.repository import Adw, GObject, Gtk

from gnomemusic.search import Search


@Gtk.Template(resource_path="/org/gnome/Music/ui/SearchHeaderBar.ui")
class SearchHeaderBar(Adw.Bin):
    """SearcnHeaderbar of the application"""

    __gtype_name__ = "SearchHeaderBar"

    _search_header_bar = Gtk.Template.Child()
    _search_button = Gtk.Template.Child()

    search_mode_active = GObject.Property(type=bool, default=False)
    search_state = GObject.Property(type=int, default=0)
    search_text = GObject.Property(type=str)

    def __init__(self, application):
        super().__init__()

        self._coregrilo = application.props.coregrilo

        self._entry = Gtk.SearchEntry()
        self._entry.props.placeholder_text = _(
            "Search songs, artists and albums")
        self._entry.props.halign = Gtk.Align.CENTER
        self._entry.props.visible = True
        self._entry.props.width_request = 500
        self._entry.props.search_delay = 250
        self._search_header_bar.props.title_widget = self._entry

        self.bind_property(
            "search-mode-active", self._search_button, "active",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self.bind_property("search-text", self._entry, "text")
        self.connect("notify::search-text", self._on_search_text_changed)

        self.connect(
            "notify::search-mode-active", self._on_search_mode_changed)
        self.connect("notify::search-state", self._search_state_changed)

        self._entry.connect("search-changed", self._search_entry_changed)

        shortcut_controller = Gtk.ShortcutController.new()
        self._entry.add_controller(shortcut_controller)

        search_bar_close_shortcut = Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("Escape"),
            Gtk.ShortcutAction.parse_string("action(win.search_bar_close)"))
        shortcut_controller.add_shortcut(search_bar_close_shortcut)

    def _search_entry_changed(self, widget: Gtk.SearchEntry) -> bool:
        search_term = self._entry.get_text()
        self._coregrilo.search(search_term)

        if search_term == "":
            self._set_error_style(False)
            self.props.search_state = Search.State.NONE

        return False

    def _on_search_mode_changed(self, klass, data):
        if self.props.search_mode_active:
            self._entry.grab_focus()

    def _search_state_changed(self, klass, data):
        search_state = self.props.search_state

        if search_state == Search.State.NO_RESULT:
            self._set_error_style(True)
        elif search_state == Search.State.RESULT:
            self._set_error_style(False)
        elif search_state == Search.State.NONE:
            self._set_error_style(False)
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

    def _on_search_text_changed(
            self, searchheaderbar: SearchHeaderBar, data: Any) -> None:
        self._entry.set_position(len(self._entry.props.text))
