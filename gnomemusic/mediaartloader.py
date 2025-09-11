# Copyright 2022 The GNOME Music developers
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
from typing import Optional

import asyncio
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, GObject

from gnomemusic.musiclogger import MusicLogger


class MediaArtLoader(GObject.GObject):
    """Handles retrieval of MediaArt cache art

    Signals when the media is loaded and passes a texture or None.
    """

    __gtype_name__ = "MediaArtLoader"

    __gsignals__ = {
        "finished": (GObject.SignalFlags.RUN_FIRST, None, (object, ))
    }

    _chunksize = 32768
    _log = MusicLogger()
    _sem = asyncio.Semaphore(10)

    def __init__(self) -> None:
        """Intialize MediaArtLoader
        """
        super().__init__()

        self._cancel = Gio.Cancellable()
        self._texture: Optional[Gdk.Texture] = None

    async def _start(self, uri: str) -> None:
        """Start the cache query

        :param str uri: The MediaArt uri
        """
        thumb_file = Gio.File.new_for_uri(uri)
        if thumb_file:
            async with self._sem:
                try:
                    stream = await thumb_file.read_async(
                        GLib.PRIORITY_DEFAULT_IDLE, self._cancel)
                except GLib.Error as error:
                    if error.matches(
                            Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                        return
                    self._log.warning(
                        "Error: {}, {}".format(error.domain, error.message))
                    self.emit("finished", self._texture)
                    return

                barray = bytearray()
                loop = True
                while loop:
                    try:
                        gbytes = await stream.read_bytes_async(
                            self._chunksize, GLib.PRIORITY_DEFAULT_IDLE,
                            self._cancel)
                    except GLib.Error as error:
                        if error.matches(
                                Gio.io_error_quark(),
                                Gio.IOErrorEnum.CANCELLED):
                            return
                        self._log.warning(
                            "Error: {}, {}".format(
                                error.domain, error.message))
                        await stream.close_async(GLib.PRIORITY_DEFAULT)
                        self.emit("finished", self._texture)
                        return

                    gbytes_size = gbytes.get_size()
                    if gbytes_size > 0:
                        barray += gbytes.unref_to_data()
                    else:
                        loop = False

                try:
                    # See pygobject#114 for bytes conversion.
                    self._texture = Gdk.Texture.new_from_bytes(
                        GLib.Bytes(bytes(barray)))
                except GLib.Error as error:
                    self._log.warning("Error: {}, {} in file: {}".format(
                        error.domain, error.message, thumb_file.get_uri()))

                    if error.matches(
                            GdkPixbuf.pixbuf_error_quark(),
                            GdkPixbuf.PixbufError.UNKNOWN_TYPE):
                        try:
                            await stream.close_async(GLib.PRIORITY_DEFAULT)
                            await thumb_file.delete_async(
                                GLib.PRIORITY_DEFAULT_IDLE)
                        except GLib.Error as error:
                            self._log.warning(
                                f"Failure during removal of invalid cache "
                                f"item: {error.domain}, {error.message},"
                                f" {thumb_file.get_uri()}")
                else:
                    await stream.close_async(GLib.PRIORITY_DEFAULT)

        self.emit("finished", self._texture)

    def start(self, uri: str) -> None:
        """Start the cache query

        :param str uri: The MediaArt uri
        """
        asyncio.create_task(self._start(uri))

    def cancel(self) -> None:
        """Cancel the cache query
        """
        self._cancel.cancel()
