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
from gi.repository import (
    GLib, GObject, MediaArt, Gio, Gly, Gst, GstTag, GstPbutils)

from gnomemusic.musiclogger import MusicLogger
from gnomemusic.utils import create_idle_task


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
        self._file = None

    def query(self, coreobject, title):
        """Start the local query

        :param coreobject: The CoreAlbum or CoreSong to search art for
        :param str title: The album title for the CoreAlbum or CoreSong
        """
        self._album = title
        self._artist = coreobject.props.artist
        self._coreobject = coreobject

        try:
            if coreobject.props.url is None:
                self.emit("art-found", False)
                return
        except AttributeError:
            self.emit("art-found", False)
            return

        try:
            discoverer = GstPbutils.Discoverer.new(Gst.SECOND)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self._lookup_cover_in_directory()
            return

        discoverer.connect("discovered", self._discovered)
        discoverer.start()

        success, file = MediaArt.get_file(self._artist, self._album, "album")

        if not success:
            self.emit("art-found", False)
            discoverer.stop()
            return

        self._file = file

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
                "image-type", GstTag.TagImageType)
            if not success:
                continue
            if image_type not in [
                    GstTag.TagImageType.UNDEFINED,
                    GstTag.TagImageType.FRONT_COVER]:
                continue

            buf = sample.get_buffer()
            success, map_info = buf.map(Gst.MapFlags.READ)
            if not success:
                continue

            gbytes = GLib.Bytes.new(map_info.data)
            buf.unmap(map_info)

            create_idle_task(self._save_as_jpg(gbytes))
            discoverer.stop()
            return

        discoverer.stop()
        create_idle_task(self._lookup_cover_in_directory())

    async def _save_as_jpg(self, data: GLib.Bytes) -> None:
        loader = Gly.Loader.new_for_bytes(data)
        loader.set_accepted_memory_formats(Gly.MemoryFormatSelection.R8G8B8)
        try:
            image = await loader.load_async()
            frame = await image.next_frame_async()
        except GLib.Error as error:
            self._log.warning(f"Error: {error.domain}, {error.message}")
            create_idle_task(self._lookup_cover_in_directory())
            return

        try:
            ostream = await self._file.create_async(
                Gio.FileCreateFlags.NONE, GLib.PRIORITY_DEFAULT_IDLE)
        except GLib.Error as error:
            # File already exists.
            self._log.info(
                f"Error: {error.domain}, {error.message} for album: "
                f"{self._album} and artist: {self._artist}")
            self.emit("art-found", True)
            return
        else:
            try:
                creator = Gly.Creator.new("image/jpeg")
                creator.add_frame_with_stride(
                    frame.get_width(),
                    frame.get_height(),
                    frame.get_stride(),
                    frame.get_memory_format(),
                    frame.get_buf_bytes())
                encoded_image = await creator.create_async()
                buffer = encoded_image.get_data()
            except GLib.Error as error:
                self._log.warning(
                    f"Error: {error.domain}, {error.message} for album: "
                    f"{self._album} by artist: {self._artist}")
                await ostream.close_async(GLib.PRIORITY_DEFAULT_IDLE)
                await self._file.delete_async(GLib.PRIORITY_DEFAULT_IDLE)
                self.emit("art-found", False)
                return

            try:
                await ostream.write_bytes_async(
                    buffer, GLib.PRIORITY_DEFAULT_IDLE)
            except GLib.Error as error:
                self._log.info(f"Error: {error.domain}, {error.message}")
                create_idle_task(self._lookup_cover_in_directory())
                return
            finally:
                await ostream.close_async(GLib.PRIORITY_DEFAULT)

        self.emit("art-found", True)

    async def _lookup_cover_in_directory(self) -> None:
        """Find local art in cover.jpeg files."""
        try:
            success = await self._media_art.uri_async(
                MediaArt.Type.ALBUM, MediaArt.ProcessFlags.NONE,
                self._coreobject.props.url, self._artist, self._album,
                GLib.PRIORITY_DEFAULT_IDLE)
            if success:
                self.emit("art-found", True)
                return
        except GLib.Error as error:
            if error.matches(
                    MediaArt.error_quark(), MediaArt.Error.SYMLINK_FAILED):
                # This error indicates that the coverart has already
                # been linked by another concurrent lookup.
                self.emit("art-found", True)
                return
            else:
                self._log.warning("Error: {}, {}".format(
                    MediaArt.Error(error.code), error.message))

        self.emit("art-found", False)
