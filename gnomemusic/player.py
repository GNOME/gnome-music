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
from random import randrange
import time

import gi
gi.require_version('GstPbutils', '1.0')
from gi.repository import GObject, GstPbutils

from gnomemusic.coresong import CoreSong
from gnomemusic.gstplayer import GstPlayer, Playback
from gnomemusic.widgets.songwidget import SongWidget
import gnomemusic.utils as utils


class RepeatMode(IntEnum):
    """Enum for player repeat mode"""
    NONE = 0
    SONG = 1
    ALL = 2
    SHUFFLE = 3


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

    repeat_mode = GObject.Property(type=int, default=RepeatMode.NONE)

    def __init__(self, application):
        super().__init__()

        GstPbutils.pb_utils_init()

        self._app = application
        self._log = application.props.log
        self._position = 0

        self._validation_songs = {}
        self._discoverer = GstPbutils.Discoverer()
        self._discoverer.connect("discovered", self._on_discovered)
        self._discoverer.start()

        self._playlist_model = self._app.props.coremodel.props.playlist
        self._model = self._app.props.coremodel.props.playlist_sort

        self.connect("notify::repeat-mode", self._on_repeat_mode_changed)
        self._playlist_model.connect("items-changed", self._on_items_changed)
        self._on_items_changed_sentinel = 0

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

    def get_next(self):
        """Get the next song in the playlist.

        :return: The next CoreSong or None.
        :rtype: CoreSong
        """
        if not self.has_next():
            return None

        if self.props.repeat_mode == RepeatMode.SONG:
            next_position = self.props.position
        elif (self.props.repeat_mode == RepeatMode.ALL
                and self.props.position == self._model.get_n_items() - 1):
            next_position = 0
        else:
            next_position = self.props.position + 1

        return self._model[next_position]

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
        self._position = next_position

        next_song = self._model[next_position]
        if next_song.props.validation == CoreSong.Validation.FAILED:
            return self.next()

        next_song.props.state = SongWidget.State.PLAYING
        self._validate_next_song()
        return True

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
        self._position = previous_position

        previous_song = self._model[previous_position]
        if previous_song.props.validation == CoreSong.Validation.FAILED:
            return self.previous()

        self._model[previous_position].props.state = SongWidget.State.PLAYING
        self._validate_previous_song()
        return True

    @GObject.Property(type=int, default=0, flags=GObject.ParamFlags.READABLE)
    def position(self):
        """Gets current song index.

        :returns: position of the current song in the playlist.
        :rtype: int
        """
        return self._position

    @GObject.Property(
        type=CoreSong, default=None, flags=GObject.ParamFlags.READABLE)
    def current_song(self):
        """Get current song.

        :returns: the song being played or None if there are no songs
        :rtype: CoreSong
        """
        n_items = self._model.get_n_items()
        if (n_items != 0
                and n_items > self._position):
            current_song = self._model[self._position]
            if current_song.props.state == SongWidget.State.PLAYING:
                return current_song

        for idx, coresong in enumerate(self._model):
            if coresong.props.state == SongWidget.State.PLAYING:
                self._position = idx
                return coresong

        return None

    def set_song(self, song):
        """Sets current song.

        If no song is provided, a song is automatically selected.

        :param CoreSong song: song to set
        :returns: The selected song
        :rtype: CoreSong
        """
        if self._model.get_n_items() == 0:
            return None

        if song is None:
            if self.props.repeat_mode == RepeatMode.SHUFFLE:
                position = randrange(0, self._model.get_n_items())
            else:
                position = 0
            song = self._model.get_item(position)
            song.props.state = SongWidget.State.PLAYING
            self._position = position
            self._validate_song(song)
            self._validate_next_song()
            return song

        for idx, coresong in enumerate(self._model):
            if coresong == song:
                coresong.props.state = SongWidget.State.PLAYING
                self._position = idx
                self._validate_song(song)
                self._validate_next_song()
                return song

        return None

    def _on_items_changed(self, model, pos, removed, added):
        if self.props.repeat_mode == RepeatMode.SHUFFLE:
            if (self._on_items_changed_sentinel == 0
                    and self._playlist_model.get_n_items()):
                self._shuffle_playlist()
            else:
                self._on_items_changed_sentinel = 0

    def _shuffle_playlist(self):
        song_list = []
        self._on_items_changed_sentinel = 1

        def _fisher_yates_shuffle(song_list):
            for n in range(len(song_list) - 1, 0, -1):
                rand_idx = randrange(n + 1)
                song_list[n], song_list[rand_idx] = \
                    song_list[rand_idx], song_list[n]

        for coresong in self._model:
            song_list.append(coresong)
        _fisher_yates_shuffle(song_list)
        self._playlist_model.splice(0, self._model.get_n_items(), song_list)

    def _on_repeat_mode_changed(self, klass, param):
        def _wrap_liststore_sort_func(func):
            def wrap(a, b, *user_data):
                return func(a.props.title, b.props.title, *user_data)
            return wrap

        if self.props.repeat_mode == RepeatMode.SHUFFLE:
            if (self._on_items_changed_sentinel == 0
                    and self._playlist_model.get_n_items()):
                self._shuffle_playlist()
            else:
                self._on_items_changed_sentinel = 0

        elif self.props.repeat_mode in [RepeatMode.NONE, RepeatMode.ALL]:
            self._playlist_model.sort(
                _wrap_liststore_sort_func(utils.natural_sort_names))

    def _validate_song(self, coresong):
        # Song is being processed or has already been processed.
        # Nothing to do.
        if coresong.props.validation > CoreSong.Validation.PENDING:
            return

        url = coresong.props.url
        if not url:
            self._log.warning(
                "The item {} doesn't have a URL set.".format(coresong))
            return
        if not url.startswith("file://"):
            self._log.debug(
                "Skipping validation of {} as not a local file".format(url))
            return

        coresong.props.validation = CoreSong.Validation.IN_PROGRESS
        self._validation_songs[url] = coresong
        self._discoverer.discover_uri_async(url)

    def _validate_next_song(self):
        if self.props.repeat_mode == RepeatMode.SONG:
            return

        current_position = self.props.position
        next_position = current_position + 1
        if next_position == self._model.get_n_items():
            if self.props.repeat_mode != RepeatMode.ALL:
                return
            next_position = 0

        self._validate_song(self._model[next_position])

    def _validate_previous_song(self):
        if self.props.repeat_mode == RepeatMode.SONG:
            return

        current_position = self.props.position
        previous_position = current_position - 1
        if previous_position < 0:
            if self.props.repeat_mode != RepeatMode.ALL:
                return
            previous_position = self._model.get_n_items() - 1

        self._validate_song(self._model[previous_position])

    def _on_discovered(self, discoverer, info, error):
        url = info.get_uri()
        coresong = self._validation_songs[url]

        if error:
            self._log.warning("Info {}: error: {}".format(info, error))
            coresong.props.validation = CoreSong.Validation.FAILED
        else:
            coresong.props.validation = CoreSong.Validation.SUCCEEDED


class Player(GObject.GObject):
    """Main Player object

    Contains the logic of playing a song with Music.
    """

    __gsignals__ = {
        'seek-finished': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'song-changed': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    state = GObject.Property(type=int, default=Playback.STOPPED)
    duration = GObject.Property(type=float, default=-1.)

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
        self._log = application.props.log
        self._playlist = PlayerPlaylist(self._app)

        self._playlist_model = self._app.props.coremodel.props.playlist_sort
        self._playlist_model.connect(
            "items-changed", self._on_playlist_model_items_changed)

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
        self._gst_player.connect("error", self._on_error)
        self._gst_player.connect('seek-finished', self._on_seek_finished)
        self._gst_player.connect("stream-start", self._on_stream_start)
        self._gst_player.bind_property(
            'duration', self, 'duration', GObject.BindingFlags.SYNC_CREATE)
        self._gst_player.bind_property(
            'state', self, 'state', GObject.BindingFlags.SYNC_CREATE)

        self._lastfm = application.props.lastfm_scrobbler

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

    def _on_playlist_model_items_changed(self, model, pos, removed, added):
        if (removed > 0
                and model.get_n_items() == 0):
            self.stop()

    def _on_about_to_finish(self, klass):
        if self.props.has_next:
            next_coresong = self._playlist.get_next()
            new_url = next_coresong.props.url
            self._gst_player.props.url = new_url
            self._gapless_set = True

    def _on_eos(self, klass):
        self._playlist.next()

        if self._gapless_set:
            # After 'eos' in the gapless case, the pipeline needs to be
            # hard reset.
            self.stop()
            self.play(self.props.current_song)
        else:
            self.stop()

        self._gapless_set = False

    def _on_error(self, klass=None):
        self.stop()
        self._gapless_set = False

        current_song = self.props.current_song
        current_song.props.validation = CoreSong.Validation.FAILED
        if (self.has_next
                and self.props.repeat_mode != RepeatMode.SONG):
            self.next()

    def _on_stream_start(self, klass):
        if self._gapless_set:
            self._playlist.next()

        self._gapless_set = False
        self._time_stamp = int(time.time())

        self.emit("song-changed")

    def _load(self, coresong):
        self._gst_player.props.state = Playback.LOADING
        self._time_stamp = int(time.time())
        self._gst_player.props.url = coresong.props.url

    def play(self, coresong=None):
        """Play a song.

        Start playing a song, a specific CoreSong if supplied and
        available or a song in the playlist decided by the play mode.

        If a song is paused, a subsequent play call without a CoreSong
        supplied will continue playing the paused song.

        :param CoreSong coresong: The CoreSong to play or None.
        """
        if self.props.current_song is None:
            coresong = self._playlist.set_song(coresong)

        if (coresong is not None
                and coresong.props.validation == CoreSong.Validation.FAILED
                and self.props.repeat_mode != RepeatMode.SONG):
            self._on_error()
            return

        if coresong is not None:
            self._load(coresong)

        if self.props.current_song is not None:
            self._gst_player.props.state = Playback.PLAYING

    def pause(self):
        """Pause"""
        self._gst_player.props.state = Playback.PAUSED

    def stop(self):
        """Stop"""
        self._gst_player.props.state = Playback.STOPPED

    def next(self):
        """"Play next song

        Play the next song of the playlist, if any.
        """
        if self._playlist.next():
            self.play(self._playlist.props.current_song)

    def previous(self):
        """Play previous song

        Play the previous song of the playlist, if any.
        """
        position = self._gst_player.props.position
        if position >= 5:
            self.set_position(0.0)
            return

        if self._playlist.previous():
            self.play(self._playlist.props.current_song)

    def play_pause(self):
        """Toggle play/pause state"""
        if self.props.state == Playback.PLAYING:
            self.pause()
        else:
            self.play()

    def _on_clock_tick(self, klass, tick):
        self._log.debug("Clock tick {}, player at {} seconds".format(
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
                # FIXME: Not using Playlist class anymore.
                # playlists.update_all_smart_playlists()
                current_song.bump_play_count()
                current_song.set_last_played()

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
        type=CoreSong, default=None, flags=GObject.ParamFlags.READABLE)
    def current_song(self):
        """Get the current song.

        :returns: The song being played. None if there is no playlist.
        :rtype: CoreSong
        """
        return self._playlist.props.current_song

    def get_position(self):
        """Get player position.

        Player position in seconds.
        :returns: position
        :rtype: float
        """
        return self._gst_player.props.position

    # TODO: used by MPRIS
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

    def _on_seek_finished(self, klass):
        # FIXME: Just a proxy
        self.emit('seek-finished')
