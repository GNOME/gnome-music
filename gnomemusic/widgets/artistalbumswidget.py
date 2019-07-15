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

import logging

from gi.repository import GObject, Gtk

from gnomemusic import log
from gnomemusic.player import PlayerPlaylist
from gnomemusic.widgets.artistalbumwidget import ArtistAlbumWidget

logger = logging.getLogger(__name__)


class ArtistAlbumsWidget(Gtk.ListBox):
    """Widget containing all albums by an artist

    A vertical list of ArtistAlbumWidget, containing all the albums
    by one artist. Contains the model for all the song widgets of
    the album(s).
    """

    __gtype_name__ = 'ArtistAlbumsWidget'

    selected_items_count = GObject.Property(type=int, default=0, minimum=0)
    selection_mode = GObject.Property(type=bool, default=False)

    __gsignals__ = {
        "ready": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __repr__(self):
        return '<ArtistAlbumsWidget>'

    @log
    def __init__(
            self, coreartist, player, window, selection_mode_allowed=False):
        super().__init__()
        self._artist = coreartist.props.artist
        self._model = coreartist.props.model
        self._player = player
        self._selection_mode_allowed = selection_mode_allowed
        self._window = window

        self._widgets = []

        self._cover_size_group = Gtk.SizeGroup.new(
            Gtk.SizeGroupMode.HORIZONTAL)
        self._songs_grid_size_group = Gtk.SizeGroup.new(
            Gtk.SizeGroupMode.HORIZONTAL)

        self._nb_albums_loaded = 0
        self._model.props.model.connect_after(
            "items-changed", self. _on_model_items_changed)
        self.bind_model(self._model, self._add_album)

        self.get_style_context().add_class("artist-albums-widget")
        self.show_all()

    def _song_activated(self, widget, song_widget):
        self._album = None

        if self.props.selection_mode:
            return

        coremodel = self._player._app.props.coremodel

        def _on_playlist_loaded(artistalbumwidget):
            self._player.play(song_widget.props.coresong)
            coremodel.disconnect(signal_id)

        signal_id = coremodel.connect("playlist-loaded", _on_playlist_loaded)
        coremodel.set_playlist_model(PlayerPlaylist.Type.ARTIST, self._model)

    def _add_album(self, corealbum):
        widget = ArtistAlbumWidget(
            corealbum, self._selection_mode_allowed,
            self._songs_grid_size_group, self._cover_size_group, self._window)

        self.bind_property(
            'selection-mode', widget, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        self._widgets.append(widget)
        widget.connect("ready", self._on_album_ready)
        widget.connect("song-activated", self._song_activated)

        return widget

    def _on_album_ready(self, artistalbumwidget):
        self._nb_albums_loaded += 1
        if self._nb_albums_loaded == self._model.get_n_items():
            artistalbumwidget.disconnect_by_func(self._on_album_ready)
            self._nb_albums_loaded = 0
            self.emit("ready")

    def _on_model_items_changed(self, model, position, removed, added):
        for i in range(model.get_n_items()):
            row = self.get_row_at_index(i)
            row.props.selectable = False

    @log
    def select_all(self):
        """Select all items"""
        for widget in self._widgets:
            widget.select_all()

    @log
    def select_none(self):
        """Deselect all items"""
        for widget in self._widgets:
            widget.select_none()

    @GObject.Property(type=str, flags=GObject.ParamFlags.READABLE)
    def artist(self):
        """Artist name"""
        return self._artist

    @log
    def get_selected_songs(self):
        """Return a list of selected songs.

        :returns: selected songs
        :rtype: list
        """
        songs = []
        for widget in self._widgets:
            songs += widget.get_selected_songs()
        return songs
