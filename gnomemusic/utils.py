# Copyright (c) 2016 Marinus Schraal <mschraal@src.gnome.org>
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
from gettext import gettext as _

import gi
gi.require_version('Grl', '0.3')
from gi.repository import Gio, GLib, Grl

from gnomemusic.grilo import grilo


class View(IntEnum):
    """Enum for views"""
    EMPTY = 0
    ALBUM = 1
    ARTIST = 2
    SONG = 3
    PLAYLIST = 4
    SEARCH = 5


def get_album_title(item):
    """Returns the album title associated with the media item

    In case of an audio file the get_album call returns the
    album title and in case of a container we are looking for
    the title.

    :param item: A Grilo Media object
    :return: The album title
    :rtype: string
    """
    if item.is_container():
        album = get_media_title(item)
    else:
        album = (item.get_album()
                 or _("Unknown album"))

    return album


def get_album_disc_nr(item):
    """Returns the album song number associated with the media item

    :param Grl.Media item: song
    :return: The album title
    :rtype: string
    """
    track_number = item.get_album_disc_number()
    if track_number == 0:
        track_number = ""
    return str(track_number)


def get_media_track_nr(item):
    """Returns the title of the media item.

    :param item: A Grilo Media object
    :return: The title
    :rtype:
    """
    track_number = item.get_track_number()
    if track_number == 0:
        return ""
    return str(track_number)


def get_artist_name(item):
    """Returns the preferred artist for a media item.

    The artist name for a particular media item can be either
    the main artist of the full album (album artist), the
    artist of the song (artist) or possibly it is not known at
    all. The first is preferred in most cases, because it is
    the most accurate in an album setting.

    :param item: A Grilo Media object
    :return: The artist name
    :rtype: string
    """

    return (item.get_album_artist()
            or item.get_artist()
            or _("Unknown Artist"))


def get_media_title(item):
    """Returns the title of the media item.

    :param item: A Grilo Media object
    :return: The title
    :rtype:
    """

    title = item.get_title()

    if not title:
        url = item.get_url()
        file_ = Gio.File.new_for_uri(url)
        fileinfo = file_.query_info(
            "standard::display-name", Gio.FileQueryInfoFlags.NONE, None)
        title = fileinfo.get_display_name()
        title = title.replace("_", " ")

    return title


def get_media_year(item):
    """Returns the year when the media was created.

    :param item: A Grilo Media object
    :return: The creation year or None if not defined
    :rtype: string
    """
    date = item.get_creation_date()

    if not date:
        return None

    return str(date.get_year())


def seconds_to_string(duration):
    """Convert a time in seconds to a mm:ss string

    :param int duration: Time in seconds
    :return: Time in mm:ss format
    :rtype: string
    """
    seconds = duration
    minutes = seconds // 60
    seconds %= 60

    return '{:d}:{:02d}'.format(minutes, seconds)


def set_album_title(item, album):
    """Sets the album title of the media item.

    :param item: A Grilo Media object
    :param album: A string representing album title
    """
    return (item.set_album(album) and
            grilo.set_metadata_key(item, Grl.METADATA_KEY_ALBUM))


def set_artist_name(item, artist):
    """Sets the artist name of the media item.

    :param item: A Grilo Media object
    :param album: A string representing artist name
    """
    return (item.set_artist(artist) and
            grilo.set_metadata_key(item, Grl.METADATA_KEY_ARTIST))


def set_album_disc_number(item, disc_number):
    """Sets the album disc number of the media item.

    :param item: A Grilo Media object
    :param album: A string representing album disc number
    """
    return (item.set_album_disc_number(int(disc_number)) and
            grilo.set_metadata_key(item, Grl.METADATA_KEY_ALBUM_DISC_NUMBER))


def set_title(item, title):
    """Sets the title of the media item.

    :param item: A Grilo Media object
    :param album: A string representing title
    """
    return (item.set_title(title) and
            grilo.set_metadata_key(item, Grl.METADATA_KEY_TITLE))


def set_track_number(item, track_number):
    """Sets the track number of the media item.

    :param item: A Grilo Media object
    :param album: A string representing track number
    """
    return (item.set_track_number(int(track_number)) and
            grilo.set_metadata_key(item, Grl.METADATA_KEY_TRACK_NUMBER))


def set_creation_year(item, creation_year):
    """Sets the creation year of the media item.

    :param item: A Grilo Media object
    :param album: A string representing creation year
    """
    creation_date = item.get_creation_date()
    if creation_date:
        timezone = creation_date.get_timezone()
        month = creation_date.get_month()
        day = creation_date.get_day_of_month()
        hour = creation_date.get_hour()
        minute = creation_date.get_minute()
        second = creation_date.get_second()
        updated_creation_date = GLib.DateTime(
            timezone, int(creation_year), month, day, hour, minute, second)
        return (item.set_creation_date(updated_creation_date) and
                grilo.set_metadata_key(item, Grl.METADATA_KEY_CREATION_DATE))


fields_getter = {
    'album': get_album_title,
    'artist': get_artist_name,
    'disc': get_album_disc_nr,
    'title': get_media_title,
    'track': get_media_track_nr,
    'year': get_media_year
}


fields_setter = {
    'album': set_album_title,
    'artist': set_artist_name,
    'disc': set_album_disc_number,
    'title': set_title,
    'track': set_track_number,
    'year': set_creation_year
}
