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

from __future__ import annotations
import time
import typing

import gi
gi.require_version('GstPbutils', '1.0')
from gi.repository import GLib, GObject

from gnomemusic.coresong import CoreSong
from gnomemusic.gstplayer import GstPlayer, Playback
from gnomemusic.utils import RepeatMode
from gnomemusic.queue import Queue

if typing.TYPE_CHECKING:
    from gi.repository import Gio, Gtk


class Player(GObject.GObject):
    """Main Player object

    Contains the logic of playing a song with Music.
    """

    __gsignals__ = {
        'seek-finished': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'song-changed': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    duration = GObject.Property(type=float, default=-1.)
    mute = GObject.Property(type=bool, default=False)
    state = GObject.Property(type=int, default=Playback.STOPPED)
    volume = GObject.Property(type=float, default=1.)

    def __init__(self, application):
        """Initialize the player

        :param Application application: Application object
        """
        super().__init__()

        self._app = application
        # In the case of gapless playback, both 'about-to-finish'
        # and 'eos' can occur during the same stream. 'about-to-finish'
        # already sets self._queue to the next song, so doing it
        # again on eos would skip a song.
        # TODO: Improve queue handling so this hack is no longer
        # needed.
        self._gapless_set = False
        self._log = application.props.log
        self._queue = Queue(self._app)

        self._queue_model = self._app.props.coremodel.props.queue_sort
        self._queue_model.connect(
            "items-changed", self._on_queue_model_items_changed)

        self._settings = application.props.settings
        self._settings.connect("changed::repeat", self._on_repeat_mode_changed)

        self._repeat = RepeatMode(self._settings.get_enum("repeat"))
        self.bind_property(
            'repeat-mode', self._queue, 'repeat-mode',
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

        self._gst_player.bind_property(
            "volume", self, "volume", GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        self._gst_player.bind_property(
            "mute", self, "mute", GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

    @GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READABLE)
    def has_next(self):
        """Test if the queue has a next song.

        :returns: True if the current song is not the last one.
        :rtype: bool
        """
        return self._queue.has_next()

    @GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READABLE)
    def has_previous(self):
        """Test if the queue has a previous song.

        :returns: True if the current song is not the first one.
        :rtype: bool
        """
        return self._queue.has_previous()

    @GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READABLE)
    def playing(self):
        """Test if a song is currently played.

        :returns: True if a song is currently played.
        :rtype: bool
        """
        return self.props.state == Playback.PLAYING

    def _on_queue_model_items_changed(
            self, model: Gtk.SortListModel, position: int, removed: int,
            added: int) -> None:
        if (removed > 0
                and model.get_n_items() == 0):
            self.stop()

    def _on_repeat_mode_changed(
            self, settings: Gio.Settings, key: str) -> None:
        repeat_mode = settings.get_enum(key)
        self.props.repeat_mode = RepeatMode(repeat_mode)

    def _on_about_to_finish(self, klass):
        if self.props.has_next:
            self._log.debug("Song is about to finish, loading the next one.")
            next_coresong = self._queue.get_next()
            new_url = next_coresong.props.url
            self._gst_player.props.url = new_url
            self._gapless_set = True

    def _on_eos(self, klass):
        self._queue.next()

        if self._gapless_set:
            # After 'eos' in the gapless case, the pipeline needs to be
            # hard reset.
            self._log.debug("Song finished, loading the next one.")
            self.stop()
            self.play(self.props.current_song)
        else:
            self._log.debug("End of the queue, stopping the player.")
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
            self._queue.next()

        self._gapless_set = False
        self._time_stamp = int(time.time())

        self.emit("song-changed")

    def _load(self, coresong):
        self._log.debug("Loading song {}".format(coresong.props.title))
        self._gst_player.props.state = Playback.LOADING
        self._time_stamp = int(time.time())
        self._gst_player.props.url = coresong.props.url

    def play(self, coresong=None):
        """Play a song.

        Start playing a song, a specific CoreSong if supplied and
        available or a song in the queue decided by the play mode.

        If a song is paused, a subsequent play call without a CoreSong
        supplied will continue playing the paused song.

        :param CoreSong coresong: The CoreSong to play or None.
        """
        if self.props.current_song is None:
            coresong = self._queue.set_song(coresong)

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
        self._app.props.window.set_player_visible(False)
        self._queue.end()

    def next(self):
        """"Play next song

        Play the next song of the queue, if any.
        """
        if self._gapless_set:
            self.set_position(0.0)
        elif self._queue.next():
            self.play(self._queue.props.current_song)

    def previous(self):
        """Play previous song

        Play the previous song of the queue, if any.
        """
        position = self._gst_player.props.position
        if self._gapless_set:
            self.stop()

        if (position < 5
                and self._queue.has_previous()):
            self._queue.previous()
            self._gapless_set = False
            self.play(self._queue.props.current_song)
        # This is a special case for a song that is very short and the
        # first song in the queue. It can trigger gapless, but
        # has_previous will return False.
        elif (position < 5
                and self._queue.props.position == 0):
            self.set_position(0.0)
            self._gapless_set = False
            self.play(self._queue.props.current_song)
        else:
            self.set_position(0.0)

    def play_pause(self):
        """Toggle play/pause state"""
        if self.props.state == Playback.PLAYING:
            self.pause()
        else:
            self.play()

    def _on_clock_tick(self, klass, tick):
        self._log.debug("Clock tick {}, player at {} seconds".format(
            tick, self._gst_player.props.position))

        if tick == 0:
            self._new_clock = True

        if self.props.duration == -1.:
            return

        position = self._gst_player.props.position
        if position > 0:
            percentage = tick / self.props.duration
            if (percentage > 0.5
                    and self._new_clock):
                self._new_clock = False
                GLib.idle_add(self._update_stats)

    def _update_stats(self) -> None:
        current_song = self._queue.props.current_song
        current_song.props.last_played = GLib.DateTime.new_now_utc()
        current_song.bump_play_count()

    @GObject.Property(type=object)
    def repeat_mode(self) -> RepeatMode:
        """Gets current repeat mode.

        :returns: current repeat mode
        :rtype: RepeatMode
        """
        return self._repeat

    @repeat_mode.setter  # type: ignore
    def repeat_mode(self, mode):
        if mode == self._repeat:
            return

        self._repeat = mode
        self._settings.set_enum("repeat", mode.value)

    @GObject.Property(type=int, default=0, flags=GObject.ParamFlags.READABLE)
    def position(self):
        """Gets current song index.

        :returns: position of the current song in the queue.
        :rtype: int
        """
        return self._queue.props.position

    @GObject.Property(
        type=CoreSong, default=None, flags=GObject.ParamFlags.READABLE)
    def current_song(self):
        """Get the current song.

        :returns: The song being played. None if there is no queue.
        :rtype: CoreSong
        """
        return self._queue.props.current_song

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
