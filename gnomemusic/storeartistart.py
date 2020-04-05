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
from gi.repository import Gio, GLib, GObject, MediaArt, Soup

from gnomemusic.musiclogger import MusicLogger
from gnomemusic.coreartist import CoreArtist
from gnomemusic.corealbum import CoreAlbum


class StoreArtistArt(GObject.Object):
    """Stores Art in the MediaArt cache.
    """

    def __init__(self, coreobject):
        """Initialize StoreArtistArt

        :param coreobject: The CoreArtist or CoreSong to store art for
        """
        self._coreobject = coreobject

        self._log = MusicLogger()
        self._soup_session = Soup.Session.new()

        uri = coreobject.props.media.get_thumbnail()
        if (uri is None
                or uri == ""):
            self._coreobject.props.thumbnail = "generic"
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
                self._coreobject.props.thumbnail = "generic"
                return

        msg = Soup.Message.new("GET", uri)
        self._soup_session.queue_message(msg, self._read_callback, None)

    def _read_callback(self, src, result, data):
        if result.props.status_code != 200:
            self._log.debug(
                "Failed to get remote art: {}".format(
                    result.props.reason_phrase))
            return

        try:
            [tmp_file, iostream] = Gio.File.new_tmp()
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self._coreobject.props.thumbnail = "generic"
            return

        istream = Gio.MemoryInputStream.new_from_bytes(
            result.props.response_body_data)
        ostream = iostream.get_output_stream()
        # FIXME: Passing the iostream here, otherwise it gets
        # closed. PyGI specific issue?
        ostream.splice_async(
            istream, Gio.OutputStreamSpliceFlags.CLOSE_SOURCE
            | Gio.OutputStreamSpliceFlags.CLOSE_TARGET, GLib.PRIORITY_LOW,
            None, self._splice_callback, [tmp_file, iostream])

    def _delete_callback(self, src, result, data):
        try:
            src.delete_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))

    def _splice_callback(self, src, result, data):
        tmp_file, iostream = data

        iostream.close_async(
            GLib.PRIORITY_LOW, None, self._close_iostream_callback, None)

        try:
            src.splice_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self._coreobject.props.thumbnail = "generic"
            return

        if isinstance(self._coreobject, CoreArtist):
            success, cache_file = MediaArt.get_file(
                self._coreobject.props.artist, None, "artist")
        elif isinstance(self._coreobject, CoreAlbum):
            success, cache_file = MediaArt.get_file(
                self._coreobject.props.artist, self._coreobject.props.title,
                "album")
        else:
            success = False

        if not success:
            self._coreobject.props.thumbnail = "generic"
            return

        try:
            # FIXME: I/O blocking
            MediaArt.file_to_jpeg(tmp_file.get_path(), cache_file.get_path())
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self._coreobject.props.thumbnail = "generic"
            return

        self._coreobject.props.media.set_thumbnail(cache_file.get_uri())
        self._coreobject.props.thumbnail = cache_file.get_uri()

        tmp_file.delete_async(
            GLib.PRIORITY_LOW, None, self._delete_callback, None)

    def _close_iostream_callback(self, src, result, data):
        try:
            src.close_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
