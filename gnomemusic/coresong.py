# Copyright 2025 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from enum import IntEnum
from random import randint
from typing import Any, Dict, Optional
import typing

from gi.repository import GLib, GObject

from gnomemusic.songart import SongArt
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.coregrilo import CoreGrilo
import gnomemusic.utils as utils


class CoreSong(GObject.GObject):
    """Song information object

    Contains all relevant information of a song.
    """

    __gtype_name__ = "CoreSong"

    album = GObject.Property(type=str)
    album_urn = GObject.Property(type=str)
    album_disc_number = GObject.Property(type=int)
    artist = GObject.Property(type=str)
    cursor_dict = GObject.Property()
    duration = GObject.Property(type=int)
    id = GObject.Property(type=str, default=None)
    play_count = GObject.Property(type=int)
    shuffle_pos = GObject.Property(type=int)
    state = GObject.Property()  # FIXME: How to set an IntEnum type?
    title = GObject.Property(type=str)
    track_number = GObject.Property(type=int)
    url = GObject.Property(type=str)
    validation = GObject.Property()  # FIXME: How to set an IntEnum type?

    class Validation(IntEnum):
        """Enum for song validation"""
        PENDING = 0
        IN_PROGRESS = 1
        FAILED = 2
        SUCCEEDED = 3

    def __init__(
            self, application: Application,
            cursor_dict: Dict[str, Any]) -> None:
        """Initiate the CoreSong object

        :param Application application: The application object
        :param Dict[str, Any] cursor_dict: Dict with Tsparql keys
        """
        super().__init__()

        self._application: Application = application
        self._coregrilo: CoreGrilo = application.props.coregrilo
        self._favorite: bool = False
        self._last_played: Optional[GLib.DateTime] = None
        self._thumbnail: Optional[str] = None

        self.props.id = cursor_dict.get("id")
        self.props.validation = CoreSong.Validation.PENDING
        self.update(cursor_dict)
        self.update_shuffle_pos()

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, CoreSong)
                and other.props.id == self.props.id)

    @GObject.Property(type=bool, default=False)
    def favorite(self) -> bool:
        return self._favorite

    @favorite.setter  # type: ignore
    def favorite(self, favorite: bool) -> None:
        if self._favorite == favorite:
            return

        self._favorite = favorite
        self._coregrilo.writeback_tracker(self, "favorite")

    @GObject.Property(type=GLib.DateTime, default=None)
    def last_played(self) -> Optional[GLib.DateTime]:
        """Get last played time

        :returns: Last played date time if available
        :rtype: GLib.DateTime or None
        """
        return self._last_played

    @last_played.setter  # type: ignore
    def last_played(self, value: Optional[GLib.DateTime]) -> None:
        """Set last played time

        :param GLib.DateTime value: The datetime to set
        """
        if not value:
            return

        self._last_played = value
        self._coregrilo.writeback_tracker(self, "last-played")

    @GObject.Property(type=str, default=None)
    def thumbnail(self) -> str:
        """Song art thumbnail retrieval

        :return: The song art uri or "generic"
        :rtype: string
        """
        if self._thumbnail is None:
            self._thumbnail = "generic"
            SongArt(self._application, self)

        return self._thumbnail

    @thumbnail.setter  # type: ignore
    def thumbnail(self, value: str) -> None:
        """Song art thumbnail setter

        :param string value: uri or "generic"
        """
        self._thumbnail = value

    def update(self, cursor_dict: Dict[str, Any]) -> None:
        """Update the song with information from the dictionary

        :param Dict[str, Any] cursor_dict: The dicationary to use
        """
        self.props.album = cursor_dict.get("album") or ""
        self.props.album_urn = cursor_dict.get("album_urn")
        self.props.album_disc_number = utils.get_int_from_cursor_dict(
            cursor_dict, "albumDiscNumber")
        self.props.artist = utils.get_artist_from_cursor_dict(cursor_dict)
        self.props.duration = utils.get_int_from_cursor_dict(
            cursor_dict, "duration")
        self._favorite = bool(cursor_dict.get("favorite"))
        self._last_played = cursor_dict.get("lastPlayed")
        self.props.play_count = utils.get_int_from_cursor_dict(
            cursor_dict, "playCount")
        self.props.title = utils.get_title_from_cursor_dict(cursor_dict)
        self.props.track_number = utils.get_int_from_cursor_dict(
            cursor_dict, "trackNumber")
        self.props.url = cursor_dict.get("url")

        self.props.cursor_dict = cursor_dict

    def bump_play_count(self) -> None:
        self.props.play_count = self.props.play_count + 1
        self._coregrilo.writeback_tracker(self, "play-count")

    def update_shuffle_pos(self) -> None:
        """Randomizes the shuffle position of this song"""
        self.props.shuffle_pos = randint(1, 1_000_000)
