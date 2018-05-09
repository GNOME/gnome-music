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

from collections import deque
from enum import IntEnum
from random import randint
import logging
import time

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstAudio', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gtk, GLib, Gio, GObject, Gst, GstPbutils

from gnomemusic import log
from gnomemusic.gstplayer import GstPlayer, Playback
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists
from gnomemusic.scrobbler import LastFmScrobbler
from gnomemusic.inhibitsuspend import InhibitSuspend


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
        'playlist-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'song-changed': (
            GObject.SignalFlags.RUN_FIRST, None, (Gtk.TreeModel, Gtk.TreeIter)
        ),
        'playback-status-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'repeat-mode-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'volume-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'prev-next-invalidated': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'seeked': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'state-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __repr__(self):
        return '<Player>'

    @log
    def __init__(self, parent_window):
        super().__init__()

        self._parent_window = parent_window

        self.playlist = None
        self.playlist_type = None
        self.playlist_id = None
        self.playlist_field = None
        self.current_song = None
        self._next_song = None
        self._shuffle_history = deque(maxlen=10)
        self._new_clock = True

        Gst.init(None)
        GstPbutils.pb_utils_init()

        self._discoverer = GstPbutils.Discoverer()
        self._discoverer.connect('discovered', self._on_discovered)
        self._discoverer.start()
        self._discovering_urls = {}

        self._settings = Gio.Settings.new('org.gnome.Music')
        self._settings.connect(
            'changed::repeat', self._on_repeat_setting_changed)
        self.repeat = self._settings.get_enum('repeat')

        self.playlist_insert_handler = 0
        self.playlist_delete_handler = 0

        self._player = GstPlayer()
        self._player.connect('clock-tick', self._on_clock_tick)
        self._player.connect('eos', self._on_eos)
        self._player.connect('notify::state', self._on_state_change)

        self._inhibit_suspend = InhibitSuspend(parent_window, self)

        self._lastfm = LastFmScrobbler()

    @log
    def _discover_item(self, item, callback, data=None):
        url = item.get_url()
        if not url:
            logger.warning(
                "The item {} doesn't have a URL set.".format(item))
            return

        if not url.startswith("file://"):
            logger.debug(
                "Skipping discovery of {} as not a local file".format(url))
            return

        obj = (callback, data)

        if url in self._discovering_urls:
            self._discovering_urls[url] += [obj]
        else:
            self._discovering_urls[url] = [obj]
            self._discoverer.discover_uri_async(url)

    @log
    def _on_discovered(self, discoverer, info, error):
        try:
            cbs = self._discovering_urls[info.get_uri()]
            del(self._discovering_urls[info.get_uri()])

            for callback, data in cbs:
                if data is not None:
                    callback(info, error, data)
                else:
                    callback(info, error)
        except KeyError:
            # Not something we're interested in
            return

    @log
    def _on_repeat_setting_changed(self, settings, value):
        self.repeat = settings.get_enum('repeat')
        self.emit('repeat-mode-changed')
        self.emit('prev-next-invalidated')
        self._validate_next_song()

    @log
    def _on_glib_idle(self):
        self.current_song = self._next_song
        self.play()

    @log
    def add_song(self, model, path, _iter):
        """Add a song to current playlist

        :param GtkListStore model: TreeModel
        :param GtkTreePath path: song position
        :param GtkTreeIter_iter: song iter
        """
        new_row = model[_iter]
        self.playlist.insert_with_valuesv(
            int(path.to_string()),
            [self.Field.SONG, self.Field.DISCOVERY_STATUS],
            [new_row[5], new_row[11]])
        self._validate_next_song()
        self.emit('prev-next-invalidated')

    @log
    def remove_song(self, model, path):
        """Remove a song from current playlist

        :param GtkListStore model: TreeModel
        :param GtkTreePath path: song position
        """
        iter_remove = self.playlist.get_iter_from_string(path.to_string())
        if (self.current_song.get_path().to_string() == path.to_string()):
            if self.has_next():
                self.next()
            elif self.has_previous():
                self.previous()
            else:
                self.stop()

        self.playlist.remove(iter_remove)
        self._validate_next_song()
        self.emit('prev-next-invalidated')

    @log
    def _get_random_iter(self, current_song):
        first_iter = self.playlist.get_iter_first()
        if not current_song:
            current_song = first_iter
        if not current_song:
            return None
        if (hasattr(self.playlist, "iter_is_valid")
                and not self.playlist.iter_is_valid(current_song)):
            return None
        current_path = int(self.playlist.get_path(current_song).to_string())
        rows = self.playlist.iter_n_children(None)
        if rows == 1:
            return current_song
        rand = current_path
        while rand == current_path:
            rand = randint(0, rows - 1)
        return self.playlist.get_iter_from_string(str(rand))

    @log
    def _get_next_song(self):
        if (self.current_song
                and self.current_song.valid()):
            iter_ = self.playlist.get_iter(self.current_song.get_path())
        else:
            iter_ = None

        next_song = None

        if self.repeat == RepeatType.SONG:
            if iter_:
                next_song = iter_
            else:
                next_song = self.playlist.get_iter_first()
        elif self.repeat == RepeatType.ALL:
            if iter_:
                next_song = self.playlist.iter_next(iter_)
            if not next_song:
                next_song = self.playlist.get_iter_first()
        elif self.repeat == RepeatType.NONE:
            if iter_:
                next_song = self.playlist.iter_next(iter_)
        elif self.repeat == RepeatType.SHUFFLE:
            next_song = self._get_random_iter(iter_)
            if iter_:
                self._shuffle_history.append(iter_)

        if next_song:
            return Gtk.TreeRowReference.new(
                self.playlist, self.playlist.get_path(next_song))
        else:
            return None

    @log
    def _get_previous_song(self):

        @log
        def get_last_iter():
            iter_ = self.playlist.get_iter_first()
            last = None

            while iter_ is not None:
                last = iter_
                iter_ = self.playlist.iter_next(iter_)

            return last

        if (self.current_song
                and self.current_song.valid()):
            iter_ = self.playlist.get_iter(self.current_song.get_path())
        else:
            iter_ = None

        previous_song = None

        if self.repeat == RepeatType.SONG:
            if iter_:
                previous_song = iter_
            else:
                previous_song = self.playlist.get_iter_first()
        elif self.repeat == RepeatType.ALL:
            if iter_:
                previous_song = self.playlist.iter_previous(iter_)
            if not previous_song:
                previous_song = get_last_iter()
        elif self.repeat == RepeatType.NONE:
            if iter_:
                previous_song = self.playlist.iter_previous(iter_)
        elif self.repeat == RepeatType.SHUFFLE:
            if iter_:
                if (self._player.position < 5
                        and len(self._shuffle_history) > 0):
                    previous_song = self._shuffle_history.pop()

                    # Discard the current song, which is already queued
                    prev_path = self.playlist.get_path(previous_song)
                    current_path = self.playlist.get_path(iter_)
                    if prev_path == current_path:
                        previous_song = None

                if (previous_song is None
                        and len(self._shuffle_history) > 0):
                    previous_song = self._shuffle_history.pop()
                else:
                    previous_song = self._get_random_iter(iter_)

        if previous_song:
            return Gtk.TreeRowReference.new(
                self.playlist, self.playlist.get_path(previous_song))
        else:
            return None

    @log
    def has_next(self):
        repeat_types = [RepeatType.ALL, RepeatType.SONG, RepeatType.SHUFFLE]
        if (not self.playlist
                or self.playlist.iter_n_children(None) < 1):
            return False
        elif not self.current_song:
            return False
        elif self.repeat in repeat_types:
            return True
        elif self.current_song.valid():
            tmp = self.playlist.get_iter(self.current_song.get_path())
            return self.playlist.iter_next(tmp) is not None
        else:
            return True

    @log
    def has_previous(self):
        repeat_types = [RepeatType.ALL, RepeatType.SONG, RepeatType.SHUFFLE]
        if (not self.playlist
                or self.playlist.iter_n_children(None) < 1):
            return False
        elif not self.current_song:
            return False
        elif self.repeat in repeat_types:
            return True
        elif self.current_song.valid():
            tmp = self.playlist.get_iter(self.current_song.get_path())
            return self.playlist.iter_previous(tmp) is not None
        else:
            return True

    @GObject.Property
    @log
    def playing(self):
        """Returns if a song is currently played

        :return: playing
        :rtype: bool
        """
        return self._player.state == Playback.PLAYING

    @log
    def _on_state_change(self, klass, arguments):
        self.emit('state-changed')

        return True

    @log
    def set_playing(self, value):
        """Set state

        :param bool value: Playing
        """
        if value:
            self.play()
        else:
            self.pause()

        self.emit('state-changed')

    @log
    def _load(self, media):
        self._time_stamp = int(time.time())

        url_ = media.get_url()
        if url_ != self._player.url:
            self._player.url = url_

        if self.current_song and self.current_song.valid():
            current_song = self.playlist.get_iter(
                self.current_song.get_path())
            self.emit('song-changed', self.playlist, current_song)

        self._validate_next_song()

    @log
    def _on_next_item_validated(self, _info, error, _iter):
        if error:
            logger.warning("Info {}: error: {}".format(_info, error))
            failed = DiscoveryStatus.FAILED
            self.playlist[_iter][self.Field.DISCOVERY_STATUS] = failed
            next_song = self.playlist.iter_next(_iter)

            if next_song:
                next_path = self.playlist.get_path(next_song)
                self._validate_next_song(
                    Gtk.TreeRowReference.new(self.playlist, next_path))

    @log
    def _validate_next_song(self, song=None):
        if song is None:
            song = self._get_next_song()

        self._next_song = song

        if song is None:
            return

        iter_ = self.playlist.get_iter(self._next_song.get_path())
        status = self.playlist[iter_][self.Field.DISCOVERY_STATUS]
        next_song = self.playlist[iter_][self.Field.SONG]
        url_ = next_song.get_url()

        # Skip remote songs discovery
        if (url_.startswith('http://')
                or url_.startswith('https://')):
            return False
        elif status == DiscoveryStatus.PENDING:
            self._discover_item(next_song, self._on_next_item_validated, iter_)
        elif status == DiscoveryStatus.FAILED:
            GLib.idle_add(self._validate_next_song)

        return False

    @log
    def _on_eos(self, klass):
        if self._next_song:
            GLib.idle_add(self._on_glib_idle)
        elif (self.repeat == RepeatType.NONE):
            self.stop()

            if self.playlist is not None:
                current_song = self.playlist.get_path(
                    self.playlist.get_iter_first())
                if current_song:
                    self.current_song = Gtk.TreeRowReference.new(
                        self.playlist, current_song)
                else:
                    self.current_song = None
                self._load(self.get_current_media())
            self.emit('playback-status-changed')
        else:
            self.stop()
            self.emit('playback-status-changed')

    @log
    def play(self):
        """Play"""
        if self.playlist is None:
            return

        media = None

        if self._player.state != Playback.PAUSED:
            self.stop()

            media = self.get_current_media()
            if not media:
                return

            self._load(media)

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
        if not self.has_next():
            return

        self.current_song = self._next_song
        self.play()

    @log
    def previous(self):
        """Play previous song

        Play the previous song of the playlist, if any.
        """
        if not self.has_previous():
            return

        position = self._player.position
        if position >= 5:
            self._player.seek(0)
            self._player.state = Playback.PLAYING
            return

        self.current_song = self._get_previous_song()
        self.play()

    @log
    def play_pause(self):
        """Toggle play/pause state"""
        if self._player.state == Playback.PLAYING:
            self.set_playing(False)
        else:
            self.set_playing(True)

    @log
    def _create_model(self, model, model_iter):
        new_model = Gtk.ListStore(GObject.TYPE_OBJECT, GObject.TYPE_INT)
        song_id = model[model_iter][5].get_id()
        new_path = None
        for row in model:
            current_iter = new_model.insert_with_valuesv(
                -1, [self.Field.SONG, self.Field.DISCOVERY_STATUS],
                [row[5], row[11]])
            if row[5].get_id() == song_id:
                new_path = new_model.get_path(current_iter)

        return new_model, new_path

    @log
    def set_playlist(self, type_, id_, model, iter_):
        self.playlist, playlist_path = self._create_model(model, iter_)
        self.current_song = Gtk.TreeRowReference.new(
            self.playlist, playlist_path)

        if type_ != self.playlist_type or id_ != self.playlist_id:
            self.emit('playlist-changed')

        self.playlist_type = type_
        self.playlist_id = id_

        if self._player.state == Playback.PLAYING:
            self.emit('prev-next-invalidated')

        GLib.idle_add(self._validate_next_song)

    @log
    def running_playlist(self, type, id):
        if type == self.playlist_type and id == self.playlist_id:
            return self.playlist
        else:
            return None

    @log
    def _on_clock_tick(self, klass, tick):
        logger.debug("Clock tick {}, player at {} seconds".format(
            tick, self._player.position))

        current_media = self.get_current_media()

        if tick == 0:
            self._new_clock = True
            self._lastfm.now_playing(current_media)

        duration = self._player.duration
        if duration is None:
            return

        position = self._player.position
        if position > 0:
            percentage = tick / duration
            if (not self._lastfm.scrobbled
                    and duration > 30
                    and (percentage > 0.5 or tick > 4 * 60)):
                self._lastfm.scrobble(current_media, self._time_stamp)

            if (percentage > 0.5
                    and self._new_clock):
                self._new_clock = False
                # FIXME: we should not need to update static
                # playlists here but removing it may introduce
                # a bug. So, we keep it for the time being.
                playlists.update_all_static_playlists()
                grilo.bump_play_count(current_media)
                grilo.set_last_played(current_media)

        self.emit('clock-tick', int(position))

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
    def get_repeat_mode(self):
        return self.repeat

    @log
    def get_position(self):
        return self._player.position

    @log
    def set_repeat_mode(self, mode):
        self.repeat = mode
        self.emit('repeat-mode-changed')

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
    def get_current_media(self):
        if not self.current_song or not self.current_song.valid():
            return None

        current_song = self.playlist.get_iter(self.current_song.get_path())
        failed = DiscoveryStatus.FAILED
        if self.playlist[current_song][self.Field.DISCOVERY_STATUS] == failed:
            return None
        return self.playlist[current_song][self.Field.SONG]
