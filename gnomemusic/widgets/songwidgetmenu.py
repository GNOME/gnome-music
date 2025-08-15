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
from typing import Any, Optional, Union, cast
import typing

from gettext import gettext as _
from gi.repository import Gio, GObject, Gtk

from gnomemusic.grilowrappers.playlist import Playlist
from gnomemusic.songtoast import SongToast
from gnomemusic.widgets.playlistdialog import PlaylistDialog
from gnomemusic.widgets.songwidget import SongWidget
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.corealbum import CoreAlbum
    from gnomemusic.coremodel import CoreModel
    from gnomemusic.coresong import CoreSong
    from gnomemusic.queue import Queue
    CoreObject = Union[CoreAlbum, CoreSong, Playlist]


@Gtk.Template(resource_path="/org/gnome/Music/ui/SongWidgetMenu.ui")
class SongWidgetMenu(Gtk.PopoverMenu):

    __gtype_name__ = "SongWidgetMenu"

    def __init__(
            self, application: Application,
            song_widget: Union[SongWidget, Gtk.ListItem],
            coreobject: Optional[CoreObject]) -> None:
        """Menu to interact with the song of a SongWidget.

        :param Application application: The application object
        :param SongWidget song_widget: The songwidget associated with the menu
        :param Union[CoreAlbum, CoreSong, Playlist] coreobject: The
            coreobject associated with the menu
        """
        super().__init__()

        self._application = application
        self._coremodel = application.props.coremodel
        self._player = application.props.player
        self._window = application.props.window

        self._coreobject = coreobject
        self._coresong: CoreSong
        self._song_widget = song_widget
        self.props.coreobject = coreobject

        self._playlist_dialog: Optional[PlaylistDialog] = None

        action_group = Gio.SimpleActionGroup()
        action_entries = [
            ("play", self._play_song),
            ("add_playlist", self._add_to_playlist),
            ("open_location", self._open_location)
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

        open_menu_item = Gio.MenuItem.new(  # noqa: F841
            _("_Open Location"), "songwidget.open_location")

    def _open_location(self, action: Gio.SimpleAction, param: Any) -> None:
        pass

    def _play_song(self, action: Gio.Simple, param: Any) -> None:
        self.popdown()
        signal_id = 0

        def _on_queue_loaded(
                coremodel: CoreModel, queue_type: Queue.Type) -> None:
            self._player.play(self._coresong)
            self._coremodel.disconnect(signal_id)

        signal_id = self._coremodel.connect(
            "queue-loaded", _on_queue_loaded)
        self._coremodel.props.active_core_object = self._coreobject

    def _add_to_playlist(self, action: Gio.Simple, param: Any) -> None:
        self.popdown()
        self._playlist_dialog = PlaylistDialog(
            self._application, [self._coresong])
        self._playlist_dialog.present(self._window)

    def _remove_from_playlist(self, action: Gio.Simple, param: Any) -> None:
        self.popdown()
        position = self._song_widget.get_index()
        SongToast(
            self._application, cast(Playlist, self._coreobject), position,
            self._coresong)

    @GObject.Property(type=GObject.GObject)
    def coreobject(self) -> CoreObject:
        return self._coreobject

    @coreobject.setter  # type: ignore
    def coreobject(self, coreobject: CoreObject) -> None:
        self._coreobject = coreobject

        if isinstance(self._song_widget, SongWidget):
            self._coresong = self._song_widget.props.coresong
        else:
            self._coresong = coreobject
