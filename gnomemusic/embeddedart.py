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
gi.require_versions({"GstPbutils": "1.0", "GstTag": "1.0", "MediaArt": "2.0"})
from gi.repository import GLib, GObject, MediaArt, Gst, GstTag, GstPbutils

from gnomemusic.musiclogger import MusicLogger


class EmbeddedArt(GObject.GObject):
    """Lookup local art

    1. Embedded art using GStreamer
    2. Available in the directory using MediaArt
    """

    _log = MusicLogger()

    __gsignals__ = {
        "art-found": (GObject.SignalFlags.RUN_FIRST, None, (bool, ))
    }

    def __init__(self):
        """Initialize EmbeddedArt
        """
        super().__init__()

        try:
            Gst.init(None)
            GstPbutils.pb_utils_init()
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            return

        self._media_art = MediaArt.Process.new()

        self._album = None
        self._artist = None
        self._coreobject = None
        self._path = None

    def query(self, coreobject):
        """Start the local query

        :param coreobject: The CoreAlbum or CoreSong to search art for
        """
        self._coreobject = coreobject

        try:
            if coreobject.props.url is None:
                self.emit("art-found", False)
                return
        except AttributeError:
            self.emit("art-found", False)
            return

        # Either this is a CoreSong or thie is a CoreAlbum, set
        # self._album accordingly.
        try:
            self._album = self._coreobject.props.album
        except Exception:
            self._album = self._coreobject.props.title
        self._artist = self._coreobject.props.artist

        try:
            discoverer = GstPbutils.Discoverer.new(Gst.SECOND)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self._lookup_cover_in_directory()
            return

        discoverer.connect('discovered', self._discovered)
        discoverer.start()

        success, path = MediaArt.get_path(self._artist, self._album, "album")

        if not success:
            self.emit("art-found", False)
            discoverer.stop()
            return

        self._path = path

        success = discoverer.discover_uri_async(self._coreobject.props.url)

        if not success:
            self._log.warning("Could not add url to discoverer.")
            self.emit("art-found", False)
            discoverer.stop()
            return

    def _discovered(self, discoverer, info, error):
        tags = info.get_tags()
        index = 0

        if (error is not None
                or tags is None):
            if error:
                self._log.warning("Discoverer error: {}, {}".format(
                    Gst.CoreError(error.code), error.message))
            discoverer.stop()
            self.emit("art-found", False)
            return

        while True:
            success, sample = tags.get_sample_index(Gst.TAG_IMAGE, index)
            if not success:
                break
            index += 1
            struct = sample.get_info()
            if struct is None:
                break
            success, image_type = struct.get_enum(
                'image-type', GstTag.TagImageType)
            if not success:
                continue
            if image_type != GstTag.TagImageType.FRONT_COVER:
                continue

            buf = sample.get_buffer()
            success, map_info = buf.map(Gst.MapFlags.READ)
            if not success:
                continue

            try:
                mime = sample.get_caps().get_structure(0).get_name()
                MediaArt.buffer_to_jpeg(map_info.data, mime, self._path)
                discoverer.stop()
                self.emit("art-found", True)
                return
            except GLib.Error as error:
                self._log.warning("Error: {}, {}".format(
                    MediaArt.Error(error.code), error.message))

        discoverer.stop()

        self._lookup_cover_in_directory()

    def _lookup_cover_in_directory(self):
        # Find local art in cover.jpeg files.
        self._media_art.uri_async(
            MediaArt.Type.ALBUM, MediaArt.ProcessFlags.NONE,
            self._coreobject.props.url, self._artist, self._album,
            GLib.PRIORITY_LOW, None, self._uri_async_cb, None)

    def _uri_async_cb(self, src, result, data):
        try:
            success = self._media_art.uri_finish(result)
            if success:
                self.emit("art-found", True)
                return
        except GLib.Error as error:
            if MediaArt.Error(error.code) == MediaArt.Error.SYMLINK_FAILED:
                # This error indicates that the coverart has already
                # been linked by another concurrent lookup.
                self.emit("art-found", True)
                return
            else:
                self._log.warning("Error: {}, {}".format(
                    MediaArt.Error(error.code), error.message))

        self.emit("art-found", False)
