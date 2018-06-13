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


class RepeatType:
    NONE = 0
    SONG = 1
    ALL = 2
    SHUFFLE = 3


class DiscoveryStatus:
    PENDING = 0
    FAILED = 1
    SUCCEEDED = 2


class PlayerPlaylist(GObject.GObject):
    """PlayerPlaylist object

    Contains the logic to discover a song, handle RepeatType and the
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
        'song-discovered': (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
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

        self._discovering_indexes = {}
        self._discoverer = GstPbutils.Discoverer()
        self._discoverer.connect('discovered', self._on_discovered)
        self._discoverer.start()

    @log
    def set_playlist(self, type_, id_, model, model_iter):
        """Set a new playlist or change the song being played

        :param PlayerPlaylist.Type type_: type of the playlist
        :param string id_: unique identifer to recognize the playlist
        :param GtkListStore model: list of songs to play
        :param GtkTreeIter model_iter: requested song

        :return: True if the playlist has been updated. False otherwise
        :rtype: bool
        """
        changed = False
        if (type_ != self._type
                or id_ != self._id):
            changed = True

        path = model.get_path(model_iter)
        self._current_index = int(path.to_string())

        if changed:
            self._type = type_
            self._id = id_

            self._songs = []
            for row in model:
                self._songs.append([row[5], row[11]])

            if self._repeat == RepeatType.SHUFFLE:
                self._shuffle_indexes = list(range(len(self._songs)))
                shuffle(self._shuffle_indexes)
                self._shuffle_indexes.remove(self._current_index)
                self._shuffle_indexes.insert(0, self._current_index)

            GLib.idle_add(self._discover_all_songs)

        return changed

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
        current_song = self._songs[self._current_index]
        changed_song = self._songs.pop(prev_pos)
        self._songs.insert(new_pos, changed_song)

        # update current_index if necessary
        return_index = -1
        first_pos = min(prev_pos, new_pos)
        last_pos = max(prev_pos, new_pos)
        if (self._current_index >= first_pos
                and self._current_index <= last_pos):
            for index, song in enumerate(self._songs[first_pos:last_pos + 1]):
                if current_song[0].get_id() == song[0].get_id():
                    self._current_index = first_pos + index
                    return_index = self._current_index
                    break

        if self._repeat == RepeatType.SHUFFLE:
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
        item = [song, DiscoveryStatus.PENDING]
        self._songs.insert(song_index, item)
        if song_index >= self._current_index:
            self._current_index += 1

        self._discoverer_song(song_index, item)

        # In the shuffle case, insert song at a random position which
        # has not been played yet.
        if self._repeat == RepeatType.SHUFFLE:
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

        if self._repeat == RepeatType.SHUFFLE:
            self._shuffle_indexes.remove(song_index)
            self._shuffle_indexes = [
                index - 1 if index > song_index else index
                for index in self._shuffle_indexes]

    @log
    def _on_repeat_setting_changed(self, settings, value):
        self.props.repeat_mode = settings.get_enum('repeat')

    @log
    def _on_discovered(self, discoverer, info, error):
        index = self._discovering_indexes[info.get_uri()]
        del(self._discovering_indexes[info.get_uri()])
        if error:
            logger.warning("Info {}: error: {}".format(info, error))
            self._songs[index][1] = DiscoveryStatus.FAILED
        else:
            self._songs[index][1] = DiscoveryStatus.SUCCEEDED
        self.emit('song-discovered', index, self._songs[index][1])

    @log
    def _discoverer_song(self, index, item):
        url = item[0].get_url()
        if not url:
            logger.warning(
                "The item {} doesn't have a URL set.".format(item[0]))
            return
        if not url.startswith("file://"):
            logger.debug(
                "Skipping discovery of {} as not a local file".format(url))
            return

        if item[1] == DiscoveryStatus.PENDING:
            self._discovering_indexes[url] = index
            self._discoverer.discover_uri_async(url)

    @log
    def _discover_all_songs(self):
        for index, item in enumerate(self._songs):
            self._discoverer_song(index, item)

    def has_next(self):
        """Test if there is a song after the current one.

        :return: True if there is a song. False otherwise.
        :rtype: bool
        """
        if (self._repeat == RepeatType.SHUFFLE
                and self._shuffle_indexes):
            index = self._shuffle_indexes.index(self._current_index)
            return index < (len(self._shuffle_indexes) - 1)
        if self._repeat != RepeatType.NONE:
            return True
        return self._current_index < (len(self._songs) - 1)

    def has_previous(self):
        """Test if there is a song before the current one.

        :return: True if there is a song. False otherwise.
        :rtype: bool
        """
        if (self._repeat == RepeatType.SHUFFLE
                and self._shuffle_indexes):
            index = self._shuffle_indexes.index(self._current_index)
            return index > 0
        if self._repeat != RepeatType.NONE:
            return True
        return self._current_index > 0

    def next(self):
        """Go to the next song in the playlist.

        :return: True if operation succeeded. False otherwise.
        :rtype: bool
        """
        if self._repeat == RepeatType.SONG:
            return True
        if (self._repeat == RepeatType.ALL
                and self._current_index == (len(self._songs) - 1)):
            self._current_index = 0
            return True
        if self.has_next():
            if self._repeat == RepeatType.SHUFFLE:
                index = self._shuffle_indexes.index(self._current_index)
                self._current_index = self._shuffle_indexes[index + 1]
            else:
                self._current_index += 1
            return True
        return False

    def previous(self):
        """Go to the previous song in the playlist.

        :return: True if operation succeeded. False otherwise.
        :rtype: bool
        """
        if self._repeat == RepeatType.SONG:
            return True
        if (self._repeat == RepeatType.ALL
                and self._current_index == 0):
            self._current_index = len(self._songs) - 1
            return True
        if self.has_previous():
            if self._repeat == RepeatType.SHUFFLE:
                index = self._shuffle_indexes.index(self._current_index)
                self._current_index = self._shuffle_indexes[index - 1]
            else:
                self._current_index -= 1
            return True
        return False

    @log
    def get_current_index(self):
        """Get current song index"""
        return self._current_index

    @GObject.Property(type=Grl.Media, default=None)
    @log
    def current_song(self):
        if self._songs:
            return self._songs[self._current_index][0]
        return None

    @GObject.Property(type=int, default=RepeatType.NONE)
    @log
    def repeat_mode(self):
        return self._repeat

    @repeat_mode.setter
    @log
    def repeat_mode(self, mode):
        if (mode == RepeatType.SHUFFLE
                and self._songs):
            self._shuffle_indexes = list(range(len(self._songs)))
            shuffle(self._shuffle_indexes)
            self._shuffle_indexes.remove(self._current_index)
            self._shuffle_indexes.insert(0, self._current_index)

        self._repeat = mode

    @GObject.Property(type=int)
    @log
    def id_(self):
        return self._id

    @GObject.Property(type=int)
    @log
    def type_(self):
        return self._type

    @log
    def get_songs(self):
        return self._songs


class Player(GObject.GObject):
    """Main Player object

    Contains the logic of playing a song with Music.
    """

    class Field(IntEnum):
        """Enum for player model fields"""
        SONG = 0
        DISCOVERY_STATUS = 1

    __gsignals__ = {
        'clock-tick': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'playback-status-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'playlist-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'prev-next-invalidated': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'repeat-mode-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'seeked': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'song-changed': (
            GObject.SignalFlags.RUN_FIRST, None, (Grl.Media, int)),
        'song-discovered': (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        'volume-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __repr__(self):
        return '<Player>'

    @log
    def __init__(self, parent_window):
        super().__init__()

        self._parent_window = parent_window

        self._playlist = PlayerPlaylist()
        self._playlist.connect('song-discovered', self._on_song_discovered)

        self._new_clock = True

        Gst.init(None)
        GstPbutils.pb_utils_init()

        self._player = GstPlayer()
        self._player.connect('clock-tick', self._on_clock_tick)
        self._player.connect('eos', self._on_eos)

        root_window = parent_window.get_toplevel()
        self._inhibit_suspend = InhibitSuspend(root_window, self)

        self._lastfm = LastFmScrobbler()

    @log
    def has_next(self):
        """Test if the playlist has a next song."""
        return self._playlist.has_next()

    @log
    def has_previous(self):
        """Test if the playlist has a previous song."""
        return self._playlist.has_previous()

    @GObject.Property
    @log
    def playing(self):
        """Test if a song is currently played."""
        return self._player.state == Playback.PLAYING

    @log
    def _load(self, song):
        self._time_stamp = int(time.time())

        url_ = song.get_url()
        if url_ != self._player.url:
            self._player.url = url_

        self.emit('song-changed', song, self._playlist.get_current_index())

    @log
    def _on_eos(self, klass):
        def on_glib_idle():
            self._playlist.next()
            self.play()

        if self._playlist.has_next():
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
    def set_playlist(self, type_, id_, model, iter_):
        """Set a new playlist or change the song being played

        :param PlayerPlaylist.Type type_: type of the playlist
        :param string id_: unique identifer to recognize the playlist
        :param GtkListStore model: list of songs to play
        :param GtkTreeIter model_iter: requested song
        """
        pl_changed = self._playlist.set_playlist(type_, id_, model, iter_)

        if self._player.state == Playback.PLAYING:
            self.emit('prev-next-invalidated')

        self._playlist.bind_property(
            'repeat_mode', self, 'repeat_mode',
            GObject.BindingFlags.SYNC_CREATE)

        if pl_changed:
            self.emit('playlist-changed')

    @log
    def playlist_change_position(self, prev_pos, new_pos):
        """Change order of a song in the playlist

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
            if self.has_next():
                self.next()
            elif self.has_previous():
                self.previous()
            else:
                self.stop()
        self._playlist.remove_song(song_index)
        self.emit('playlist-changed')
        self.emit('prev-next-invalidated')

    @log
    def add_song(self, song, song_index):
        """Add a song to the current playlist

        :param int song_index: position of the song to add
        """
        self._playlist.add_song(song, song_index)
        self.emit('playlist-changed')
        self.emit('prev-next-invalidated')

    @log
    def _on_song_discovered(self, playlist, index, status):
        self.emit('song-discovered', index, status)
        return True

    @log
    def playing_playlist(self, type_, id_):
        if (type_ == self._playlist.props.type_
                and id_ == self._playlist.props.id_):
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
    @log
    def repeat_mode(self, mode):
        self.emit('repeat-mode-changed')
        self.emit('prev-next-invalidated')

    @GObject.Property(type=Grl.Media, default=None)
    def current_song(self):
        if not self._playlist:
            return None
        return self._playlist.props.current_song

    @log
    def get_playlist_type(self):
        """Playlist type getter"""
        return self._playlist.props.type_

    @log
    def get_playlist_id(self):
        """Playlist id getter"""
        return self._playlist.props.id_

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
    @log
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
