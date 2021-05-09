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
from typing import Union
import typing

from gi.repository import Gtk

from gnomemusic.grilowrappers.grltrackerplaylists import Playlist
from gnomemusic.widgets.notificationspopup import PlaylistNotification
from gnomemusic.widgets.playlistdialog import PlaylistDialog
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.corealbum import CoreAlbum
    from gnomemusic.widgets.songwidget import SongWidget


@Gtk.Template(resource_path="/org/gnome/Music/ui/SongWidgetMenu.ui")
class SongWidgetMenu(Gtk.PopoverMenu):

    __gtype_name__ = "SongWidgetMenu"

    _remove_from_playlist_button = Gtk.Template.Child()

    def __init__(
            self, application: Application, song_widget: SongWidget,
            coreobject: Union[CoreAlbum, Playlist]) -> None:
        """Menu to interact with the song of a SongWidget.

        :param Application application: The application object
        :param SongWidget song_widget: The songwidget associated with the menu
        :param Union[CoreAlbum, Playlist]  coreboject: The coreobject
            associated with the menu
        """
        super().__init__()

        self._application = application
        self._coremodel = application.props.coremodel
        self._player = application.props.player
        self._window = application.props.window

        self._coreobject = coreobject
        self._song_widget = song_widget
        self._coresong = song_widget.props.coresong

        if isinstance(self._coreobject, Playlist):
            self._remove_from_playlist_button.props.visible = True
            self._remove_from_playlist_button.props.sensitive = (
                not self._coreobject.props.is_smart)
        else:
            self._remove_from_playlist_button.props.visible = False

    @Gtk.Template.Callback()
    def _on_play_clicked(self, widget: Gtk.Button) -> None:
        self.popdown()
        signal_id = 0

        def _on_playlist_loaded(klass, playlist_type):
            self._player.play(self._coresong)
            self._coremodel.disconnect(signal_id)

        signal_id = self._coremodel.connect(
            "playlist-loaded", _on_playlist_loaded)
        self._coremodel.props.active_core_object = self._coreobject

    @Gtk.Template.Callback()
    def _on_add_to_playlist_clicked(self, widget: Gtk.Button) -> None:
        self.popdown()
        playlist_dialog = PlaylistDialog(self._application)
        playlist_dialog.props.transient_for = self._window
        if playlist_dialog.run() == Gtk.ResponseType.ACCEPT:
            playlist = playlist_dialog.props.selected_playlist
            playlist.add_songs([self._coresong])

        playlist_dialog.destroy()

    @Gtk.Template.Callback()
    def _on_remove_from_playlist_clicked(self, widget: Gtk.Button) -> None:
        self.popdown()
        position = self._song_widget.get_index()
        notification = PlaylistNotification(  # noqa: F841
            self._window.notifications_popup, self._application,
            PlaylistNotification.Type.SONG, self._coreobject, position,
            self._coresong)
