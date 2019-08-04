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

    def __init__(self, media, coreselection, grilo):
        super().__init__()

        self._grilo = grilo
        self._coreselection = coreselection
        self._favorite = False
        self._selected = False

        self.fields_setter = {
            'album': self.set_album_title,
            'artist': self.set_artist_name,
            'disc': self.set_album_disc_number,
            'title': self.set_title,
            'track': self.set_track_number,
            'year': self.set_creation_year
        }

        self.props.grlid = media.get_source() + media.get_id()
        self.props.validation = CoreSong.Validation.PENDING
        self.update(media)

    def __eq__(self, other):
        return (isinstance(other, CoreSong)
                and other.props.media.get_id() == self.props.media.get_id())

    @GObject.Property(type=bool, default=False)
    def favorite(self):
        return self._favorite

    @favorite.setter
    def favorite(self, favorite):
        self._favorite = favorite

        # FIXME: Circular trigger, can probably be solved more neatly.
        old_fav = self.props.media.get_favourite()
        if old_fav == self._favorite:
            return

        self.props.media.set_favourite(self._favorite)
        self._grilo.writeback(self.props.media, Grl.METADATA_KEY_FAVOURITE)

    @GObject.Property(type=bool, default=False)
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
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
        self.props.media.set_play_count(self.props.play_count + 1)
        self._grilo.writeback(self.props.media, Grl.METADATA_KEY_PLAY_COUNT)

    def set_album_title(self, album):
        self.props.media.set_album(album)
        self._grilo.writeback(self.props.media, Grl.METADATA_KEY_ALBUM)

    def set_artist_name(self, artist):
        self.props.media.set_artist(artist)
        self._grilo.writeback(self.props.media, Grl.METADATA_KEY_ARTIST)

    def set_album_disc_number(self, disc_number):
        self.props.media.set_album_disc_number(int(disc_number))
        self._grilo.writeback(self.props.media, Grl.METADATA_KEY_ALBUM_DISC_NUMBER)

    def set_title(self, title):
        self.props.media.set_title(title)
        self._grilo.writeback(self.props.media, Grl.METADATA_KEY_TITLE)

    def set_track_number(self, track_number):
        self.props.media.set_track_number(int(track_number))
        self._grilo.writeback(self.props.media, Grl.METADATA_KEY_TRACK_NUMBER)

    def set_creation_year(self, creation_year):
        creation_date = self.props.media.get_creation_date()
        if creation_date:
            timezone = creation_date.get_timezone()
            month = creation_date.get_month()
            day = creation_date.get_day_of_month()
            hour = creation_date.get_hour()
            minute = creation_date.get_minute()
            second = creation_date.get_second()
            updated_creation_date = GLib.DateTime(
                timezone, int(creation_year), month,
                day, hour, minute, second)
            self.props.media.set_creation_date(updated_creation_date)
            self._grilo.writeback(self.props.media, Grl.METADATA_KEY_CREATION_DATE)

    def set_last_played(self):
        self.props.media.set_last_played(GLib.DateTime.new_now_utc())
        self._grilo.writeback(self.props.media, Grl.METADATA_KEY_LAST_PLAYED)
