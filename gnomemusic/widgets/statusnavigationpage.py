# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from enum import IntEnum
import typing

from gettext import gettext as _
from gi.repository import Adw, GLib, GObject, Gtk, Tracker

from gnomemusic.widgets.headerbar import HeaderBar
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


@Gtk.Template(resource_path="/org/gnome/Music/ui/StatusNavigationPage.ui")
class StatusNavigationPage(Adw.NavigationPage):
    """Status page when there is no music or an issue with Tracker

    This view can have several states

    EMPTY: No music has been found at startup (default)
    NO_TRACKER: Tracker is unavailable
    TRACKER_OUTDATED: Tracker version is too old
    """

    class State(IntEnum):
        """Enum for StatusNavigationPage state."""
        EMPTY = 0
        SEARCH = 1
        NO_TRACKER = 2
        TRACKER_OUTDATED = 3

    __gtype_name__ = "StatusNavigationPage"

    _description_label = Gtk.Template.Child()
    _initial_state = Gtk.Template.Child()
    _status_page = Gtk.Template.Child()
    _toolbar = Gtk.Template.Child()

    def __init__(self, application: Application) -> None:
        super().__init__()

        # FIXME: This is now duplicated here and in TrackerWrapper.
        try:
            music_folder = GLib.get_user_special_dir(
                GLib.UserDirectory.DIRECTORY_MUSIC)
            assert music_folder is not None
        except (TypeError, AssertionError):
            self._content_text = _("Your XDG Music directory is not set.")
        else:
            music_folder = Tracker.sparql_escape_string(
                GLib.filename_to_uri(music_folder))
            href_text = "<a href='{}'>{}</a>".format(
                music_folder, _("Music Folder"))
            # TRANSLATORS: This is a label to display a link to open
            # a user's music folder. {} will be replaced with the
            # translated text 'Music folder'
            folder_text = _("The contents of your {} will appear here.")
            self._content_text = folder_text.format(href_text)

        self._headerbar = HeaderBar(application)
        self._headerbar.props.state = HeaderBar.State.EMPTY
        self._toolbar.add_top_bar(self._headerbar)

        # Hack to get to AdwClamp, so it can be hidden for the
        # initial state.
        child_of_child = self._status_page.get_first_child().get_first_child()
        self._adw_clamp = child_of_child.get_first_child().get_first_child()

        self._status_page.set_child(self._initial_state)

        self.props.state = StatusNavigationPage.State.EMPTY

    @GObject.Property(type=int, default=0, minimum=0, maximum=2)
    def state(self) -> int:
        """Get the state of the empty view

        :returns: The view state
        :rtype: int
        """
        return self._state

    @state.setter  # type: ignore
    def state(self, value: int) -> None:
        """Set the state of the empty view

        :param int value: new state
        """
        self._state = value

        self._adw_clamp.props.visible = True
        self._initial_state.props.visible = False

        if self._state == StatusNavigationPage.State.EMPTY:
            self._set_empty_state()
        elif self._state == StatusNavigationPage.State.SEARCH:
            self._set_search_state()
        elif self._state == StatusNavigationPage.State.NO_TRACKER:
            self._set_no_tracker_state()
        elif self._state == StatusNavigationPage.State.TRACKER_OUTDATED:
            self._set_tracker_outdated_state()

        self._headerbar.props.state = HeaderBar.State.EMPTY

    def _set_empty_state(self) -> None:
        self._adw_clamp.props.visible = False
        self._initial_state.props.visible = True

        self._description_label.props.label = self._content_text

    def _set_search_state(self) -> None:
        self._status_page.props.title = _("No Music Found")
        self._status_page.props.description = _("Try a Different Search")

    def _set_no_tracker_state(self) -> None:
        self._status_page.props.title = _(
            "GNOME Music could not connect to Tracker.")
        self._status_page.props.description = _(
            "Your music files cannot be indexed without Tracker running.")

        self._status_page.props.icon_name = "dialog-error-symbolic"

    def _set_tracker_outdated_state(self) -> None:
        self._status_page.props.title = _(
            "Your system Tracker version seems outdated.")
        self._status_page.props.description = _(
            "Music needs Tracker version 3.0.0 or higher.")

        self._status_page.props.icon_name = "dialog-error-symbolic"
