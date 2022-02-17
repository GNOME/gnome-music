# Copyright 2021 The GNOME Music developers
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
from typing import Any, Optional, Union
import typing

from gi.repository import Gio, Gtk

from gnomemusic.grilowrappers.grltrackerplaylists import Playlist
from gnomemusic.widgets.notificationspopup import PlaylistNotification
from gnomemusic.widgets.playlistdialog import PlaylistDialog
from gnomemusic.widgets.songwidget import SongWidget
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.corealbum import CoreAlbum
    from gnomemusic.coresong import CoreSong


@Gtk.Template(resource_path="/org/gnome/Music/ui/SongWidgetMenu.ui")
class SongWidgetMenu(Gtk.PopoverMenu):

    __gtype_name__ = "SongWidgetMenu"

    def __init__(
            self, application: Application,
            song_widget: Union[SongWidget, Gtk.ListItem],
            coreobject: Union[CoreAlbum, CoreSong, Playlist]) -> None:
        """Menu to interact with the song of a SongWidget.

        :param Application application: The application object
        :param SongWidget song_widget: The songwidget associated with the menu
        :param Union[CoreAlbum, CoreSong, Playlist]  coreboject: The
            coreobject associated with the menu
        """
        super().__init__()

        self._application = application
        self._coremodel = application.props.coremodel
        self._player = application.props.player
        self._window = application.props.window

        self._coreobject = coreobject
        self._song_widget = song_widget

        if isinstance(song_widget, SongWidget):
            self._coresong = song_widget.props.coresong
        else:
            self._coresong = coreobject

        self._playlist_dialog: Optional[PlaylistDialog] = None

        action_group = Gio.SimpleActionGroup()
        action_entries = [
            ("play", self._play_song),
            ("add_playlist", self._add_to_playlist)
        ]
        if (isinstance(self._coreobject, Playlist)
                and not self._coreobject.props.is_smart):
            action_entries.append(
                ("remove_playlist", self._remove_from_playlist))
        elif not isinstance(self._coreobject, Playlist):
            self.props.menu_model.remove(2)

        for name, callback in action_entries:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            action_group.add_action(action)

        self.insert_action_group("songwidget", action_group)

    def _play_song(self, action: Gio.Simple, param: Any) -> None:
        self.popdown()
        signal_id = 0

        def _on_playlist_loaded(klass, playlist_type):
            self._player.play(self._coresong)
            self._coremodel.disconnect(signal_id)

        signal_id = self._coremodel.connect(
            "playlist-loaded", _on_playlist_loaded)
        self._coremodel.props.active_core_object = self._coreobject

    def _add_to_playlist(self, action: Gio.Simple, param: Any) -> None:

        def on_response(dialog: PlaylistDialog, response_id: int) -> None:
            if not self._playlist_dialog:
                return

            if response_id == Gtk.ResponseType.ACCEPT:
                playlist = self._playlist_dialog.props.selected_playlist
                playlist.add_songs([self._coresong])

            self._playlist_dialog.destroy()
            self._playlist_dialog = None

        self.popdown()
        self._playlist_dialog = PlaylistDialog(self._application)
        self._playlist_dialog.props.transient_for = self._window
        self._playlist_dialog.connect("response", on_response)
        self._playlist_dialog.present()

    def _remove_from_playlist(self, action: Gio.Simple, param: Any) -> None:
        self.popdown()
        position = self._song_widget.get_index()
        notification = PlaylistNotification(  # noqa: F841
            self._window.notifications_popup, self._application,
            PlaylistNotification.Type.SONG, self._coreobject, position,
            self._coresong)
