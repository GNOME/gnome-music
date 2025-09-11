# Copyright 2025 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from enum import IntEnum
from random import randrange
from typing import Dict, Optional
import typing

from gi.repository import Gtk, GObject, GstPbutils

from gnomemusic.coresong import CoreSong
from gnomemusic.utils import RepeatMode
from gnomemusic.widgets.songwidget import SongWidget

if typing.TYPE_CHECKING:
    from gi.repository import GLib

    from gnomemusic.application import Application


class Queue(GObject.GObject):
    """Queue of songs to be played

    Contains the logic to validate a song, handle RepeatMode and the
    list of songs being played.
    """

    class Type(IntEnum):
        """Type of queue"""
        SONGS = 0
        ALBUM = 1
        ARTIST = 2
        PLAYLIST = 3
        SEARCH_RESULT = 4

    repeat_mode = GObject.Property(type=object)

    def __init__(self, application: Application) -> None:
        """Initialize the queue
        """
        super().__init__()

        GstPbutils.pb_utils_init()

        self._app = application
        self._log = application.props.log
        self._position = 0

        self._validation_songs: Dict[str, CoreSong] = {}
        self._discoverer = GstPbutils.Discoverer()
        self._discoverer.connect("discovered", self._on_discovered)
        self._discoverer.start()

        self._coremodel = self._app.props.coremodel
        self._model = self._coremodel.props.queue_sort
        self._model_recent = self._coremodel.props.recent_queue

        self.connect("notify::repeat-mode", self._on_repeat_mode_changed)

    def has_next(self) -> bool:
        """Check if there is a song after the current one.

        :return: True if there is a song. False otherwise.
        :rtype: bool
        """
        if (self.props.repeat_mode == RepeatMode.SONG
                or self.props.repeat_mode == RepeatMode.ALL
                or self.props.position < self._model.get_n_items() - 1):
            return True

        return False

    def has_previous(self) -> bool:
        """Check if there is a song before the current one.

        :return: True if there is a song. False otherwise.
        :rtype: bool
        """
        if (self.props.repeat_mode == RepeatMode.SONG
                or self.props.repeat_mode == RepeatMode.ALL
                or (self.props.position <= self._model.get_n_items() - 1
                    and self.props.position > 0)):
            return True

        return False

    def get_next(self) -> Optional[CoreSong]:
        """Get the next song in the queue.

        :return: The next CoreSong or None.
        :rtype: CoreSong | None
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

    def next(self) -> bool:
        """Go to the next song in the queue.

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

        self._update_model_recent()
        next_song.props.state = SongWidget.State.PLAYING
        self._validate_next_song()
        return True

    def previous(self) -> bool:
        """Go to the previous song in the queue.

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

        self._update_model_recent()
        self._model[previous_position].props.state = SongWidget.State.PLAYING
        self._validate_previous_song()
        return True

    @GObject.Property(type=int, default=0, flags=GObject.ParamFlags.READABLE)
    def position(self) -> int:
        """Gets current song index.

        :returns: position of the current song in the queue.
        :rtype: int
        """
        return self._position

    @GObject.Property(
        type=CoreSong, default=None, flags=GObject.ParamFlags.READABLE)
    def current_song(self) -> Optional[CoreSong]:
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
                self._update_model_recent()
                return coresong

        return None

    def set_song(self, song: Optional[CoreSong]) -> Optional[CoreSong]:
        """Sets current song.

        If no song is provided, a song is automatically selected.

        :param CoreSong song: song to set
        :returns: The selected song
        :rtype: CoreSong | None
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
            self._update_model_recent()
            return song

        for idx, coresong in enumerate(self._model):
            if coresong == song:
                coresong.props.state = SongWidget.State.PLAYING
                self._position = idx
                self._validate_song(song)
                self._validate_next_song()
                self._update_model_recent()
                return song

        return None

    def end(self) -> None:
        """End play of this queue

        Resets all song state
        """
        for song in self._model:
            song.props.state = SongWidget.State.UNPLAYED

    def _update_model_recent(self) -> None:
        recent_size = self._coremodel.props.recent_queue_size
        offset = max(0, self._position - recent_size)
        self._model_recent.set_offset(offset)

    def _on_repeat_mode_changed(
            self, queue: Queue, param: GObject.ParamSpecBoxed) -> None:
        if self.props.repeat_mode == RepeatMode.SHUFFLE:
            for idx, coresong in enumerate(self._model):
                coresong.update_shuffle_pos()

            song_sorter_exp = Gtk.PropertyExpression.new(
                CoreSong, None, "shuffle-pos")
            songs_sorter = Gtk.NumericSorter.new(song_sorter_exp)
            self._model.set_sorter(songs_sorter)
        elif self.props.repeat_mode in [RepeatMode.NONE, RepeatMode.ALL]:
            self._model.set_sorter(None)

    def _validate_song(self, coresong: CoreSong) -> None:
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

    def _validate_next_song(self) -> None:
        if self.props.repeat_mode == RepeatMode.SONG:
            return

        current_position = self.props.position
        next_position = current_position + 1
        if next_position == self._model.get_n_items():
            if self.props.repeat_mode != RepeatMode.ALL:
                return
            next_position = 0

        self._validate_song(self._model[next_position])

    def _validate_previous_song(self) -> None:
        if self.props.repeat_mode == RepeatMode.SONG:
            return

        current_position = self.props.position
        previous_position = current_position - 1
        if previous_position < 0:
            if self.props.repeat_mode != RepeatMode.ALL:
                return
            previous_position = self._model.get_n_items() - 1

        self._validate_song(self._model[previous_position])

    def _on_discovered(
            self, discoverer: GstPbutils.Discoverer,
            info: GstPbutils.DiscovererInfo, error: GLib.Error) -> None:
        url = info.get_uri()
        coresong = self._validation_songs[url]

        if error:
            self._log.warning("Info {}: error: {}".format(info, error))
            coresong.props.validation = CoreSong.Validation.FAILED
        else:
            coresong.props.validation = CoreSong.Validation.SUCCEEDED
