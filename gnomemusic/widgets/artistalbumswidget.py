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
from gnomemusic.widgets.songwidget import SongWidget

logger = logging.getLogger(__name__)


@Gtk.Template(resource_path='/org/gnome/Music/ui/ArtistAlbumsWidget.ui')
class ArtistAlbumsWidget(Gtk.Box):
    """Widget containing all albums by an artist

    A vertical list of ArtistAlbumWidget, containing all the albums
    by one artist. Contains the model for all the song widgets of
    the album(s).
    """

    __gtype_name__ = 'ArtistAlbumsWidget'

    _artist_label = Gtk.Template.Child()

    selected_items_count = GObject.Property(type=int, default=0, minimum=0)
    selection_mode = GObject.Property(type=bool, default=False)

    def __repr__(self):
        return '<ArtistAlbumsWidget>'

    @log
    def __init__(
            self, coreartist, player, window, selection_mode_allowed=False):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._artist = coreartist.props.artist
        self._model = coreartist.props.model
        self._player = player
        self._selection_mode_allowed = selection_mode_allowed
        self._window = window

        self._artist_label.props.label = self._artist

        self._widgets = []

        hbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._album_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                  spacing=48)
        hbox.pack_start(self._album_box, False, False, 16)

        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_policy(Gtk.PolicyType.NEVER,
                                         Gtk.PolicyType.AUTOMATIC)
        self._scrolled_window.add(hbox)
        self.pack_start(self._scrolled_window, True, True, 0)

        self._cover_size_group = Gtk.SizeGroup.new(
            Gtk.SizeGroupMode.HORIZONTAL)
        self._songs_grid_size_group = Gtk.SizeGroup.new(
            Gtk.SizeGroupMode.HORIZONTAL)

        # FIXME: Make this a ListBox as well.
        for album in self._model:
            self._add_album(album)

        self.show_all()

    def _song_activated(self, widget, song_widget):
        if self.props.selection_mode:
            return

        self._album = None
        def _on_playlist_loaded(klass):
            self._player.play(None, None, song_widget._media)
            self._player._app._coremodel.disconnect(signal_id)

        signal_id = self._player._app._coremodel.connect(
            "playlist-loaded", _on_playlist_loaded)
        self._player._app._coremodel.set_playlist_model(
            PlayerPlaylist.Type.ARTIST, self._album, song_widget._media,
            self._model)

    def _add_album(self, corealbum):
        widget = ArtistAlbumWidget(
            corealbum, self._selection_mode_allowed,
            self._songs_grid_size_group, self._cover_size_group, self._window)

        self.bind_property(
            'selection-mode', widget, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        self._album_box.pack_start(widget, False, False, 0)
        self._widgets.append(widget)

        widget.connect("song-activated", self._song_activated)

    @log
    def _model_row_changed(self, model, path, itr):
        if not self.props.selection_mode:
            return

        selected_items = 0
        for row in model:
            if row[6]:
                selected_items += 1

        self.props.selected_items_count = selected_items

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
