# Copyright 2019 The GNOME Music developers
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

import math

import gi
gi.require_version("Gfm", "0.1")
from gi.repository import GObject, Gio, Gfm, Gtk

from gnomemusic.coreartist import CoreArtist
from gnomemusic.coresong import CoreSong
from gnomemusic.grilowrappers.grltrackerplaylists import Playlist
from gnomemusic.player import PlayerPlaylist
from gnomemusic.songliststore import SongListStore
from gnomemusic.widgets.songwidget import SongWidget
import gnomemusic.utils as utils


class CoreModel(GObject.GObject):
    """Provides all the list models used in Music

    Music is using a hierarchy of data objects with list models to
    contain the information about the users available music. This
    hierarchy is filled mainly through Grilo, with the exception of
    playlists which are a Tracker only feature.

    There are three main models: one for artist info, one for albums
    and one for songs. The data objects within these are CoreArtist,
    CoreAlbum and CoreSong respectively.

    The data objects contain filtered lists of the three main models.
    This makes the hierarchy as follows.

    CoreArtist -> CoreAlbum -> CoreDisc -> CoreSong

    Playlists are a Tracker only feature and do not use the three
    main models directly.

    GrlTrackerPlaylists -> Playlist -> CoreSong

    The Player playlist is a copy of the relevant playlist, built by
    using the components described above as needed.
    """

    __gsignals__ = {
        "playlist-loaded": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "smart-playlist-change": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    active_playlist = GObject.Property(type=Playlist, default=None)
    songs_available = GObject.Property(type=bool, default=False)

    _recent_size = 21

    def __init__(self, application):
        """Initiate the CoreModel object

        :param Application application: The Application instance to use
        """
        super().__init__()

        self._flatten_model = None
        self._player_signal_id = None
        self._current_playlist_model = None
        self._previous_playlist_model = None

        self._songs_model = Gio.ListStore.new(CoreSong)
        self._songliststore = SongListStore(self._songs_model)

        self._application = application

        self._albums_model = Gio.ListStore()
        self._albums_model_sort = Gfm.SortListModel.new(self._albums_model)
        self._albums_model_sort.set_sort_func(
            utils.wrap_list_store_sort_func(self._albums_sort))

        self._artists_model = Gio.ListStore.new(CoreArtist)
        self._artists_model_sort = Gfm.SortListModel.new(self._artists_model)
        self._artists_model_sort.set_sort_func(
            utils.wrap_list_store_sort_func(self._artist_sort))

        self._playlist_model = Gio.ListStore.new(CoreSong)
        self._playlist_model_sort = Gfm.SortListModel.new(self._playlist_model)
        self._playlist_model_recent = Gfm.SliceListModel.new(
            self._playlist_model_sort, 0, self._recent_size)

        self._songs_search_proxy = Gio.ListStore.new(Gfm.FilterListModel)
        self._songs_search_flatten = Gfm.FlattenListModel.new(CoreSong)
        self._songs_search_flatten.set_model(self._songs_search_proxy)

        self._albums_search_model = Gfm.FilterListModel.new(
            self._albums_model)
        self._albums_search_model.set_filter_func(lambda a: False)

        self._albums_search_filter = Gfm.FilterListModel.new(
            self._albums_search_model)

        self._artists_search_model = Gfm.FilterListModel.new(
            self._artists_model)
        self._artists_search_model.set_filter_func(lambda a: False)

        self._artists_search_filter = Gfm.FilterListModel.new(
            self._artists_search_model)

        self._playlists_model = Gio.ListStore.new(Playlist)
        self._playlists_model_filter = Gfm.FilterListModel.new(
            self._playlists_model)
        self._playlists_model_sort = Gfm.SortListModel.new(
            self._playlists_model_filter)
        self._playlists_model_sort.set_sort_func(
            utils.wrap_list_store_sort_func(self._playlists_sort))

        self._user_playlists_model_filter = Gfm.FilterListModel.new(
            self._playlists_model)
        self._user_playlists_model_sort = Gfm.SortListModel.new(
            self._user_playlists_model_filter)
        self._user_playlists_model_sort.set_sort_func(
            utils.wrap_list_store_sort_func(self._playlists_sort))

        self._songs_model.connect(
            "items-changed", self._on_songs_items_changed)

    def _on_songs_items_changed(self, model, position, removed, added):
        available = self.props.songs_available
        now_available = model.get_n_items() > 0

        if available == now_available:
            return

        if model.get_n_items() > 0:
            self.props.songs_available = True
        else:
            self.props.songs_available = False

    def _filter_selected(self, coresong):
        return coresong.props.selected

    def _albums_sort(self, album_a, album_b):
        return utils.natural_sort_names(
            album_a.props.title, album_b.props.title)

    def _artist_sort(self, artist_a, artist_b):
        return utils.natural_sort_names(
            artist_a.props.artist, artist_b.props.artist)

    def _playlists_sort(self, playlist_a, playlist_b):
        if playlist_a.props.is_smart:
            if not playlist_b.props.is_smart:
                return -1
            return utils.natural_sort_names(
                playlist_a.props.title, playlist_b.props.title)

        if playlist_b.props.is_smart:
            return 1

        # cannot use GLib.DateTime.compare
        # https://gitlab.gnome.org/GNOME/pygobject/issues/334
        # newest first
        date_diff = playlist_b.props.creation_date.difference(
            playlist_a.props.creation_date)
        return math.copysign(1, date_diff)

    def set_player_model(self, playlist_type, model):
        """Set the model for PlayerPlaylist to use

        This fills playlist model based on the playlist type and model
        given. This builds a separate model to stay alive and play
        while the user navigates other views.

        :param PlaylistType playlist_type: The type of the playlist
        :param Gio.ListStore model: The base model for the player model
        """
        if model is self._previous_playlist_model:
            for song in self._playlist_model:
                if song.props.state == SongWidget.State.PLAYING:
                    song.props.state = SongWidget.State.PLAYED

            self.emit("playlist-loaded", playlist_type)
            return

        def _bind_song_properties(model_song, player_song):
            model_song.bind_property(
                "state", player_song, "state",
                GObject.BindingFlags.BIDIRECTIONAL
                | GObject.BindingFlags.SYNC_CREATE)

        def _on_items_changed(model, position, removed, added):
            songs_list = []
            if added > 0:
                for i in list(range(added)):
                    coresong = model[position + i]
                    song = CoreSong(self._application, coresong.props.media)
                    _bind_song_properties(coresong, song)
                    songs_list.append(song)

            self._playlist_model.splice(position, removed, songs_list)

        played_states = [SongWidget.State.PLAYING, SongWidget.State.PLAYED]
        for song in self._playlist_model:
            if song.props.state in played_states:
                song.props.state = SongWidget.State.UNPLAYED

        if self._player_signal_id is not None:
            self._current_playlist_model.disconnect(self._player_signal_id)
            self._player_signal_id = None
            self._current_playlist_model = None

        if (playlist_type != PlayerPlaylist.Type.PLAYLIST
                and self.props.active_playlist is not None):
            self.props.active_playlist = None

        songs_added = []

        if playlist_type == PlayerPlaylist.Type.ALBUM:
            proxy_model = Gio.ListStore.new(Gio.ListModel)

            for disc in model:
                proxy_model.append(disc.props.model)

            self._flatten_model = Gfm.FlattenListModel.new(
                CoreSong, proxy_model)
            self._current_playlist_model = self._flatten_model

            for model_song in self._flatten_model:
                song = CoreSong(self._application, model_song.props.media)
                _bind_song_properties(model_song, song)
                songs_added.append(song)

        elif playlist_type == PlayerPlaylist.Type.ARTIST:
            proxy_model = Gio.ListStore.new(Gio.ListModel)

            for artist_album in model:
                for disc in artist_album.model:
                    proxy_model.append(disc.props.model)

            self._flatten_model = Gfm.FlattenListModel.new(
                CoreSong, proxy_model)
            self._current_playlist_model = self._flatten_model

            for model_song in self._flatten_model:
                song = CoreSong(self._application, model_song.props.media)
                _bind_song_properties(model_song, song)
                songs_added.append(song)

        elif playlist_type == PlayerPlaylist.Type.SONGS:
            self._current_playlist_model = self._songliststore.props.model

            for song in self._songliststore.props.model:
                songs_added.append(song)

                if song.props.state == SongWidget.State.PLAYING:
                    song.props.state = SongWidget.State.PLAYED

        elif playlist_type == PlayerPlaylist.Type.SEARCH_RESULT:
            self._current_playlist_model = self._songs_search_flatten

            for song in self._songs_search_flatten:
                songs_added.append(song)

        elif playlist_type == PlayerPlaylist.Type.PLAYLIST:
            self._current_playlist_model = model

            for model_song in model:
                song = CoreSong(self._application, model_song.props.media)
                _bind_song_properties(model_song, song)
                songs_added.append(song)

        self._playlist_model.splice(
            0, self._playlist_model.get_n_items(), songs_added)

        if self._current_playlist_model is not None:
            self._player_signal_id = self._current_playlist_model.connect(
                "items-changed", _on_items_changed)
        self._previous_playlist_model = model

        self.emit("playlist-loaded", playlist_type)

    @GObject.Property(
        type=Gio.ListStore, default=None, flags=GObject.ParamFlags.READABLE)
    def songs(self):
        return self._songs_model

    @GObject.Property(
        type=Gio.ListStore, default=None, flags=GObject.ParamFlags.READABLE)
    def albums(self):
        return self._albums_model

    @GObject.Property(
        type=Gio.ListStore, default=None, flags=GObject.ParamFlags.READABLE)
    def artists(self):
        return self._artists_model

    @GObject.Property(
        type=Gio.ListStore, default=None, flags=GObject.ParamFlags.READABLE)
    def playlist(self):
        return self._playlist_model

    @GObject.Property(
        type=Gfm.SortListModel, default=None,
        flags=GObject.ParamFlags.READABLE)
    def albums_sort(self):
        return self._albums_model_sort

    @GObject.Property(
        type=Gfm.SortListModel, default=None,
        flags=GObject.ParamFlags.READABLE)
    def artists_sort(self):
        return self._artists_model_sort

    @GObject.Property(
        type=Gfm.SortListModel, default=None,
        flags=GObject.ParamFlags.READABLE)
    def playlist_sort(self):
        return self._playlist_model_sort

    @GObject.Property(
        type=Gfm.SliceListModel, default=None,
        flags=GObject.ParamFlags.READABLE)
    def recent_playlist(self):
        return self._playlist_model_recent

    @GObject.Property(
        type=int, default=None,
        flags=GObject.ParamFlags.READABLE)
    def recent_playlist_size(self):
        return self._recent_size // 2

    @GObject.Property(
        type=Gfm.FilterListModel, default=None,
        flags=GObject.ParamFlags.READABLE)
    def songs_search(self):
        return self._songs_search_flatten

    @GObject.Property(
        type=Gio.ListStore, default=None,
        flags=GObject.ParamFlags.READABLE)
    def songs_search_proxy(self):
        return self._songs_search_proxy

    @GObject.Property(
        type=Gfm.FilterListModel, default=None,
        flags=GObject.ParamFlags.READABLE)
    def albums_search(self):
        return self._albums_search_model

    @GObject.Property(
        type=Gfm.FilterListModel, default=None,
        flags=GObject.ParamFlags.READABLE)
    def albums_search_filter(self):
        return self._albums_search_filter

    @GObject.Property(
        type=Gfm.FilterListModel, default=None,
        flags=GObject.ParamFlags.READABLE)
    def artists_search(self):
        return self._artists_search_model

    @GObject.Property(
        type=Gfm.FilterListModel, default=None,
        flags=GObject.ParamFlags.READABLE)
    def artists_search_filter(self):
        return self._artists_search_filter

    @GObject.Property(
        type=Gtk.ListStore, default=None, flags=GObject.ParamFlags.READABLE)
    def songs_gtkliststore(self):
        return self._songliststore

    @GObject.Property(
        type=Gio.ListStore, default=None, flags=GObject.ParamFlags.READABLE)
    def playlists(self):
        return self._playlists_model

    @GObject.Property(
        type=Gfm.SortListModel, default=None,
        flags=GObject.ParamFlags.READABLE)
    def playlists_sort(self):
        return self._playlists_model_sort

    @GObject.Property(
        type=Gfm.SortListModel, default=None,
        flags=GObject.ParamFlags.READABLE)
    def playlists_filter(self):
        return self._playlists_model_filter

    @GObject.Property(
        type=Gfm.SortListModel, default=None,
        flags=GObject.ParamFlags.READABLE)
    def user_playlists_sort(self):
        return self._user_playlists_model_sort

    @GObject.Property(
        type=Gfm.SortListModel, default=None,
        flags=GObject.ParamFlags.READABLE)
    def user_playlists_filter(self):
        return self._user_playlists_model_filter
