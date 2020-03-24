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

from gi.repository import GObject, Gtk

from gnomemusic.player import PlayerPlaylist
from gnomemusic.widgets.artistalbumwidget import ArtistAlbumWidget


class ArtistAlbumsWidget(Gtk.ListBox):
    """Widget containing all albums by an artist

    A vertical list of ArtistAlbumWidget, containing all the albums
    by one artist. Contains the model for all the song widgets of
    the album(s).
    """

    __gtype_name__ = 'ArtistAlbumsWidget'

    selection_mode = GObject.Property(type=bool, default=False)

    def __init__(self, coreartist, application):
        super().__init__()

        self._application = application
        self._artist = coreartist.props.artist
        self._model = coreartist.props.model
        self._player = self._application.props.player

        self._cover_size_group = Gtk.SizeGroup.new(
            Gtk.SizeGroupMode.HORIZONTAL)
        self._songs_grid_size_group = Gtk.SizeGroup.new(
            Gtk.SizeGroupMode.HORIZONTAL)

        self.bind_model(self._model, self._add_album)

        self.get_style_context().add_class("artist-albums-widget")
        self.show_all()

    def _song_activated(self, widget, song_widget):
        self._album = None

        if self.props.selection_mode:
            return

        coremodel = self._application.props.coremodel

        def _on_playlist_loaded(klass, playlist_type):
            self._player.play(song_widget.props.coresong)
            coremodel.disconnect(signal_id)

        signal_id = coremodel.connect("playlist-loaded", _on_playlist_loaded)
        coremodel.set_player_model(PlayerPlaylist.Type.ARTIST, self._model)

    def _add_album(self, corealbum):
        row = Gtk.ListBoxRow()
        row.props.selectable = False
        row.props.activatable = False

        widget = ArtistAlbumWidget(
            corealbum, self._songs_grid_size_group, self._cover_size_group)

        self.bind_property(
            'selection-mode', widget, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        row.add(widget)
        widget.connect("song-activated", self._song_activated)

        return row

    def select_all(self):
        """Select all items"""
        def toggle_selection(row):
            row.get_child().select_all()

        self.foreach(toggle_selection)

    def deselect_all(self):
        """Deselect all items"""
        def toggle_selection(row):
            row.get_child().deselect_all()

        self.foreach(toggle_selection)

    @GObject.Property(type=str, flags=GObject.ParamFlags.READABLE)
    def artist(self):
        """Artist name"""
        return self._artist
