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
from typing import Any, Dict, List, Union
import re
import unicodedata
import typing

from gettext import gettext as _
import gi
gi.require_version("Tsparql", "3.0")
from gi.repository import Gio, GLib, Gtk, Tsparql

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


class RepeatMode(Enum):
    """Enum for player repeat mode"""

    # Translators: "shuffle" causes tracks to play in random order.
    NONE = 0, "media-playlist-consecutive-symbolic", _("Shuffle/Repeat Off")
    SONG = 1, "media-playlist-repeat-song-symbolic", _("Repeat Song")
    ALL = 2, "media-playlist-repeat-symbolic", _("Repeat All")
    SHUFFLE = 3, "media-playlist-shuffle-symbolic", _("Shuffle")

    # The type checking is necessary to avoid false positives
    # See: https://github.com/python/mypy/issues/1021
    if typing.TYPE_CHECKING:
        icon: str
        label: str

    def __new__(
            cls, value: int, icon: str = "", label: str = "") -> "RepeatMode":
        obj = object.__new__(cls)
        obj._value_ = value
        obj.icon = icon
        obj.label = label
        return obj


class SongStateIcon(Enum):
    """Enum for icons used in song playing and validation"""
    ERROR = "dialog-error-symbolic"
    PLAYING = "media-playback-start-symbolic"


class View(IntEnum):
    """Enum for views"""
    ALBUM = 0
    ARTIST = 1
    PLAYLIST = 2


def get_artist_from_cursor_dict(cursor_dict: Dict[str, Any]) -> str:
    """Returns the preferred artist for a media item.

    The artist name for a particular media item can be either
    the main artist of the full album (album artist), the
    artist of the song (artist) or possibly it is not known at
    all. The first is preferred in most cases, because it is
    the most accurate in an album setting.

    :param Dict[str, Any] cursor_dict: Dict with Tsparql keys
    :return: The artist name
    :rtype: str
    """

    return (cursor_dict.get("albumArtist")
            or cursor_dict.get("artist")
            or _("Unknown Artist"))


def get_title_from_cursor_dict(cursor_dict):
    """Returns the title of the media item.

    :param Dict[str, Any] cursor_dict: Dict with Tsparql keys
    :return: The title
    :rtype: str
    """

    title = cursor_dict.get("title")

    if not title:
        url = cursor_dict.get("url")
        # FIXME: This and the later occurance are user facing strings,
        # but they ideally should never be seen. A media should always
        # contain a URL or we can not play it, in that case it should
        # be removed.
        if (url is None
                or url == ""):
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


def dict_from_cursor(cursor: Tsparql.SparqlCursor) -> Dict[str, Any]:
    """Iterate a TinySparql cursor to create a dictionary

    :param Tsparql.SparqlCursor cursor: The cursor
    :returns: Dictionary of variable-key pair
    :rtype: Dict[str, Any]
    """
    vars: dict[str, Any] = {}
    for column in range(cursor.get_n_columns()):
        vtype = cursor.get_value_type(column)
        if vtype == Tsparql.SparqlValueType.UNBOUND:
            value = None
        elif vtype == Tsparql.SparqlValueType.INTEGER:
            value = cursor.get_integer(column)
        elif vtype == Tsparql.SparqlValueType.DOUBLE:
            value = cursor.get_double(column)
        elif vtype == Tsparql.SparqlValueType.DATETIME:
            value = cursor.get_datetime(column)
        elif vtype == Tsparql.SparqlValueType.BOOLEAN:
            value = cursor.get_boolean(column)
        else:
            value, _ = cursor.get_string(column)

        vars[cursor.get_variable_name(column)] = value

    return vars


def get_int_from_cursor_dict(cursor_dict: Dict[str, Any], field: str) -> int:
    """Get a specific numeric field from a dictionary or zero

    :param Dict[str, Any] cursor_dict: The dictionary
    :param str field: The field to look up
    :rtype: int
    """
    i = cursor_dict.get(field)
    if not i:
        return 0

    return int(i)
