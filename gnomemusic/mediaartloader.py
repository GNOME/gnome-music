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
from gi.repository import Gdk, Gly, GlyGtk4, Gio, GLib, GObject

from gnomemusic.musiclogger import MusicLogger


class MediaArtLoader(GObject.GObject):
    """Handles retrieval of MediaArt cache art

    Signals when the media is loaded and passes a texture or None.
    """

    __gtype_name__ = "MediaArtLoader"

    __gsignals__ = {
        "finished": (GObject.SignalFlags.RUN_FIRST, None, (object, ))
    }

    _log = MusicLogger()
    _sem = asyncio.Semaphore(10)

    def __init__(self) -> None:
        """Initialize MediaArtLoader
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
                    loader = Gly.Loader.new(thumb_file)
                    image = await loader.load_async(self._cancel)
                    frame = await image.next_frame_async(self._cancel)
                    self._texture = GlyGtk4.frame_get_texture(frame)
                except GLib.Error as error:
                    if error.matches(
                            Gio.io_error_quark(),
                            Gio.IOErrorEnum.CANCELLED):
                        return
                    self._log.warning("Error: {}, {} in file: {}".format(
                        error.domain, error.message, thumb_file.get_uri()))
                    if error.matches(
                            Gly.loader_error_quark(),
                            Gly.LoaderError.UNKNOWN_IMAGE_FORMAT):
                        try:
                            await thumb_file.delete_async(
                                GLib.PRIORITY_DEFAULT_IDLE)
                        except GLib.Error as error:
                            self._log.warning(
                                f"Failure during removal of invalid cache "
                                f"item: {error.domain}, {error.message},"
                                f" {thumb_file.get_uri()}")

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
