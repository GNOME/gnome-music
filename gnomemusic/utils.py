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

from enum import Enum, IntEnum

from gettext import gettext as _
from gi.repository import Gio


class SongStateIcon(Enum):
    """Enum for icons used in song playing and validation"""
    ERROR = "dialog-error-symbolic"
    PLAYING = "media-playback-start-symbolic"


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
        # FIXME
        if url is None:
            return "NO URL"
        file_ = Gio.File.new_for_uri(url)
        fileinfo = file_.query_info(
            "standard::display-name", Gio.FileQueryInfoFlags.NONE, None)
        title = fileinfo.get_display_name()
        title = title.replace("_", " ")

    return title


def get_media_year(item):
    """Returns the year when the media was created.

    :param item: A Grilo Media object
    :return: The creation year or '----' if not defined
    :rtype: string
    """
    date = item.get_creation_date()

    if not date:
        return ""

    return str(date.get_year())


def get_album_disc_nr(item):
    """Returns the album song number associated with the media item

    :param Grl.Media item: song
    :return: The album disc number
    :rtype: string
    """
    track_number = item.get_album_disc_number()
    if track_number == 0:
        track_number = ""
    return str(track_number)


def get_media_track_nr(item):
    """Returns the track number of the media item.

    :param Grl.Media item: song
    :return: The song track number
    :rtype: string
    """
    track_number = item.get_track_number()
    if track_number == 0:
        return ""
    return str(track_number)


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


fields_getter = {
    "album": get_album_title,
    "artist": get_artist_name,
    "disc": get_album_disc_nr,
    "title": get_media_title,
    "track": get_media_track_nr,
    "year": get_media_year
}
