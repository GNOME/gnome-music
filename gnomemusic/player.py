# Copyright © 2018 The GNOME Music developers
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
from itertools import chain
from random import randint
import logging
import time

import gi
gi.require_version('Grl', '0.3')
gi.require_version('Gst', '1.0')
gi.require_version('GstAudio', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import GObject, Grl, GstPbutils
from gi._gi import pygobject_new_full

from gnomemusic import log
from gnomemusic.gstplayer import GstPlayer, Playback
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists
from gnomemusic.scrobbler import LastFmScrobbler
from gnomemusic.widgets.songwidget import SongWidget


logger = logging.getLogger(__name__)
playlists = Playlists.get_default()


class RepeatMode(IntEnum):
    """Enum for player repeat mode"""
    NONE = 0
    SONG = 1
    ALL = 2
    SHUFFLE = 3


class ValidationStatus(IntEnum):
    """Enum for song validation"""
    PENDING = 0
    IN_PROGRESS = 1
    FAILED = 2
    SUCCEEDED = 3


class PlayerField(IntEnum):
    """Enum for player model fields"""
    SONG = 0
    VALIDATION = 1


class PlayerPlaylist(GObject.GObject):
    """PlayerPlaylist object

    Contains the logic to validate a song, handle RepeatMode and the
    list of songs being played.
    """

    class Type(IntEnum):
        """Type of playlist."""
        SONGS = 0
        ALBUM = 1
        ARTIST = 2
        PLAYLIST = 3
        SEARCH_RESULT = 4

    __gsignals__ = {
        'song-validated': (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
    }

    _nb_songs_max = 10

    repeat_mode = GObject.Property(type=int, default=RepeatMode.NONE)

    def __repr__(self):
        return '<PlayerPlayList>'

    @log
    def __init__(self, application):
        super().__init__()

        GstPbutils.pb_utils_init()

        self._app = application
        self._songs = []
        self._shuffle_indexes = []
        self._position = 0

        self._type = -1
        self._id = -1

        # self._validation_indexes = None
        # self._discoverer = GstPbutils.Discoverer()
        # self._discoverer.connect('discovered', self._on_discovered)
        # self._discoverer.start()

        self._model = self._app._coremodel.props.playlist_sort

        self.connect("notify::repeat-mode", self._on_repeat_mode_changed)

    @log
    def set_playlist(self, playlist_type, playlist_id, model, model_iter=None):
        """Set a new playlist or change the song being played

        If no song is requested (through model_iter), a song will be
        automatically selected:
        * the first song in a linear mode
        * a random song in shuffle mode

        :param PlayerPlaylist.Type playlist_type: playlist type
        :param string playlist_id: unique identifer to recognize the playlist
        :param GtkListStore model: list of songs to play
        :param GtkTreeIter model_iter: requested song

        :return: True if the playlist has been updated. False otherwise
        :rtype: bool
        """
        pass

    @log
    def change_position(self, prev_pos, new_pos):
        """Change order of a song in the playlist

        :param int prev_pos: previous position
        :param int new_pos: new position
        :return: new index of the song being played. -1 if unchanged
        :rtype: int
        """
        pass

    @log
    def add_song(self, song, song_index):
        """Add a song to the playlist.

        :param Grl.Media song: new song
        :param int song_index: song position
        """
        pass

    @log
    def remove_song(self, song_index):
        """Remove a song from the playlist.

        :param int song_index: index of the song to remove
        """
        pass

    @log
    def has_next(self):
        """Test if there is a song after the current one.

        :return: True if there is a song. False otherwise.
        :rtype: bool
        """
        if (self.props.repeat_mode == RepeatMode.SONG
                or self.props.repeat_mode == RepeatMode.ALL
                or self.props.position < self._model.get_n_items() - 1):
            return True

        return False

    @log
    def has_previous(self):
        """Test if there is a song before the current one.

        :return: True if there is a song. False otherwise.
        :rtype: bool
        """
        if (self.props.repeat_mode == RepeatMode.SONG
                or self.props.repeat_mode == RepeatMode.ALL
                or (self.props.position <= self._model.get_n_items() - 1
                    and self.props.position > 0)):
            return True

        return False

    @log
    def next(self):
        """Go to the next song in the playlist.

        :return: True if the operation succeeded. False otherwise.
        :rtype: bool
        """
        if not self.has_next():
            return False

        if self.props.repeat_mode == RepeatMode.SONG:
            next_position = self.props.position
        elif (self.props.repeat_mode == RepeatMode.ALL
                and self.props.position == self._model.get_n_items() - 1):
            next_position = 0
        else:
            next_position = self.props.position + 1

        self._model[self.props.position].props.state = SongWidget.State.PLAYED
        self._model[next_position].props.state = SongWidget.State.PLAYING

        self._position = next_position

        return True

    @log
    def previous(self):
        """Go to the previous song in the playlist.

        :return: True if the operation succeeded. False otherwise.
        :rtype: bool
        """
        if not self.has_previous():
            return False

        if self.props.repeat_mode == RepeatMode.SONG:
            previous_position = self.props.position
        elif (self.props.repeat_mode == RepeatMode.ALL
                and self.props.position == 0):
            previous_position = self._model.get_n_items() - 1
        else:
            previous_position = self.props.position - 1

        self._model[self.props.position].props.state = SongWidget.State.PLAYED
        self._model[previous_position].props.state = SongWidget.State.PLAYING

        self._position = previous_position

        return True

    @GObject.Property(type=int, default=0, flags=GObject.ParamFlags.READABLE)
    def position(self):
        """Gets current song index.

        :returns: position of the current song in the playlist.
        :rtype: int
        """
        return self._position

    @GObject.Property(
        type=Grl.Media, default=None, flags=GObject.ParamFlags.READABLE)
    def current_song(self):
        """Get current song.

        :returns: the song being played or None if there are no songs
        :rtype: Grl.Media
        """
        n_items = self._model.get_n_items()
        if (n_items != 0
                and n_items > self._position):
            current_song = self._model[self._position]
            if current_song.props.state == SongWidget.State.PLAYING:
                return current_song.props.media

        for idx, coresong in enumerate(self._model):
            if coresong.props.state == SongWidget.State.PLAYING:
                print("position", idx)
                self._position = idx
                return coresong.props.media

        return None

    @log
    def _on_repeat_mode_changed(self, klass, param):

        def _wrap_list_store_sort_func(func):
            def wrap(a, b, *user_data):
                a = pygobject_new_full(a, False)
                b = pygobject_new_full(b, False)
                return func(a, b, *user_data)

            return wrap

        # FIXME: This shuffle is too simple.
        def _shuffle_sort(song_a, song_b):
            return randint(-1, 1)

        if self.props.repeat_mode == RepeatMode.SHUFFLE:
            self._model.set_sort_func(
                _wrap_list_store_sort_func(_shuffle_sort))
        elif self.props.repeat_mode == RepeatMode.NONE:
            self._model.set_sort_func(None)

    @GObject.Property(type=int, flags=GObject.ParamFlags.READABLE)
    def playlist_id(self):
        """Get playlist unique identifier.

        :returns: playlist id
        :rtype: int
        """
        return self._id

    @GObject.Property(type=int, flags=GObject.ParamFlags.READABLE)
    def playlist_type(self):
        """Get playlist type.

        :returns: playlist type
        :rtype: PlayerPlaylist.Type
        """
        return self._type

    @log
    def get_mpris_playlist(self):
        """Get recent and next songs from the current playlist.

        If the playlist is an album, return all songs.
        Returned songs are sorted according to the repeat mode.
        This method is used by mpris to expose a TrackList.

        :returns: current playlist
        :rtype: list of index and Grl.Media
        """
        return []
        if not self.props.current_song:
            return []

        songs = []
        nb_songs = len(self._songs)
        current_index = self._position
        if self.props.repeat_mode == RepeatMode.SHUFFLE:
            current_index = self._shuffle_indexes.index(self._position)

        index_min = current_index - self._nb_songs_max
        index_max = current_index + self._nb_songs_max + 1
        if self._type == PlayerPlaylist.Type.ALBUM:
            index_min = 0
            index_max = nb_songs

        first_index = max(index_min, 0)
        last_index = min(index_max, nb_songs)

        if self.props.repeat_mode == RepeatMode.SHUFFLE:
            indexes = self._shuffle_indexes[first_index:last_index]
        else:
            indexes = range(first_index, last_index)

        if (self.props.repeat_mode == RepeatMode.ALL
                and (last_index - first_index) < (2 * self._nb_songs_max + 1)):
            offset_sup = min(
                self._nb_songs_max - last_index + current_index + 1,
                first_index)
            offset_inf = min(
                self._nb_songs_max - current_index + first_index,
                nb_songs - last_index)

            indexes = chain(
                range(nb_songs - offset_inf, nb_songs), indexes,
                range(offset_sup))

        songs = [[index, self._songs[index][PlayerField.SONG]]
                 for index in indexes]
        return songs


class Player(GObject.GObject):
    """Main Player object

    Contains the logic of playing a song with Music.
    """

    __gsignals__ = {
        'playlist-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'seek-finished': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'song-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'song-validated': (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
    }

    state = GObject.Property(type=int, default=Playback.STOPPED)
    duration = GObject.Property(type=float, default=-1.)

    def __repr__(self):
        return '<Player>'

    @log
    def __init__(self, application):
        """Initialize the player

        :param Application application: Application object
        """
        super().__init__()

        self._app = application
        # In the case of gapless playback, both 'about-to-finish'
        # and 'eos' can occur during the same stream. 'about-to-finish'
        # already sets self._playlist to the next song, so doing it
        # again on eos would skip a song.
        # TODO: Improve playlist handling so this hack is no longer
        # needed.
        self._gapless_set = False

        self._playlist = PlayerPlaylist(self._app)
        self._playlist.connect('song-validated', self._on_song_validated)

        self._settings = application.props.settings
        self._settings.connect(
            'changed::repeat', self._on_repeat_setting_changed)

        self._repeat = self._settings.get_enum('repeat')
        self.bind_property(
            'repeat-mode', self._playlist, 'repeat-mode',
            GObject.BindingFlags.SYNC_CREATE)

        self._new_clock = True

        self._gst_player = GstPlayer(application)
        self._gst_player.connect("about-to-finish", self._on_about_to_finish)
        self._gst_player.connect('clock-tick', self._on_clock_tick)
        self._gst_player.connect('eos', self._on_eos)
        self._gst_player.connect('seek-finished', self._on_seek_finished)
        self._gst_player.connect("stream-start", self._on_stream_start)
        self._gst_player.bind_property(
            'duration', self, 'duration', GObject.BindingFlags.SYNC_CREATE)
        self._gst_player.bind_property(
            'state', self, 'state', GObject.BindingFlags.SYNC_CREATE)

        self._lastfm = LastFmScrobbler()

    @GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READABLE)
    def has_next(self):
        """Test if the playlist has a next song.

        :returns: True if the current song is not the last one.
        :rtype: bool
        """
        return self._playlist.has_next()

    @GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READABLE)
    def has_previous(self):
        """Test if the playlist has a previous song.

        :returns: True if the current song is not the first one.
        :rtype: bool
        """
        return self._playlist.has_previous()

    @GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READABLE)
    def playing(self):
        """Test if a song is currently played.

        :returns: True if a song is currently played.
        :rtype: bool
        """
        return self.props.state == Playback.PLAYING

    @log
    def _load(self, song):
        self._gst_player.props.state = Playback.LOADING
        self._time_stamp = int(time.time())

        self._gst_player.props.url = song.get_url()

    @log
    def _on_about_to_finish(self, klass):
        if self.props.has_next:
            self._playlist.next()

            new_url = self._playlist.props.current_song.get_url()
            self._gst_player.props.url = new_url
            self._gapless_set = True

    @log
    def _on_eos(self, klass):
        if self._gapless_set:
            # After 'eos' in the gapless case, the pipeline needs to be
            # hard reset.
            self.stop()
            self.play()
        else:
            self.stop()

        self._gapless_set = False

    def _on_stream_start(self, klass):
        self._gapless_set = False
        self._time_stamp = int(time.time())

        self.emit("song-changed")

    def _load2(self, song):
        self._gst_player.props.state = Playback.LOADING
        self._time_stamp = int(time.time())

        self._gst_player.props.url = song.get_url()
        print(song.get_url())

    @log
    def play(self, song_changed=True, song_offset=None, media=None):
        """Play a song.

        Load a new song or resume playback depending on song_changed
        value. If song_offset is defined, set a new song and play it.

        :param bool song_changed: indicate if a new song must be loaded
        :param int song_offset: position relative to current song
        """
        if self.props.current_song is None:
            return

        if media is None:
            media = self._playlist.props.current_song

        self._load2(media)

        self._gst_player.props.state = Playback.PLAYING
        return

        if (song_offset is not None
                and not self._playlist.set_song(song_offset)):
            return False

        if (song_changed
                or self._gapless_set):
            self._load(self._playlist.props.current_song)

        self._gst_player.props.state = Playback.PLAYING

    @log
    def pause(self):
        """Pause"""
        self._gst_player.props.state = Playback.PAUSED

    @log
    def stop(self):
        """Stop"""
        self._gst_player.props.state = Playback.STOPPED

    @log
    def next(self):
        """"Play next song

        Play the next song of the playlist, if any.
        """
        if self._playlist.next():
            self.play(None, None, self._playlist.props.current_song)

    @log
    def previous(self):
        """Play previous song

        Play the previous song of the playlist, if any.
        """
        position = self._gst_player.props.position
        if position >= 5:
            self.set_position(0.0)
            return

        if self._playlist.previous():
            self.play(None, None, self._playlist.props.current_song)

    @log
    def play_pause(self):
        """Toggle play/pause state"""
        if self.props.state == Playback.PLAYING:
            self.pause()
        else:
            self.play(False)

    @log
    def set_playlist(self, playlist_type, playlist_id, model, iter_=None):
        """Set a new playlist or change the song being played.

        :param PlayerPlaylist.Type playlist_type: playlist type
        :param string playlist_id: unique identifer to recognize the playlist
        :param GtkListStore model: list of songs to play
        :param GtkTreeIter model_iter: requested song
        """
        playlist_changed = self._playlist.set_playlist(
            playlist_type, playlist_id, model, iter_)

        if playlist_changed:
            self.emit('playlist-changed')

    @log
    def playlist_change_position(self, prev_pos, new_pos):
        """Change order of a song in the playlist.

        :param int prev_pos: previous position
        :param int new_pos: new position
        :return: new index of the song being played. -1 if unchanged
        :rtype: int
        """
        current_index = self._playlist.change_position(prev_pos, new_pos)
        if current_index >= 0:
            self.emit('playlist-changed')
        return current_index

    @log
    def remove_song(self, song_index):
        """Remove a song from the current playlist.

        :param int song_index: position of the song to remove
        """
        if self.props.position == song_index:
            if self.props.has_next:
                self.next()
            elif self.props.has_previous:
                self.previous()
            else:
                self.stop()
        self._playlist.remove_song(song_index)
        self.emit('playlist-changed')

    @log
    def add_song(self, song, song_index):
        """Add a song to the current playlist.

        :param int song_index: position of the song to add
        """
        self._playlist.add_song(song, song_index)
        self.emit('playlist-changed')

    @log
    def _on_song_validated(self, playlist, index, status):
        self.emit('song-validated', index, status)
        return True

    @log
    def playing_playlist(self, playlist_type, playlist_id):
        """Test if the current playlist matches type and id.

        :param PlayerPlaylist.Type playlist_type: playlist type
        :param string playlist_id: unique identifer to recognize the playlist
        :returns: True if these are the same playlists. False otherwise.
        :rtype: bool
        """
        if (playlist_type == self._playlist.props.playlist_type
                and playlist_id == self._playlist.props.playlist_id):
            return True
        return False

    @log
    def _on_clock_tick(self, klass, tick):
        logger.debug("Clock tick {}, player at {} seconds".format(
            tick, self._gst_player.props.position))

        current_song = self._playlist.props.current_song

        if tick == 0:
            self._new_clock = True
            self._lastfm.now_playing(current_song)

        if self.props.duration == -1.:
            return

        position = self._gst_player.props.position
        if position > 0:
            percentage = tick / self.props.duration
            if (not self._lastfm.scrobbled
                    and self.props.duration > 30.
                    and (percentage > 0.5 or tick > 4 * 60)):
                self._lastfm.scrobble(current_song, self._time_stamp)

            if (percentage > 0.5
                    and self._new_clock):
                self._new_clock = False
                # FIXME: we should not need to update smart
                # playlists here but removing it may introduce
                # a bug. So, we keep it for the time being.
                playlists.update_all_smart_playlists()
                grilo.bump_play_count(current_song)
                grilo.set_last_played(current_song)

    @log
    def _on_repeat_setting_changed(self, settings, value):
        self.props.repeat_mode = settings.get_enum('repeat')

    @GObject.Property(type=int, default=RepeatMode.NONE)
    def repeat_mode(self):
        return self._repeat

    @repeat_mode.setter
    def repeat_mode(self, mode):
        if mode == self._repeat:
            return

        self._repeat = mode
        self._settings.set_enum('repeat', mode)

    @GObject.Property(type=int, default=0, flags=GObject.ParamFlags.READABLE)
    def position(self):
        """Gets current song index.

        :returns: position of the current song in the playlist.
        :rtype: int
        """
        return self._playlist.props.position

    @GObject.Property(
        type=Grl.Media, default=None, flags=GObject.ParamFlags.READABLE)
    def current_song(self):
        """Get the current song.

        :returns: the song being played. None if there is no playlist.
        :rtype: Grl.Media
        """
        return self._playlist.props.current_song

    @log
    def get_playlist_type(self):
        """Playlist type getter

        :returns: Current playlist type. None if no playlist.
        :rtype: PlayerPlaylist.Type
        """
        return self._playlist.props.playlist_type

    @log
    def get_playlist_id(self):
        """Playlist id getter

        :returns: PlayerPlaylist identifier. None if no playlist.
        :rtype: int
        """
        return self._playlist.props.playlist_id

    @log
    def get_position(self):
        """Get player position.

        Player position in seconds.
        :returns: position
        :rtype: float
        """
        return self._gst_player.props.position

    # TODO: used by MPRIS
    @log
    def set_position(self, position_second):
        """Change GstPlayer position.

        If the position if negative, set it to zero.
        If the position if greater than song duration, do nothing
        :param float position_second: requested position in second
        """
        if position_second < 0.0:
            position_second = 0.0

        duration_second = self._gst_player.props.duration
        if position_second <= duration_second:
            self._gst_player.seek(position_second)

    @log
    def get_mpris_playlist(self):
        """Get recent and next songs from the current playlist.

        If the playlist is an album, return all songs.
        Returned songs are sorted according to the repeat mode.
        This method is used by mpris to expose a TrackList.

        :returns: current playlist
        :rtype: list of index and Grl.Media
        """
        return self._playlist.get_mpris_playlist()

    @log
    def _on_seek_finished(self, klass):
        # FIXME: Just a proxy
        self.emit('seek-finished')
