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

from __future__ import annotations
from enum import IntEnum
from random import randint
from typing import Optional
import typing

import gi
gi.require_version('Grl', '0.3')
from gi.repository import Grl, GLib, GObject

from gnomemusic.songart import SongArt
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.coregrilo import CoreGrilo
    from gnomemusic.coreselection import CoreSelection
import gnomemusic.utils as utils


class CoreSong(GObject.GObject):
    """Exposes a Grl.Media with relevant data as properties
    """

    __gtype_name__ = "CoreSong"

    album = GObject.Property(type=str)
    album_disc_number = GObject.Property(type=int)
    artist = GObject.Property(type=str)
    duration = GObject.Property(type=int)
    media = GObject.Property(type=Grl.Media)
    grlid = GObject.Property(type=str, default=None)
    play_count = GObject.Property(type=int)
    shuffle_pos = GObject.Property(type=int)
    state = GObject.Property()  # FIXME: How to set an IntEnum type?
    title = GObject.Property(type=str)
    track_number = GObject.Property(type=int)
    url = GObject.Property(type=str)
    validation = GObject.Property()  # FIXME: How to set an IntEnum type?

    class Validation(IntEnum):
        """Enum for song validation"""
        PENDING: int = 0
        IN_PROGRESS: int = 1
        FAILED: int = 2
        SUCCEEDED: int = 3

    def __init__(self, application: Application, media: Grl.Media) -> None:
        """Initiate the CoreSong object

        :param Application application: The application object
        :param Grl.Media media: A media object
        """
        super().__init__()

        self._application: Application = application
        self._coregrilo: CoreGrilo = application.props.coregrilo
        self._coreselection: CoreSelection = application.props.coreselection
        self._favorite: bool = False
        self._selected: bool = False
        self._thumbnail: Optional[str] = None

        self.props.grlid = media.get_source() + media.get_id()
        self._is_tracker: bool = media.get_source() == "grl-tracker3-source"
        self._is_filesystem: bool = media.get_source() == "grl-filesystem"
        self.props.validation = CoreSong.Validation.PENDING
        self.update(media)
        self.update_shuffle_pos()

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, CoreSong)
                and other.props.media.get_id() == self.props.media.get_id())

    @GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READABLE)
    def is_tracker(self) -> bool:
        return self._is_tracker

    @GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READABLE)
    def is_filesystem(self) -> bool:
        """This property checks if the coresong has been loaded
        by the Grilo filesystem plugin.

        :returns: True is the song comes from the Grilo filesystem
                  plugin
        """
        return self._is_filesystem

    @GObject.Property(type=bool, default=False)
    def favorite(self) -> bool:
        return self._favorite

    @favorite.setter  # type: ignore
    def favorite(self, favorite: bool) -> None:
        if not self._is_tracker:
            return

        self._favorite = favorite

        # FIXME: Circular trigger, can probably be solved more neatly.
        old_fav: bool = self.props.media.get_favourite()
        if old_fav == self._favorite:
            return

        self.props.media.set_favourite(self._favorite)
        self._coregrilo.writeback_tracker(
            self.props.media, "favorite")

    @GObject.Property(type=bool, default=False)
    def selected(self) -> bool:
        return self._selected

    @selected.setter  # type: ignore
    def selected(self, value: bool) -> None:
        if not self._is_tracker:
            return

        if self._selected == value:
            return

        self._selected = value
        self._coreselection.update_selection(self, self._selected)

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

        if self._thumbnail != "generic":
            self.props.media.set_thumbnail(self._thumbnail)

    def update(self, media: Grl.Media) -> None:
        self.props.media = media
        self.props.album = utils.get_album_title(media)
        self.props.album_disc_number = media.get_album_disc_number()
        self.props.artist = utils.get_artist_name(media)
        self.props.duration = media.get_duration()
        self.props.favorite = media.get_favourite()
        self.props.play_count = media.get_play_count()
        self.props.title = utils.get_media_title(media)
        self.props.track_number = media.get_track_number()
        self.props.url = media.get_url()

    def bump_play_count(self) -> None:
        if not self._is_tracker:
            return

        self.props.media.set_play_count(self.props.play_count + 1)
        self._coregrilo.writeback_tracker(
            self.props.media, "play-count")

    def set_last_played(self) -> None:
        if not self._is_tracker:
            return

        self.props.media.set_last_played(GLib.DateTime.new_now_utc())
        self._coregrilo.writeback_tracker(
            self.props.media, "last-played")

    def update_shuffle_pos(self) -> None:
        """Randomizes the shuffle position of this song"""
        self.props.shuffle_pos = randint(1, 1_000_000)
