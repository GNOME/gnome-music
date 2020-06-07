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


@Gtk.Template(resource_path="/org/gnome/Music/ui/NotificationsPopup.ui")
class NotificationsPopup(Gtk.Revealer):
    """Display notification messages as popups

    There are two types of messages:
    - loading notification
    - playlist or song deletion
    Messages are arranged under each other
    """

    __gtype_name__ = "NotificationsPopup"

    _grid = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        self._loading_notification = LoadingNotification()
        self._loading_notification.connect('visible', self._set_visibility)
        self._loading_notification.connect('invisible', self._set_visibility)
        self._grid.attach(self._loading_notification, 0, 0, 1, 1)

    def _hide_notifications(self, notification, remove):
        if remove:
            self._grid.remove(notification)
        self._loading_notification.hide()
        self.hide()

    def _set_visibility(self, notification, remove=False):
        """Display or hide Notifications Popup.

        Popup is displayed if a loading is active or if a playlist
        deletion is in progress.
        """
        loading_finished = self._loading_notification._counter == 0
        # no_other_notif = (len(self._grid.get_children()) == 1
        #                   or (len(self._grid.get_children()) == 2
        #                       and notification != self._loading_notification))
        no_other_notif = True
        invisible = loading_finished and no_other_notif

        if not invisible:
            if remove:
                self._grid.remove(notification)
            self.show()
        else:
            # notification has to be removed from grid once unreveal is
            # finished. Otherwise, an empty grid will be unrevealed.
            duration = self.get_transition_duration()
            GLib.timeout_add(
                duration + 100, self._hide_notifications, notification, remove)
        self.set_reveal_child(not invisible)

    def pop_loading(self):
        """Decrease loading notification counter.

        If it reaches zero, the notification is withdrawn.
        """
        self._loading_notification.pop()

    def push_loading(self):
        """Increase loading notification counter.

        If no notification is visible, start loading notification.
        """
        self._loading_notification.push()

    def add_notification(self, notification):
        """Display a new notification

        :param notification: notification to display
        """
        self._grid.attach(notification, 0, 0, 1, 1)
        self.show()
        self.set_reveal_child(True)

    def remove_notification(self, notification):
        """Removes notification.

        :param notification: notification to remove
        """
        self._set_visibility(notification, True)

    def terminate_pending(self):
        """Terminate all pending playlists notifications"""
        children = self._grid.get_children()
        if len(children) > 1:
            for notification in children[:-1]:
                notification._finish_deletion()


@Gtk.Template(resource_path="/org/gnome/Music/ui/LoadingNotification.ui")
class LoadingNotification(Gtk.Grid):
    """LoadingNotification displays a loading notification message

    It can be triggered by different all main views. Message is
    displayed as long as at least one loading operation is in progress.
    """

    __gsignals__ = {
        'visible': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'invisible': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    __gtype_name__ = "LoadingNotification"

    def __init__(self):
        super().__init__()
        self._counter = 0
        self._timeout_id = 0

    def pop(self):
        """Decrease the counter. Hide notification if it reaches 0."""
        self._counter = self._counter - 1

        if self._counter == 0:
            # Stop the timeout if necessary
            if self._timeout_id > 0:
                if not self.is_visible():
                    GLib.source_remove(self._timeout_id)
                self._timeout_id = 0
            self.emit('invisible')

    def push(self):
        """Increase the counter. Start notification if necessary."""
        def callback():
            self.props.visible = True
            self.emit('visible')

        if self._counter == 0:
            # Only show the notification after a small delay, thus
            # add a timeout. 500ms feels good enough.
            self._timeout_id = GLib.timeout_add(500, callback)

        self._counter = self._counter + 1


@Gtk.Template(resource_path="/org/gnome/Music/ui/PlaylistNotification.ui")
class PlaylistNotification(Gtk.Grid):
    """Show a notification on playlist or song deletion.

    It also provides an option to undo removal. Notification is added
    to the NotificationsPopup.
    """

    __gtype_name__ = "PlaylistNotification"

    _label = Gtk.Template.Child()

    class Type(IntEnum):
        """Enum for Playlists Notifications"""
        PLAYLIST = 0
        SONG = 1

    def __init__(
            self, notifications_popup, application, type_, playlist,
            position=None, coresong=None):
        """Creates a playlist deletion notification popup (song or playlist)

        :param GtkRevealer: notifications_popup: the popup object
        :param Apllication: application object
        :param type_: NotificationType (song or playlist)
        :param Playlist playlist: playlist
        :param int position: position of the object to delete
        :param object coresong: CoreSong for song deletion
        """
        super().__init__()
        self._notifications_popup = notifications_popup
        self._coregrilo = application.props.coregrilo
        self.type_ = type_
        self._playlist = playlist
        self._position = position
        self._coresong = coresong

        message = self._create_notification_message()
        self._label.props.label = message

        if self.type_ == PlaylistNotification.Type.PLAYLIST:
            self._coregrilo.stage_playlist_deletion(self._playlist)
        else:
            playlist.stage_song_deletion(self._coresong, position)

        self._timeout_id = GLib.timeout_add_seconds(5, self._finish_deletion)
        self._notifications_popup.add_notification(self)

    def _create_notification_message(self):
        if self.type_ == PlaylistNotification.Type.PLAYLIST:
            msg = _("Playlist {} removed".format(self._playlist.props.title))
        else:
            playlist_title = self._playlist.props.title
            song_title = self._coresong.props.title
            msg = _("{} removed from {}".format(
                song_title, playlist_title))

        return msg

    @Gtk.Template.Callback()
    def _undo_deletion(self, widget_):
        """Undo deletion and remove notification"""
        if self._timeout_id > 0:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = 0

        self._notifications_popup.remove_notification(self)
        if self.type_ == PlaylistNotification.Type.PLAYLIST:
            self._coregrilo.finish_playlist_deletion(self._playlist, False)
        else:
            self._playlist.undo_pending_song_deletion(
                self._coresong, self._position)

    @Gtk.Template.Callback()
    def _close_notification(self, widget_):
        if self._timeout_id > 0:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = 0

        self._finish_deletion()

    def _finish_deletion(self):
        self._notifications_popup.remove_notification(self)
        if self.type_ == PlaylistNotification.Type.PLAYLIST:
            self._coregrilo.finish_playlist_deletion(self._playlist, True)
        else:
            self._playlist.finish_song_deletion(self._coresong)
