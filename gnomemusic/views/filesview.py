# Copyright 2022 The GNOME Music Developers
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
import typing

from gettext import gettext as _

from gi.repository import Gio, GObject, Gtk

from gnomemusic.coresong import CoreSong
from gnomemusic.widgets.songwidget import SongWidget
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


@Gtk.Template(resource_path="/org/gnome/Music/ui/FilesView.ui")
class FilesView(Gtk.ScrolledWindow):
    """Main view of all songs sorted artistwise

    Consists all songs along with songname, star, length, artist
    and the album name.
    """

    __gtype_name__ = "FilesView"

    icon_name = GObject.Property(
        type=str, default="folder-symbolic",
        flags=GObject.ParamFlags.READABLE)
    title = GObject.Property(
        type=str, default=_("Files"), flags=GObject.ParamFlags.READABLE)

    _list_box = Gtk.Template.Child()

    def __init__(self, application: Application):
        """Initialize

        :param GtkApplication window: The application object
        """
        super().__init__()

        self.props.name = "files"

        self._player = application.props.player

        self._coremodel = application.props.coremodel
        self._files_model = self._coremodel.props.files
        self._list_box.bind_model(self._files_model, self._create_widget)

        self._files_model.connect(
            "items-changed", self._on_files_model_items_changed)
        self._on_files_model_items_changed(self._files_model, 0, 0, 0)

    def _create_widget(self, coresong: CoreSong) -> SongWidget:
        song_widget = SongWidget(coresong, show_artist_and_album=True)
        song_widget.props.show_song_number = False
        return song_widget

    def _on_files_model_items_changed(
            self, model: Gio.ListStore, pos: int, removed: int,
            added: int) -> None:
        self.props.visible = model.get_n_items() > 0

    @Gtk.Template.Callback()
    def _song_activated(
            self, widget: Gtk.Widget, song_widget: SongWidget) -> None:
        signal_id = 0

        def _on_playlist_loaded(klass, playlist_type):
            self._player.play(song_widget.props.coresong)
            self._coremodel.disconnect(signal_id)

        signal_id = self._coremodel.connect(
            "playlist-loaded", _on_playlist_loaded)
        self._coremodel.props.active_core_object = song_widget.props.coresong
