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

from enum import Enum
from math import pi

import cairo
import gi
gi.require_version("MediaArt", "2.0")
gi.require_version("Soup", "2.4")
from gi.repository import (Gdk, GdkPixbuf, Gio, GLib, GObject, Gtk, MediaArt,
                           Soup)

from gnomemusic.musiclogger import MusicLogger


def _make_icon_frame(icon_surface, art_size=None, scale=1, default_icon=False):
    icon_w = icon_surface.get_width()
    icon_h = icon_surface.get_height()
    ratio = icon_h / icon_w

    # Scale down the image according to the biggest axis
    if ratio > 1:
        w = int(art_size.width / ratio)
        h = art_size.height
    else:
        w = art_size.width
        h = int(art_size.height * ratio)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w * scale, h * scale)
    surface.set_device_scale(scale, scale)
    ctx = cairo.Context(surface)

    matrix = cairo.Matrix()

    line_width = 0.6
    ctx.new_sub_path()
    ctx.arc(w / 2, h / 2, (w / 2) - line_width, 0, 2 * pi)
    ctx.set_source_rgba(0, 0, 0, 0.7)
    ctx.set_line_width(line_width)
    ctx.stroke_preserve()

    if default_icon:
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
        ctx.set_source_rgba(0, 0, 0, 0.3)
        ctx.mask_surface(icon_surface, w / 3, h / 3)
        ctx.fill()
    else:
        matrix.scale(icon_w / (w * scale), icon_h / (h * scale))
        ctx.set_source_surface(icon_surface, 0, 0)

        pattern = ctx.get_source()
        pattern.set_matrix(matrix)
        ctx.fill()

    ctx.arc(w / 2, h / 2, w / 2, 0, 2 * pi)
    ctx.clip()

    return surface


class DefaultIcon(GObject.GObject):
    """Provides the symbolic fallback and loading icons."""

    class Type(Enum):
        LOADING = "content-loading-symbolic"
        ARTIST = "avatar-default-symbolic"

    _cache = {}
    _default_theme = Gtk.IconTheme.get_default()

    def __init__(self):
        super().__init__()

    def _make_default_icon(self, icon_type, art_size, scale):
        icon_info = self._default_theme.lookup_icon_for_scale(
            icon_type.value, art_size.width / 3, scale, 0)
        icon = icon_info.load_surface()

        icon_surface = _make_icon_frame(icon, art_size, scale, True)

        return icon_surface

    def get(self, icon_type, art_size, scale=1):
        """Returns the requested symbolic icon

        Returns a cairo surface of the requested symbolic icon in the
        given size.

        :param enum icon_type: The DefaultIcon.Type of the icon
        :param enum art_size: The Art.Size requested

        :return: The symbolic icon
        :rtype: cairo.Surface
        """
        if (icon_type, art_size, scale) not in self._cache.keys():
            new_icon = self._make_default_icon(icon_type, art_size, scale)
            self._cache[(icon_type, art_size, scale)] = new_icon

        return self._cache[(icon_type, art_size, scale)]


class ArtistArt(GObject.GObject):

    _log = MusicLogger()

    def __init__(self, application, coreartist):
        """Initialize the ArtistArt.

        :param Application application: The application object
        :param CoreArtist coreartist: The coreartist to use
        """
        super().__init__()

        self._coreartist = coreartist
        self._artist = self._coreartist.props.artist
        self._soup_session = Soup.Session.new()

        if self._in_cache():
            return

        self._coreartist.connect(
            "notify::thumbnail", self._on_thumbnail_changed)

        application.props.coregrilo.get_artist_art(self._coreartist)

    def _in_cache(self):
        success, thumb_file = MediaArt.get_file(
            self._artist, None, "artist")
        if (not success
                or not thumb_file.query_exists()):
            return False

        self._coreartist.props.cached_thumbnail_uri = thumb_file.get_path()

        return True

    def _on_thumbnail_changed(self, coreartist, thumbnail):
        uri = coreartist.props.thumbnail

        if (uri is None
                or uri == ""):
            self._coreartist.props.cached_thumbnail_uri = ""
            return

        msg = Soup.Message.new("GET", uri)
        self._soup_session.queue_message(msg, self._read_callback, None)

    def _read_callback(self, src, result, data):
        if result.props.status_code != 200:
            self._log.debug(
                "Failed to get remote art for the artist {} : {}".format(
                    self._artist, result.props.reason_phrase))
            return

        try:
            istream = Gio.MemoryInputStream.new_from_bytes(
                result.props.response_body_data)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self._coreartist.props.cached_thumbnail_uri = ""
            return

        try:
            [tmp_file, iostream] = Gio.File.new_tmp()
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self._coreartist.props.cached_thumbnail_uri = ""
            return

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
            self._coreartist.props.cached_thumbnail_uri = ""
            return

        success, cache_path = MediaArt.get_path(self._artist, None, "artist")

        if not success:
            self._coreartist.props.cached_thumbnail_uri = ""
            return

        try:
            # FIXME: I/O blocking
            MediaArt.file_to_jpeg(tmp_file.get_path(), cache_path)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self._coreartist.props.cached_thumbnail_uri = ""
            return

        self._in_cache()

        tmp_file.delete_async(
            GLib.PRIORITY_LOW, None, self._delete_callback, None)

    def _close_iostream_callback(self, src, result, data):
        try:
            src.close_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))


class ArtistCache(GObject.GObject):
    """Handles retrieval of MediaArt cache art

    Uses signals to indicate success or failure.
    """

    __gtype_name__ = "ArtistCache"

    __gsignals__ = {
        "result": (GObject.SignalFlags.RUN_FIRST, None, (object, ))
    }

    _log = MusicLogger()

    def __init__(self, size, scale):
        super().__init__()

        self._size = size
        self._scale = scale

        self._default_icon = DefaultIcon().get(
            DefaultIcon.Type.ARTIST, self._size, self._scale)

        cache_dir = GLib.build_filenamev(
            [GLib.get_user_cache_dir(), "media-art"])
        cache_dir_file = Gio.File.new_for_path(cache_dir)
        cache_dir_file.query_info_async(
            Gio.FILE_ATTRIBUTE_ACCESS_CAN_READ, Gio.FileQueryInfoFlags.NONE,
            GLib.PRIORITY_LOW, None, self._cache_dir_info_read, None)

    def _cache_dir_info_read(self, cache_dir_file, res, data):
        try:
            cache_dir_file.query_info_finish(res)
            return
        except GLib.Error:
            # directory does not exist yet
            try:
                cache_dir_file.make_directory(None)
            except GLib.Error as error:
                self._log.warning(
                    "Error: {}, {}".format(error.domain, error.message))

    def query(self, coreartist):
        """Start the cache query

        :param CoreSong coresong: The CoreSong object to search art for
        """
        thumbnail_uri = coreartist.props.cached_thumbnail_uri
        if thumbnail_uri == "":
            self.emit("result", self._default_icon)
            return
        elif thumbnail_uri is None:
            return

        thumb_file = Gio.File.new_for_path(thumbnail_uri)
        if thumb_file:
            thumb_file.read_async(
                GLib.PRIORITY_LOW, None, self._open_stream, None)
            return

        self.emit("result", self._default_icon)

    def _open_stream(self, thumb_file, result, arguments):
        try:
            stream = thumb_file.read_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self.emit("result", self._default_icon)
            return

        GdkPixbuf.Pixbuf.new_from_stream_async(
            stream, None, self._pixbuf_loaded, None)

    def _pixbuf_loaded(self, stream, result, data):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self.emit("result", self._default_icon)
            return

        stream.close_async(GLib.PRIORITY_LOW, None, self._close_stream, None)

        surface = Gdk.cairo_surface_create_from_pixbuf(
            pixbuf, self._scale, None)
        surface = _make_icon_frame(surface, self._size, self._scale)

        self.emit("result", surface)

    def _close_stream(self, stream, result, data):
        try:
            stream.close_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
