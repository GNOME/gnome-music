# Copyright (c) 2018 The GNOME Music Developers
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
from gi.repository import GLib, GObject, Gtk

from gnomemusic import log


class NotificationsPopup(Gtk.Revealer):
    """Display notification messages as popups

    There are two types of messages:
    - loading notification
    - playlist or song deletion
    Messages are arranged under each other
    """

    def __repr__(self):
        return '<NotificationsPopup>'

    @log
    def __init__(self):
        super().__init__(
            halign=Gtk.Align.CENTER, valign=Gtk.Align.START,
            transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN)
        self._setup_view()

    @log
    def _setup_view(self):
        frame = Gtk.Frame()
        frame.get_style_context().add_class('app-notification')
        self.add(frame)

        self._grid = Gtk.Grid(
            row_spacing=6, orientation=Gtk.Orientation.VERTICAL)
        frame.add(self._grid)

        self._loading_notification = LoadingNotification()
        self._loading_notification.connect('visible', self._set_visibility)
        self._loading_notification.connect('invisible', self._set_visibility)
        self._grid.add(self._loading_notification)

        self.show_all()
        self._loading_notification.hide()

    @log
    def _set_visibility(self, widget=None):
        """Display or hide Notifications Popup.

        Popup is displayed if a loading is active or if a playlist
        deletion is in progress.
        """
        invisible = ((self._loading_notification._counter == 0)
                     and (len(self._grid.get_children()) == 1))

        if not invisible:
            self.show()
        else:
            self._loading_notification.hide()
            self.hide()
        self.set_reveal_child(not invisible)

    @log
    def pop_loading(self):
        """Decrease loading notification counter.

        If it reaches zero, the notification is withdrawn.
        """
        self._loading_notification.pop()

    @log
    def push_loading(self):
        """Increase loading notification counter.

        If no notification is visible, start loading notification.
        """
        self._loading_notification.push()

    @log
    def add_notification(self, notification):
        """Display a new notification

        :param notification: notification to display
        """
        self._grid.add(notification)
        self.show()
        self.set_reveal_child(True)

    @log
    def remove_notification(self, notification, signal):
        """Remove notification and emit a signal.

        :param notification: notification to remove
        :param signal: signal to emit: deletion or undo action
        """
        self._grid.remove(notification)
        self._set_visibility()
        notification.emit(signal)

    @log
    def terminate_pending(self):
        """Terminate all pending playlists notifications"""
        children = self._grid.get_children()
        if len(children) > 1:
            for notification in children[:-1]:
                self.remove_notification(notification, 'finish-deletion')


class LoadingNotification(Gtk.Grid):
    """LoadingNotification displays a loading notification message

    It can be triggered by different all main views. Message is
    displayed as long as at least one loading operation is in progress.
    """

    __gsignals__ = {
        'visible': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'invisible': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __repr__(self):
        return '<LoadingNotification>'

    @log
    def __init__(self):
        super().__init__(column_spacing=18)
        self._counter = 0
        self._timeout_id = 0

        spinner = Gtk.Spinner()
        spinner.start()
        self.add(spinner)

        label = Gtk.Label(
            label=_("Loading"), halign=Gtk.Align.START, hexpand=True)
        self.add(label)
        self.show_all()

    @log
    def pop(self):
        """Decrease the counter. Hide notification if it reaches 0."""
        self._counter = self._counter - 1

        if self._counter == 0:
            # Stop the timeout if necessary
            if self._timeout_id > 0:
                GLib.source_remove(self._timeout_id)
                self._timeout_id = 0
            self.emit('invisible')

    @log
    def push(self):
        """Increase the counter. Start notification if necessary."""
        def callback():
            self.show_all()
            self.emit('visible')

        if self._counter == 0:
            # Only show the notification after a small delay, thus
            # add a timeout. 500ms feels good enough.
            self._timeout_id = GLib.timeout_add(500, callback)

        self._counter = self._counter + 1


class PlaylistNotification(Gtk.Grid):
    """Show a notification on playlist or song deletion.

    It also provides an option to undo removal. Notification is added
    to the NotificationsPopup.
    """

    class Type(IntEnum):
        """Enum for Playlists Notifications"""
        PLAYLIST = 0
        SONG = 1

    __gsignals__ = {
        'undo-deletion': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'finish-deletion': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __repr__(self):
        return '<PlaylistNotification>'

    @log
    def __init__(self, notifications_popup, type, message, media_id):
        super().__init__(column_spacing=18)
        self._notifications_popup = notifications_popup
        self.type = type
        self.media_id = media_id

        self._label = Gtk.Label(
            label=message, halign=Gtk.Align.START, hexpand=True)
        self.add(self._label)

        undo_button = Gtk.Button.new_with_mnemonic(_("_Undo"))
        undo_button.connect("clicked", self._undo_clicked)
        self.add(undo_button)
        self.show_all()

        self._timeout_id = GLib.timeout_add_seconds(
            5, self._notifications_popup.remove_notification, self,
            'finish-deletion')

        self._notifications_popup.add_notification(self)

    @log
    def _undo_clicked(self, widget):
        """Undo deletion and remove notification"""
        if self._timeout_id > 0:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = 0

        self._notifications_popup.remove_notification(self, 'undo-deletion')
