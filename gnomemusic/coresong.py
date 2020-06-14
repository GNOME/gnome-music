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

from collections import deque
from enum import IntEnum

import gi
gi.require_version('Grl', '0.3')
from gi.repository import Grl, GLib, GObject

import gnomemusic.utils as utils


class CoreSong(GObject.GObject):
    """Exposes a Grl.Media with relevant data as properties
    """

    album = GObject.Property(type=str)
    album_disc_number = GObject.Property(type=int)
    artist = GObject.Property(type=str)
    duration = GObject.Property(type=int)
    media = GObject.Property(type=Grl.Media)
    grlid = GObject.Property(type=str, default=None)
    play_count = GObject.Property(type=int)
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

    def __init__(self, application, media):
        """Initiate the CoreSong object

        :param Application application: The application object
        :param Grl.Media media: A media object
        """
        super().__init__()

        self._log = application.props.log
        self._coregrilo = application.props.coregrilo
        self._coreselection = application.props.coreselection
        self._favorite = False
        self._selected = False

        self.props.grlid = media.get_source() + media.get_id()
        self._is_tracker = media.get_source() == "grl-tracker3-source"
        self.props.validation = CoreSong.Validation.PENDING
        self.update(media)

    def __eq__(self, other):
        return (isinstance(other, CoreSong)
                and other.props.media.get_id() == self.props.media.get_id())

    @GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READABLE)
    def is_tracker(self):
        return self._is_tracker

    @GObject.Property(type=bool, default=False)
    def favorite(self):
        return self._favorite

    @favorite.setter
    def favorite(self, favorite):
        if not self._is_tracker:
            return

        self._favorite = favorite

        # FIXME: Circular trigger, can probably be solved more neatly.
        old_fav = self.props.media.get_favourite()
        if old_fav == self._favorite:
            return

        self.props.media.set_favourite(self._favorite)
        self._coregrilo.writeback_tracker(
            self.props.media, deque(["favorite"]))

    @GObject.Property(type=bool, default=False)
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        if not self._is_tracker:
            return

        if self._selected == value:
            return

        self._selected = value
        self._coreselection.update_selection(self, self._selected)

    def update(self, media):
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

    def bump_play_count(self):
        if not self._is_tracker:
            return

        self.props.media.set_play_count(self.props.play_count + 1)
        self._coregrilo.writeback_tracker(
            self.props.media, deque(["play-count"]))

    def set_last_played(self):
        if not self._is_tracker:
            return

        self.props.media.set_last_played(GLib.DateTime.new_now_utc())
        self._coregrilo.writeback_tracker(
            self.props.media, deque(["last-played"]))

    def query_musicbrainz_tags(self, callback):
        """Retrieves metadata keys for this CoreSong

        :param callback: Metadata retrieval callback
        """
        def chromaprint_retrieved(media):
            if not media:
                callback(None)
                return

            self._coregrilo.get_tags(self, callback)

        self._coregrilo.get_chromaprint(self, chromaprint_retrieved)

    def update_tags(self, tags):
        """Update tags of a song.

        The properties of a song can be updated with Grilo writeback
        support.

        :param dict tags: New tag values
        """
        def _writeback_cb():
            return

        writeback_keys = []
        if tags["title"] != self.props.title:
            self.props.media.set_title(tags["title"])
            writeback_keys.append(Grl.METADATA_KEY_TITLE)

        if int(tags["track"]) != self.props.track_number:
            self.props.media.set_track_number(int(tags["track"]))
            writeback_keys.append(Grl.METADATA_KEY_TRACK_NUMBER)

        if tags["year"] != utils.get_media_year(self.props.media):
            date = GLib.DateTime.new_utc(int(tags["year"]), 1, 1, 0, 0, 0)
            self.props.media.set_creation_date(date)
            writeback_keys.append(Grl.METADATA_KEY_CREATION_DATE)

        mb_recording_id = tags["mb-recording-id"]
        if (mb_recording_id
                and mb_recording_id != self.props.media.get_mb_recording_id()):
            self.props.media.set_mb_recording_id(tags["mb-recording-id"])
            writeback_keys.append(Grl.METADATA_KEY_MB_RECORDING_ID)

        if (tags["mb-track-id"]
                and tags["mb-track-id"] != self.props.media.get_mb_track_id()):
            self.props.media.set_mb_track_id(tags["mb-track-id"])
            writeback_keys.append(Grl.METADATA_KEY_MB_TRACK_ID)

        if tags["artist"] != self.props.media.get_artist():
            self.props.media.set_artist(tags["artist"])
            writeback_keys.append(Grl.METADATA_KEY_ARTIST)

        if (tags["mb-artist-id"]
                and tags["mb-artist-id"]
                    != self.props.media.get_mb_artist_id()):
            self.props.media.set_mb_artist_id(tags["mb-artist-id"])
            writeback_keys.append(Grl.METADATA_KEY_MB_ARTIST_ID)

        if tags["album"] != self.props.media.get_album():
            self.props.media.set_album(tags["album"])
            writeback_keys.append(Grl.METADATA_KEY_ALBUM)

        if int(tags["disc"]) != self.props.media.get_album_disc_number():
            self.props.media.set_album_disc_number(int(tags["disc"]))
            writeback_keys.append(Grl.METADATA_KEY_ALBUM_DISC_NUMBER)

        if (tags["album-artist"]
                and tags["album-artist"]
                    != self.props.media.get_album_artist()):
            self.props.media.set_album_artist(tags["album-artist"])
            writeback_keys.append(Grl.METADATA_KEY_ALBUM_ARTIST)

        if (tags["mb-release-id"]
                and tags["mb-release-id"]
                    != self.props.media.get_mb_release_id()):
            self.props.media.set_mb_release_id(tags["mb-release-id"])
            writeback_keys.append(Grl.METADATA_KEY_MB_RELEASE_ID)

        release_group_id = tags["mb-release-group-id"]
        if (release_group_id
                and release_group_id
                    != self.props.media.get_mb_release_group_id()):
            self.props.media.set_mb_release_group_id(release_group_id)
            writeback_keys.append(Grl.METADATA_KEY_MB_RELEASE_GROUP_ID)

        if writeback_keys:
            self._log.debug(
                "Updating tags of a song: {}".format(writeback_keys))
            self._coregrilo.writeback(
                self.props.media, writeback_keys, _writeback_cb)
