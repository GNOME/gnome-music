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

import gi
gi.require_versions({"MediaArt": "2.0", "Soup": "2.4"})
from gi.repository import Gio, GLib, GObject, MediaArt, Soup, GdkPixbuf

from gnomemusic.musiclogger import MusicLogger
from gnomemusic.coreartist import CoreArtist
from gnomemusic.corealbum import CoreAlbum
from gnomemusic.coresong import CoreSong


class StoreArt(GObject.Object):
    """Stores Art in the MediaArt cache.
    """

    __gsignals__ = {
        "finished": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

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

    def start(self, coreobject, uri):
        self._coreobject = coreobject

        if (uri is None
                or uri == ""):
            self.emit("finished")
            return

        if isinstance(self._coreobject, CoreArtist):
            success, self._file = MediaArt.get_file(
                self._coreobject.props.artist, None, "artist")
        elif isinstance(self._coreobject, CoreAlbum):
            success, self._file = MediaArt.get_file(
                self._coreobject.props.artist, self._coreobject.props.title,
                "album")
        elif isinstance(self._coreobject, CoreSong):
            success, self._file = MediaArt.get_file(
                self._coreobject.props.artist, self._coreobject.props.album,
                "album")
        else:
            success = False

        if not success:
            self.emit("finished")
            return

        cache_dir = GLib.build_filenamev(
            [GLib.get_user_cache_dir(), "media-art"])
        cache_dir_file = Gio.File.new_for_path(cache_dir)
        cache_dir_file.query_info_async(
            Gio.FILE_ATTRIBUTE_ACCESS_CAN_READ, Gio.FileQueryInfoFlags.NONE,
            GLib.PRIORITY_LOW, None, self._cache_dir_info_read, uri)

    def _cache_dir_info_read(self, cache_dir_file, res, uri):
        try:
            cache_dir_file.query_info_finish(res)
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
        self._soup_session.queue_message(msg, self._read_callback, None)

    def _read_callback(self, src, result, data):
        if result.props.status_code != 200:
            self._log.debug(
                "Failed to get remote art: {}".format(
                    result.props.reason_phrase))
            self.emit("finished")
            return

        istream = Gio.MemoryInputStream.new_from_bytes(
            result.props.response_body_data)
        GdkPixbuf.Pixbuf.new_from_stream_async(
            istream, None, self._pixbuf_from_stream_finished)

    def _pixbuf_from_stream_finished(
            self, stream: Gio.MemoryInputStream,
            result: Gio.AsyncResult) -> None:
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(result)
        except GLib.Error as error:
            self._log.warning(f"Error: {error.domain}, {error.message}")
            self.emit("finished")
        else:
            self._file.create_async(
                Gio.FileCreateFlags.NONE, GLib.PRIORITY_LOW, None,
                self._output_stream_created, pixbuf)
        finally:
            stream.close_async(GLib.PRIORITY_LOW, None, self._stream_closed)

    def _output_stream_created(
            self, stream: Gio.FileOutputStream, result: Gio.AsyncResult,
            pixbuf: GdkPixbuf.Pixbuf) -> None:
        try:
            output_stream = stream.create_finish(result)
        except GLib.Error as error:
            # File already exists.
            self._log.info(f"Error: {error.domain}, {error.message}")
        else:
            pixbuf.save_to_streamv_async(
                output_stream, "jpeg", None, None, None,
                self._output_stream_saved, output_stream)

    def _output_stream_saved(
            self, pixbuf: GdkPixbuf.Pixbuf, result: Gio.AsyncResult,
            output_stream: Gio.FileOutputStream) -> None:
        try:
            pixbuf.save_to_stream_finish(result)
        except GLib.Error as error:
            self._log.warning(f"Error: {error.domain}, {error.message}")
        else:
            self._coreobject.props.thumbnail = self._file.get_uri()
        finally:
            self.emit("finished")
            output_stream.close_async(
                GLib.PRIORITY_LOW, None, self._stream_closed)

    def _stream_closed(
            self, stream: Gio.OutputStream, result: Gio.AsyncResult) -> None:
        try:
            stream.close_finish(result)
        except GLib.Error as error:
            self._log.warning(f"Error: {error.domain}, {error.message}")
