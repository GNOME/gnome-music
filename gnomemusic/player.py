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

from collections import defaultdict
from enum import IntEnum
from random import shuffle, randrange
import logging
import time

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstAudio', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gio, GLib, GObject, Grl, Gst, GstPbutils

from gnomemusic import log
from gnomemusic.gstplayer import GstPlayer, Playback
from gnomemusic.grilo import grilo
from gnomemusic.inhibitsuspend import InhibitSuspend
from gnomemusic.playlists import Playlists
from gnomemusic.scrobbler import LastFmScrobbler


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
    FAILED = 1
    SUCCEEDED = 2


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

    def __repr__(self):
        return '<PlayerPlayList>'

    @log
    def __init__(self):
        super().__init__()
        self._songs = []
        self._shuffle_indexes = []
        self._current_index = 0

        self._type = -1
        self._id = -1

        self._settings = Gio.Settings.new('org.gnome.Music')
        self._settings.connect(
            'changed::repeat', self._on_repeat_setting_changed)
        self._repeat = self._settings.get_enum('repeat')

        self._validation_indexes = None
        self._discoverer = GstPbutils.Discoverer()
        self._discoverer.connect('discovered', self._on_discovered)
        self._discoverer.start()

    @log
    def set_playlist(self, playlist_type, playlist_id, model, model_iter):
        """Set a new playlist or change the song being played

        :param PlayerPlaylist.Type playlist_type: playlist type
        :param string playlist_id: unique identifer to recognize the playlist
        :param GtkListStore model: list of songs to play
        :param GtkTreeIter model_iter: requested song

        :return: True if the playlist has been updated. False otherwise
        :rtype: bool
        """
        path = model.get_path(model_iter)
        self._current_index = int(path.to_string())
        self._validation_indexes = defaultdict(list)

        # Playlist is the same. Check that the requested song is valid.
        # If not, try to get the next valid one
        if (playlist_type == self._type
                and playlist_id == self._id):
            if not self._current_song_is_valid():
                self.next()
            else:
                self._validate_song(self._current_index)
                self._validate_next_song()
            return False

        self._type = playlist_type
        self._id = playlist_id

        self._songs = []
        for row in model:
            self._songs.append([row[5], row[11]])

        if self._repeat == RepeatMode.SHUFFLE:
            self._shuffle_indexes = list(range(len(self._songs)))
            shuffle(self._shuffle_indexes)
            self._shuffle_indexes.remove(self._current_index)
            self._shuffle_indexes.insert(0, self._current_index)

        # If the playlist has already been played, check that the requested
        # song is valid. If it has never been played, validate the current
        # song and the next song to display an error icon on failure.
        if not self._current_song_is_valid():
            self.next()
        else:
            self._validate_song(self._current_index)
            self._validate_next_song()
        return True

    @log
    def set_song(self, song_index):
        """Change playlist index.

        :param int song_index: requested song index
        :return: True if the index has changed. False otherwise.
        :rtype: bool
        """
        if song_index >= len(self._songs):
            return False

        self._current_index = song_index
        return True

    @log
    def change_position(self, prev_pos, new_pos):
        """Change order of a song in the playlist

        :param int prev_pos: previous position
        :param int new_pos: new position
        :return: new index of the song being played. -1 if unchanged
        :rtype: int
        """
        current_item = self._songs[self._current_index]
        current_song_id = current_item[PlayerField.SONG].get_id()
        changed_song = self._songs.pop(prev_pos)
        self._songs.insert(new_pos, changed_song)

        # Update current_index if necessary.
        return_index = -1
        first_pos = min(prev_pos, new_pos)
        last_pos = max(prev_pos, new_pos)
        if (self._current_index >= first_pos
                and self._current_index <= last_pos):
            for index, item in enumerate(self._songs[first_pos:last_pos + 1]):
                if item[PlayerField.SONG].get_id() == current_song_id:
                    self._current_index = first_pos + index
                    return_index = self._current_index
                    break

        if self._repeat == RepeatMode.SHUFFLE:
            index_l = self._shuffle_indexes.index(last_pos)
            self._shuffle_indexes.pop(index_l)
            self._shuffle_indexes = [
                index + 1 if (index < last_pos and index >= first_pos)
                else index
                for index in self._shuffle_indexes]
            self._shuffle_indexes.insert(index_l, first_pos)

        return return_index

    @log
    def add_song(self, song, song_index):
        """Add a song to the playlist.

        :param Grl.Media song: new song
        :param int song_index: song position
        """
        item = [song, ValidationStatus.PENDING]
        self._songs.insert(song_index, item)
        if song_index >= self._current_index:
            self._current_index += 1

        self._validate_song(song_index)

        # In the shuffle case, insert song at a random position which
        # has not been played yet.
        if self._repeat == RepeatMode.SHUFFLE:
            index = self._shuffle_indexes.index(self._current_index)
            new_song_index = randrange(index, len(self._shuffle_indexes))
            self._shuffle_indexes.insert(new_song_index, song_index)

    @log
    def remove_song(self, song_index):
        """Remove a song from the playlist.

        :param int song_index: index of the song to remove
        """
        self._songs.pop(song_index)
        if song_index < self._current_index:
            self._current_index -= 1

        if self._repeat == RepeatMode.SHUFFLE:
            self._shuffle_indexes.remove(song_index)
            self._shuffle_indexes = [
                index - 1 if index > song_index else index
                for index in self._shuffle_indexes]

    @log
    def _on_repeat_setting_changed(self, settings, value):
        self.props.repeat_mode = settings.get_enum('repeat')

    @log
    def _on_discovered(self, discoverer, info, error):
        url = info.get_uri()
        field = PlayerField.VALIDATION
        index = self._validation_indexes[url].pop(0)
        if not self._validation_indexes[url]:
            self._validation_indexes.pop(url)

        if error:
            logger.warning("Info {}: error: {}".format(info, error))
            self._songs[index][field] = ValidationStatus.FAILED
        else:
            self._songs[index][field] = ValidationStatus.SUCCEEDED
        self.emit('song-validated', index, self._songs[index][field])

    @log
    def _validate_song(self, index):
        item = self._songs[index]
        # Song has already been processed, nothing to do.
        if item[PlayerField.VALIDATION] != ValidationStatus.PENDING:
            return

        song = item[PlayerField.SONG]
        url = song.get_url()
        if not url:
            logger.warning("The item {} doesn't have a URL set.".format(song))
            return
        if not url.startswith("file://"):
            logger.debug(
                "Skipping validation of {} as not a local file".format(url))
            return

        self._validation_indexes[url].append(index)
        self._discoverer.discover_uri_async(url)

    @log
    def _get_next_index(self):
        if not self.has_next():
            return -1

        if self._repeat == RepeatMode.SONG:
            return self._current_index
        if (self._repeat == RepeatMode.ALL
                and self._current_index == (len(self._songs) - 1)):
            return 0
        if self._repeat == RepeatMode.SHUFFLE:
            index = self._shuffle_indexes.index(self._current_index)
            return self._shuffle_indexes[index + 1]
        else:
            return self._current_index + 1

    @log
    def _get_previous_index(self):
        if not self.has_previous():
            return -1

        if self._repeat == RepeatMode.SONG:
            return self._current_index
        if (self._repeat == RepeatMode.ALL
                and self._current_index == 0):
            return len(self._songs) - 1
        if self._repeat == RepeatMode.SHUFFLE:
            index = self._shuffle_indexes.index(self._current_index)
            return self._shuffle_indexes[index - 1]
        else:
            return self._current_index - 1

    @log
    def _validate_next_song(self):
        if self._repeat == RepeatMode.SONG:
            return

        next_index = self._get_next_index()
        if next_index >= 0:
            self._validate_song(next_index)

    @log
    def _validate_previous_song(self):
        if self._repeat == RepeatMode.SONG:
            return

        previous_index = self._get_previous_index()
        if previous_index >= 0:
            self._validate_song(previous_index)

    @log
    def has_next(self):
        """Test if there is a song after the current one.

        :return: True if there is a song. False otherwise.
        :rtype: bool
        """
        if (self._repeat == RepeatMode.SHUFFLE
                and self._shuffle_indexes):
            index = self._shuffle_indexes.index(self._current_index)
            return index < (len(self._shuffle_indexes) - 1)
        if self._repeat != RepeatMode.NONE:
            return True
        return self._current_index < (len(self._songs) - 1)

    @log
    def has_previous(self):
        """Test if there is a song before the current one.

        :return: True if there is a song. False otherwise.
        :rtype: bool
        """
        if (self._repeat == RepeatMode.SHUFFLE
                and self._shuffle_indexes):
            index = self._shuffle_indexes.index(self._current_index)
            return index > 0
        if self._repeat != RepeatMode.NONE:
            return True
        return self._current_index > 0

    @log
    def next(self):
        """Go to the next song in the playlist.

        :return: True if the operation succeeded. False otherwise.
        :rtype: bool
        """
        next_index = self._get_next_index()
        if next_index >= 0:
            self._current_index = next_index
            if self._current_song_is_valid():
                self._validate_next_song()
                return True
            else:
                return self.next()
        return False

    @log
    def previous(self):
        """Go to the previous song in the playlist.

        :return: True if the operation succeeded. False otherwise.
        :rtype: bool
        """
        previous_index = self._get_previous_index()
        if previous_index >= 0:
            self._current_index = previous_index
            if self._current_song_is_valid():
                self._validate_previous_song()
                return True
            else:
                return self.previous()
        return False

    @log
    def get_current_index(self):
        """Get current song index.

        :returns: position of the current song int the playlist.
        :rtype: int
        """
        return self._current_index

    @GObject.Property(
        type=Grl.Media, default=None, flags=GObject.ParamFlags.READABLE)
    def current_song(self):
        """Get current song.

        :returns: the song being played or None if there are no songs
        :rtype: Grl.Media
        """
        if self._songs:
            return self._songs[self._current_index][PlayerField.SONG]
        return None

    def _current_song_is_valid(self):
        """Check if current song can be played.

        :returns: False if validation failed
        :rtype: bool
        """
        current_item = self._songs[self._current_index]
        return current_item[PlayerField.VALIDATION] != ValidationStatus.FAILED

    @GObject.Property(type=int, default=RepeatMode.NONE)
    def repeat_mode(self):
        """Get repeat mode.

        :returns: the repeat mode
        :rtype: RepeatMode
        """
        return self._repeat

    @repeat_mode.setter
    def repeat_mode(self, mode):
        """Set repeat mode.

        :param RepeatMode mode: new repeat_mode
        """
        if (mode == RepeatMode.SHUFFLE
                and self._songs):
            self._shuffle_indexes = list(range(len(self._songs)))
            shuffle(self._shuffle_indexes)
            self._shuffle_indexes.remove(self._current_index)
            self._shuffle_indexes.insert(0, self._current_index)

        self._repeat = mode

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
    def get_songs(self):
        """Get the current playlist.

        Each member of the list has two elements: the song, and the validation
        status.

        :returns: current playlist
        :rtype: list
        """
        return self._songs


class Player(GObject.GObject):
    """Main Player object

    Contains the logic of playing a song with Music.
    """

    __gsignals__ = {
        'clock-tick': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'playlist-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'song-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'song-validated': (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        'playback-status-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'repeat-mode-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'volume-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'prev-next-invalidated': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'seeked': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __repr__(self):
        return '<Player>'

    @log
    def __init__(self, parent_window):
        super().__init__()

        self._parent_window = parent_window

        self._playlist = PlayerPlaylist()
        self._playlist.connect('song-validated', self._on_song_validated)

        self._new_clock = True

        Gst.init(None)
        GstPbutils.pb_utils_init()

        self._player = GstPlayer()
        self._player.connect('clock-tick', self._on_clock_tick)
        self._player.connect('eos', self._on_eos)

        root_window = parent_window.get_toplevel()
        self._inhibit_suspend = InhibitSuspend(root_window, self)

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
        return self._player.state == Playback.PLAYING

    @log
    def _load(self, song):
        self._time_stamp = int(time.time())

        url_ = song.get_url()
        if url_ != self._player.url:
            self._player.url = url_

        self.emit('song-changed', self._playlist.get_current_index())

    @log
    def _on_eos(self, klass):
        def on_glib_idle():
            self._playlist.next()
            self.play()

        if self.props.has_next:
            GLib.idle_add(on_glib_idle)
        else:
            self.stop()
            self.emit('playback-status-changed')

    @log
    def play(self, song_index=None):
        """Play"""
        if not self._playlist:
            return

        if (song_index
                and not self._playlist.set_song(song_index)):
            return False

        if self._player.state != Playback.PAUSED:
            self.stop()
            self._load(self._playlist.props.current_song)

        self._player.state = Playback.PLAYING
        self.emit('playback-status-changed')

    @log
    def pause(self):
        """Pause"""
        self._player.state = Playback.PAUSED
        self.emit('playback-status-changed')

    @log
    def stop(self):
        """Stop"""
        self._player.state = Playback.STOPPED
        self.emit('playback-status-changed')

    @log
    def next(self):
        """"Play next song

        Play the next song of the playlist, if any.
        """

        if self._playlist.next():
            self.play()

    @log
    def previous(self):
        """Play previous song

        Play the previous song of the playlist, if any.
        """
        position = self._player.position
        if position >= 5:
            self._player.seek(0)
            self._player.state = Playback.PLAYING
            return

        if self._playlist.previous():
            self.play()

    @log
    def play_pause(self):
        """Toggle play/pause state"""
        if self._player.state == Playback.PLAYING:
            self.pause()
        else:
            self.play()

    @log
    def set_playlist(self, playlist_type, playlist_id, model, iter_):
        """Set a new playlist or change the song being played.

        :param PlayerPlaylist.Type playlist_type: playlist type
        :param string playlist_id: unique identifer to recognize the playlist
        :param GtkListStore model: list of songs to play
        :param GtkTreeIter model_iter: requested song
        """
        playlist_changed = self._playlist.set_playlist(
            playlist_type, playlist_id, model, iter_)

        if self._player.state == Playback.PLAYING:
            self.emit('prev-next-invalidated')

        self._playlist.bind_property(
            'repeat_mode', self, 'repeat_mode',
            GObject.BindingFlags.SYNC_CREATE)

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
            self.emit('prev-next-invalidated')
        return current_index

    @log
    def remove_song(self, song_index):
        """Remove a song from the current playlist.

        :param int song_index: position of the song to remove
        """
        if self._playlist.get_current_index() == song_index:
            if self.props.has_next:
                self.next()
            elif self.props.has_previous:
                self.previous()
            else:
                self.stop()
        self._playlist.remove_song(song_index)
        self.emit('playlist-changed')
        self.emit('prev-next-invalidated')

    @log
    def add_song(self, song, song_index):
        """Add a song to the current playlist.

        :param int song_index: position of the song to add
        """
        self._playlist.add_song(song, song_index)
        self.emit('playlist-changed')
        self.emit('prev-next-invalidated')

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
            tick, self._player.position))

        current_song = self._playlist.props.current_song

        if tick == 0:
            self._new_clock = True
            self._lastfm.now_playing(current_song)

        duration = self._player.duration
        if duration is None:
            return

        position = self._player.position
        if position > 0:
            percentage = tick / duration
            if (not self._lastfm.scrobbled
                    and duration > 30
                    and (percentage > 0.5 or tick > 4 * 60)):
                self._lastfm.scrobble(current_song, self._time_stamp)

            if (percentage > 0.5
                    and self._new_clock):
                self._new_clock = False
                # FIXME: we should not need to update static
                # playlists here but removing it may introduce
                # a bug. So, we keep it for the time being.
                playlists.update_all_static_playlists()
                grilo.bump_play_count(current_song)
                grilo.set_last_played(current_song)

        self.emit('clock-tick', int(position))

    @GObject.Property(type=int)
    def repeat_mode(self):
        return self._playlist.props.repeat_mode

    @repeat_mode.setter
    def repeat_mode(self, mode):
        self.emit('repeat-mode-changed')
        self.emit('prev-next-invalidated')

    @GObject.Property(
        type=Grl.Media, default=None, flags=GObject.ParamFlags.READABLE)
    def current_song(self):
        """Get the current song.

        :returns: the song being played. None if there is no playlist.
        :rtype: Grl.Media
        """
        if not self._playlist:
            return None
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

    # MPRIS
    @log
    def get_gst_player(self):
        """GstPlayer getter"""
        return self._player

    @log
    def get_playback_status(self):
        # FIXME: Just a proxy right now.
        return self._player.state

    @GObject.Property
    def url(self):
        """GstPlayer url loaded

        :return: url
        :rtype: string
        """
        # FIXME: Just a proxy right now.
        return self._player.url

    @log
    def get_position(self):
        return self._player.position

    # TODO: used by MPRIS
    @log
    def set_position(self, offset, start_if_ne=False, next_on_overflow=False):
        if offset < 0:
            if start_if_ne:
                offset = 0
            else:
                return

        duration = self._player.duration
        if duration is None:
            return

        if duration >= offset * 1000:
            self._player.seek(offset * 1000)
            self.emit('seeked', offset)
        elif next_on_overflow:
            self.next()

    @log
    def get_volume(self):
        return self._player.volume

    @log
    def set_volume(self, rate):
        self._player.volume = rate
        self.emit('volume-changed')

    @log
    def get_songs(self):
        return self._playlist.get_songs()
