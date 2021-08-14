# Copyright (c) 2016 The GNOME Music Developers
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

from enum import IntEnum

from gettext import gettext as _
from gi.repository import GLib, GObject, Gtk, Tracker


@Gtk.Template(resource_path="/org/gnome/Music/ui/EmptyView.ui")
class EmptyView(Gtk.Stack):
    """Empty view when there is no music to display

    This view can have three states
    INITIAL means that Music app has never been initialized and no music
    has been found
    EMPTY means that no music has been found at startup
    SEARCH is the empty search view: no music found during a search
    """

    class State(IntEnum):
        """Enum for EmptyView state."""
        INITIAL = 0
        EMPTY = 1
        SEARCH = 2
        NO_TRACKER = 3
        TRACKER_OUTDATED = 4

    __gtype_name__ = "EmptyView"

    _description_label = Gtk.Template.Child()
    _initial_state = Gtk.Template.Child()
    _status_page = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        # FIXME: This is now duplicated here and in GrlTrackerWrapper.
        try:
            music_folder = GLib.get_user_special_dir(
                GLib.UserDirectory.DIRECTORY_MUSIC)
            assert music_folder is not None
        except (TypeError, AssertionError):
            self._content_text = _("Your XDG Music directory is not set.")
            return

        music_folder = Tracker.sparql_escape_string(
            GLib.filename_to_uri(music_folder))

        href_text = "<a href='{}'>{}</a>".format(
            music_folder, _("Music Folder"))

        # TRANSLATORS: This is a label to display a link to open user's music
        # folder. {} will be replaced with the translated text 'Music folder'
        folder_text = _("The contents of your {} will appear here.")
        self._content_text = folder_text.format(href_text)

        # Hack to get to HdyClamp, so it can be hidden for the
        # initial state.
        child_of_child = self._status_page.get_child().get_child()
        self._hdy_clamp = child_of_child.get_child().get_children()[0]

        self._status_page.add(self._initial_state)

        self._state = EmptyView.State.INITIAL

    @GObject.Property(type=int, default=0, minimum=0, maximum=4)
    def state(self):
        """Get the state of the empty view

        :returns: The view state
        :rtype: int
        """
        return self._state

    @state.setter  # type: ignore
    def state(self, value):
        """Set the state of the empty view

        :param int value: new state
        """
        self._state = value

        self._hdy_clamp.props.visible = True
        self._initial_state.props.visible = False

        if self._state == EmptyView.State.INITIAL:
            self._set_initial_state()
        elif self._state == EmptyView.State.EMPTY:
            self._set_empty_state()
        elif self._state == EmptyView.State.SEARCH:
            self._set_search_state()
        elif self._state == EmptyView.State.NO_TRACKER:
            self._set_no_tracker_state()
        elif self._state == EmptyView.State.TRACKER_OUTDATED:
            self._set_tracker_outdated_state()

    def _set_initial_state(self):
        self._status_page.props.title = _("Hey DJ")
        self._status_page.props.description = self._content_text

        self._status_page.props.icon_name = "initial-state"

    def _set_empty_state(self):
        self._hdy_clamp.props.visible = False
        self._initial_state.props.visible = True

        self._description_label.props.label = self._content_text

    def _set_search_state(self):
        self._status_page.props.title = _("No Music Found")
        self._status_page.props.description = _("Try a Different Search")

    def _set_no_tracker_state(self):
        self._status_page.props.title = _(
            "GNOME Music could not connect to Tracker.")
        self._status_page.props.description = _(
            "Your music files cannot be indexed without Tracker running.")

        self._status_page.props.icon_name = "dialog-error-symbolic"

    def _set_tracker_outdated_state(self):
        self._status_page.props.title = _(
            "Your system Tracker version seems outdated.")
        self._status_page.props.description = _(
            "Music needs Tracker version 3.0.0 or higher.")

        self._status_page.props.icon_name = "dialog-error-symbolic"

    def select_all(self):
        """Cannot select songs from EmptyView."""
        pass

    def deselect_all(self):
        """Cannot select songs from EmptyView."""
        pass
