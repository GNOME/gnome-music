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

import asyncio

import gi
gi.require_version("MediaArt", "2.0")
from gi.repository import GLib, GObject, Gio, MediaArt

from gnomemusic.asynciolimiter import StrictLimiter


class ArtistArt(GObject.GObject):
    """Artist art retrieval object
    """

    _limiter = StrictLimiter(2 / 1)

    def __init__(self, application, coreartist):
        """Initialize.

        :param Application application: The application object
        :param CoreArtist coreartist: The coreartist to use
        """
        super().__init__()

        self._coreartist = coreartist
        self._coregrilo = application.props.coregrilo
        self._artist = self._coreartist.props.artist

        asyncio.create_task(self._in_cache())

    async def _in_cache(self) -> None:
        success, thumb_file = MediaArt.get_file(self._artist, None, "artist")

        if not success:
            return

        try:
            await thumb_file.query_info_async(
                Gio.FILE_ATTRIBUTE_STANDARD_TYPE, Gio.FileQueryInfoFlags.NONE,
                GLib.PRIORITY_DEFAULT_IDLE)
        except GLib.Error as error:
            if error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.NOT_FOUND):
                await self._limiter.wait()
                # This indicates that the file has not been created, so
                # there is no art in the MediaArt cache.
                self._coregrilo.get_artist_art(self._coreartist)
            else:
                raise
        else:
            self._coreartist.props.thumbnail = thumb_file.get_uri()
