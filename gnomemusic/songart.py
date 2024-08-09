# Copyright 2020 The GNOME Music developers
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

import asyncio

import gi
gi.require_version("MediaArt", "2.0")
from gi.repository import GLib, GObject, Gio, MediaArt

from gnomemusic.embeddedart import EmbeddedArt


class SongArt(GObject.GObject):
    """SongArt retrieval object
    """

    def __init__(self, application, coresong):
        """Initialize SongArt

        :param Application application: The application object
        :param CoreSong coresong: The coresong to use
        """
        super().__init__()

        self._coresong = coresong
        self._coregrilo = application.props.coregrilo
        self._album = self._coresong.props.album
        self._artist = self._coresong.props.artist

        asyncio.create_task(self._in_cache())

    def _on_embedded_art_found(self, embeddedart, found):
        if found:
            asyncio.create_task(self._in_cache())
        else:
            self._coregrilo.get_song_art(self._coresong)

    async def _in_cache(self) -> None:
        success, thumb_file = MediaArt.get_file(
            self._artist, self._album, "album")
        if not success:
            return

        try:
            result = await thumb_file.query_info_async(
                Gio.FILE_ATTRIBUTE_STANDARD_TYPE, Gio.FileQueryInfoFlags.NONE,
                GLib.PRIORITY_DEFAULT_IDLE)
        except GLib.Error:
            # This indicates that the file has not been created, so
            # there is no art in the MediaArt cache.
            result = False

        if result:
            self._coresong.props.thumbnail = thumb_file.get_uri()
        else:
            embedded = EmbeddedArt()
            embedded.connect("art-found", self._on_embedded_art_found)
            embedded.query(self._coresong, self._album)
