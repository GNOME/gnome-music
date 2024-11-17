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

from __future__ import annotations
from enum import Enum, IntEnum
from typing import Any, List, Union
import re
import unicodedata

from gettext import gettext as _
import gi
gi.require_version("Tracker", "3.0")
from gi.repository import Gio, Grl, GLib, Gtk, Tracker

from gnomemusic.musiclogger import MusicLogger


class ArtSize(Enum):
    """Enum for icon sizes"""
    XSMALL = (42, 42)
    SMALL = (74, 74)
    MEDIUM = (192, 192)
    LARGE = (256, 256)

    def __init__(self, width, height):
        """Intialize width and height"""
        self.width = width
        self.height = height


class CoreObjectType(Enum):
    """Indicates the type of the CoreObject passed"""
    ALBUM = 0
    ARTIST = 1
    SONG = 2


class DefaultIconType(Enum):
    ALBUM = "folder-music-symbolic"
    ARTIST = "music-artist-symbolic"


class SongStateIcon(Enum):
    """Enum for icons used in song playing and validation"""
    ERROR = "dialog-error-symbolic"
    PLAYING = "media-playback-start-symbolic"


class View(IntEnum):
    """Enum for views"""
    ALBUM = 0
    ARTIST = 1
    PLAYLIST = 2


def get_album_title(item):
    """Returns the album title associated with the media item

    In case of an audio file the get_album call returns the
    album title and in case of a container we are looking for
    the title.

    :param Grl.Media item: A Grilo Media object
    :return: The album title
    :rtype: str
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

    :param Grl.Media item: A Grilo Media object
    :return: The artist name
    :rtype: str
    """

    return (item.get_album_artist()
            or item.get_artist()
            or _("Unknown Artist"))


def get_media_title(item):
    """Returns the title of the media item.

    :param Grl.Media item: A Grilo Media object
    :return: The title
    :rtype: str
    """

    title = item.get_title()

    if not title:
        url = item.get_url()
        # FIXME: This and the later occurance are user facing strings,
        # but they ideally should never be seen. A media should always
        # contain a URL or we can not play it, in that case it should
        # be removed.
        if url is None:
            return "NO URL"
        file_ = Gio.File.new_for_uri(url)
        try:
            # FIXME: query_info is not async.
            fileinfo = file_.query_info(
                "standard::display-name", Gio.FileQueryInfoFlags.NONE, None)
        except GLib.Error as error:
            MusicLogger().warning(
                "Error: {}, {}".format(error.domain, error.message))
            return "NO URL"
        title = fileinfo.get_display_name()
        title = title.replace("_", " ")

    return title


def get_media_year(item):
    """Returns the year when the media was published.

    :param Grl.Media item: A Grilo Media object
    :return: The publication year or None if not defined
    :rtype: str or None
    """
    date = item.get_publication_date()

    if not date:
        return None

    return str(date.get_year())


def seconds_to_string(duration):
    """Convert a time in seconds to a mm:ss string

    :param int duration: Time in seconds
    :return: Time in mm:ss format
    :rtype: str
    """
    seconds = duration
    minutes = seconds // 60
    seconds %= 60

    return '{:d}:{:02d}'.format(minutes, seconds)


def normalize_caseless(text):
    """Get a normalized casefolded version of a string.

    :param str text: string to normalize
    :returns: normalized casefolded string
    :rtype: str
    """
    return unicodedata.normalize("NFKD", text.casefold())


def natural_sort_names(name_a: str, name_b: str) -> int:
    """Natural order comparison of two strings.

    A natural order is an alphabetical order which takes into account
    digit numbers. For example, it returns ["Album 3", "Album 10"]
    instead of ["Album 10", "Album 3"] for an alphabetical order.
    The names are also normalized to properly take into account names
    which contain accents.

    :param str name_a: first string to compare
    :param str name_b: second string to compare
    :returns: Gtk Ordering
    :rtype: int
    """
    def _extract_numbers(text: str) -> List[Union[int, str]]:
        return [int(tmp) if tmp.isdigit() else tmp
                for tmp in re.split(r"(\d+)", normalize_caseless(text))]

    extract_a = _extract_numbers(name_a)
    extract_b = _extract_numbers(name_b)
    if extract_a < extract_b:
        return Gtk.Ordering.SMALLER
    elif extract_a > extract_b:
        return Gtk.Ordering.LARGER
    else:
        return Gtk.Ordering.EQUAL


def create_grilo_media_from_cursor(
        cursor: Tracker.SparqlCursor, grl_type: Grl.MediaType) -> Grl.Media:
    """Iterate a TinySparql cursor to create a Grl.Media

    :param Tracker.SparqlCursor cursor: The cursor
    :param Grl.MediaType grl_type: The Grilo media type
    :returns: Grilo media
    :rtype: Grl.Media
    """
    vars: dict[str, Any] = {}
    for column in range(cursor.get_n_columns()):
        vtype = cursor.get_value_type(column)
        if vtype == Tracker.SparqlValueType.UNBOUND:
            value = None
        elif vtype == Tracker.SparqlValueType.INTEGER:
            value = cursor.get_integer(column)
        elif vtype == Tracker.SparqlValueType.DOUBLE:
            value = cursor.get_double(column)
        elif vtype == Tracker.SparqlValueType.DATETIME:
            value = cursor.get_datetime(column)
        elif vtype == Tracker.SparqlValueType.BOOLEAN:
            value = cursor.get_boolean(column)
        else:
            value, _ = cursor.get_string(column)

        vars[cursor.get_variable_name(column)] = value

    if grl_type == Grl.MediaType.CONTAINER:
        media = Grl.Media.container_new()
    elif grl_type == Grl.MediaType.AUDIO:
        media = Grl.Media.audio_new()

    media.set_source("gnome-music")

    for key in vars.keys():
        if key == "id":
            media.set_id(vars["id"])
        elif key == "url":
            media.set_url(vars["url"])
        elif key == "title":
            media.set_title(vars["title"])
        elif key == "artist":
            media.set_artist(vars["artist"])
        elif key == "album":
            media.set_album(vars["album"])
        elif key == "duration":
            media.set_duration(int(vars["duration"]))
        elif key == "tag":
            media.set_favourite(vars["tag"] is not None)
        elif key == "lastPlayed":
            last_played = vars["lastPlayed"]
            if last_played is not None:
                media.set_last_played(last_played)
        elif key == "playCount":
            play_count = vars["playCount"]
            if play_count is not None:
                media.set_play_count(int(play_count))
        elif key == "childCount":
            media.set_childcount(int(vars["childCount"]))
        elif key == "creationDate":
            creation_date = vars["creationDate"]
            if creation_date is not None:
                media.set_creation_date(creation_date)

    return media
