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

from __future__ import annotations
from typing import Optional, Union
import asyncio
import typing

import gi
gi.require_versions({"MediaArt": "2.0", "Soup": "3.0"})
from gi.repository import Gio, GLib, GObject, MediaArt, Soup, GdkPixbuf

from gnomemusic.musiclogger import MusicLogger
from gnomemusic.utils import CoreObjectType
if typing.TYPE_CHECKING:
    from gnomemusic.corealbum import CoreAlbum
    from gnomemusic.coreartist import CoreArtist
    from gnomemusic.coresong import CoreSong

if typing.TYPE_CHECKING:
    CoreObject = Union[CoreAlbum, CoreArtist, CoreSong]


class StoreArt(GObject.Object):
    """Stores Art in the MediaArt cache.
    """

    __gsignals__ = {
        "finished": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    _sem = asyncio.Semaphore(10)

    def __init__(self):
        """Initialize StoreArtistArt

        :param coreobject: The CoreArtist or CoreAlbum to store art for
        :param string uri: The art uri
        """
        super().__init__()

        self._coreobject = None

        self._file = None
        self._log = MusicLogger()
        self._soup_session = Soup.Session.new()

    async def _start(
            self, coreobject: CoreObject, uri: str,
            coreobjecttype: CoreObjectType) -> None:
        self._coreobject = coreobject

        if uri in [None, ""]:
            self.emit("finished")
            return

        album: Optional[str] = None
        artist = self._coreobject.props.artist
        art_prefix = "artist"
        success = False

        if coreobjecttype == CoreObjectType.ALBUM:
            album = self._coreobject.props.title
            art_prefix = "album"
        elif coreobjecttype == CoreObjectType.SONG:
            album = self._coreobject.props.album
            art_prefix = "album"

        success, self._file = MediaArt.get_file(artist, album, art_prefix)

        if not success:
            self.emit("finished")
            return

        async with self._sem:
            cache_dir = GLib.build_filenamev(
                [GLib.get_user_cache_dir(), "media-art"])
            cache_dir_file = Gio.File.new_for_path(cache_dir)

            try:
                await cache_dir_file.query_info_async(
                    Gio.FILE_ATTRIBUTE_ACCESS_CAN_READ,
                    Gio.FileQueryInfoFlags.NONE, GLib.PRIORITY_DEFAULT_IDLE)
            except GLib.Error:
                # directory does not exist yet
                try:
                    cache_dir_file.make_directory(None)
                except GLib.Error as error:
                    self._log.warning(
                        "Error: {}, {}".format(error.domain, error.message))
                    self.emit("finished")
                    return

            msg = Soup.Message.new("GET", uri)
            try:
                gbytes = await self._soup_session.send_and_read_async(
                    msg, GLib.PRIORITY_DEFAULT)
            except GLib.Error as error:
                self._log.debug(
                    f"Failed to get remote art: {error.domain}, "
                    f"{error.message} for album: {album} by artist: {artist}")
                self.emit("finished")
                return

            istream = Gio.MemoryInputStream.new_from_bytes(gbytes)
            try:
                pixbuf = await GdkPixbuf.Pixbuf.new_from_stream_async(istream)
            except GLib.Error as error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                self.emit("finished")
                return
            finally:
                await istream.close_async(GLib.PRIORITY_DEFAULT)

            try:
                ostream = await self._file.create_async(
                    Gio.FileCreateFlags.NONE, GLib.PRIORITY_DEFAULT_IDLE)
            except GLib.Error as error:
                # File already exists.
                self._log.info(f"Error: {error.domain}, {error.message}")
                self.emit("finished")
                return
            else:
                try:
                    _, buffer = pixbuf.save_to_bufferv("jpeg")
                except GLib.Error as error:
                    self._log.warning(
                        f"Error: {error.domain}, {error.message} for album: "
                        f"{album} by artist: {artist}")
                    await ostream.close_async(GLib.PRIORITY_DEFAULT_IDLE)
                    await self._file.delete_async(GLib.PRIORITY_DEFAULT_IDLE)
                    self.emit("finished")
                    return

                try:
                    await ostream.write_async(
                        buffer, GLib.PRIORITY_DEFAULT_IDLE)
                except GLib.Error as error:
                    self._log.info(f"Error: {error.domain}, {error.message}")
                    self.emit("finished")
                    return

                self._coreobject.props.thumbnail = self._file.get_uri()
                await ostream.close_async(GLib.PRIORITY_DEFAULT)

        self.emit("finished")

    def start(
            self, coreobject: CoreObject, uri: str,
            coreobjecttype: CoreObjectType) -> None:
        """Start storing the art from the given URI

        :param coreobject: Any of CoreSong, CoreAlbum or CoreArtist
            the URI is relevant for
        :param str uri: The URI containing the art
        :param CoreObjectType coreobjecttype: The type of the
            coreobject
        """
        asyncio.create_task(self._start(coreobject, uri, coreobjecttype))
