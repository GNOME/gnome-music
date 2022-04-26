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

from gi.repository import Gdk, Gio, GLib, GObject

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

    def __init__(self) -> None:
        """Intialize MediaArtLoader
        """
        super().__init__()

        self._bytearray = bytearray()
        self._texture: Optional[Gdk.Texture] = None

    def start(self, uri: str) -> None:
        """Start the cache query

        :param str uri: The MediaArt uri
        """
        thumb_file = Gio.File.new_for_uri(uri)
        if thumb_file:
            thumb_file.read_async(
                GLib.PRIORITY_DEFAULT_IDLE, None, self._open_stream)
        else:
            self.emit("finished", self._texture)

    def _open_stream(
            self, thumb_file: Gio.File, result: Gio.AsyncResult) -> None:
        try:
            stream = thumb_file.read_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self.emit("finished", self._texture)
        else:
            stream.read_bytes_async(
                self._chunksize, GLib.PRIORITY_DEFAULT_IDLE, None,
                self._read_bytes_async_cb)

    def _read_bytes_async_cb(
            self, stream: Gio.FileInputStream,
            result: Gio.AsyncResult) -> None:
        try:
            gbytes = stream.read_bytes_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            stream.close_async(
                GLib.PRIORITY_DEFAULT_IDLE, None, self._close_stream)
            return

        gbytes_size = gbytes.get_size()
        if gbytes_size > 0:
            self._bytearray += gbytes.unref_to_data()

            stream.read_bytes_async(
                self._chunksize, GLib.PRIORITY_DEFAULT_IDLE, None,
                self._read_bytes_async_cb)
        else:
            # FIXME: Use GTask to load textures async.
            # See pygobject#114 for bytes conversion.
            self._texture = Gdk.Texture.new_from_bytes(
                GLib.Bytes(bytes(self._bytearray)))

            self._bytearray = bytearray()

            stream.close_async(
                GLib.PRIORITY_DEFAULT_IDLE, None, self._close_stream)

    def _close_stream(
            self, stream: Gio.InputStream, result: Gio.AsyncResult) -> None:
        try:
            stream.close_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))

        self.emit("finished", self._texture)
