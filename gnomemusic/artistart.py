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
import logging
from math import pi
import os

import cairo
import gi
gi.require_version("MediaArt", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, GObject, Gtk, MediaArt

from gnomemusic.albumartcache import Art


def _make_icon_frame(icon_surface, art_size=None, scale=1, default_icon=False):
    icon_w = icon_surface.get_width()
    icon_h = icon_surface.get_height()
    ratio = icon_h / icon_w

    # scale = 2
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

    ctx.arc(w / 2, h / 2, w / 2, 0, 2 * pi)
    ctx.clip()

    matrix = cairo.Matrix()

    # if default_icon:
    #     matrix.translate(-w * (1 / 3), -h * (1 / 3))
    #     ctx.set_operator(cairo.Operator.DIFFERENCE)
    # else:
    matrix.scale(icon_w / w, icon_h / h)

    ctx.set_source_surface(icon_surface, 0, 0)
    pattern = ctx.get_source()
    pattern.set_matrix(matrix)
    ctx.rectangle(0, 0, w, h)
    ctx.fill()

    return surface


class ArtistArt(GObject.GObject):

    def __init__(self, coreartist):
        super().__init__()

        self._coreartist = coreartist
        self._artist = self._coreartist.props.artist

        if self._in_cache():
            print("In cache!")
            return

        # FIXME: Ugly.
        grilo = self._coreartist._coremodel._grilo

        self._coreartist.connect(
            "notify::thumbnail", self._on_thumbnail_changed)

        grilo.get_artist_art(self._coreartist)

    def _in_cache(self):
        success, thumb_file = MediaArt.get_file(
            self._artist, None, "artist")
        if (not success
                or not thumb_file.query_exists()):
            return False

        print("setting cached uri")
        self._coreartist.props.cached_thumbnail_uri = thumb_file.get_path()

        return True

    def _on_thumbnail_changed(self, coreartist, thumbnail):
        uri = coreartist.props.thumbnail
        print("ArtistArt", uri)

        if (uri is None
                or uri == ""):
            return

        src = Gio.File.new_for_uri(uri)
        src.read_async(
            GLib.PRIORITY_LOW, None, self._read_callback, None)

    def _read_callback(self, src, result, data):
        try:
            istream = src.read_finish(result)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))
            return

        try:
            [tmp_file, iostream] = Gio.File.new_tmp()
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))
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
            logger.warning("Error: {}, {}".format(error.domain, error.message))

    def _splice_callback(self, src, result, data):
        tmp_file, iostream = data

        iostream.close_async(
            GLib.PRIORITY_LOW, None, self._close_iostream_callback, None)

        try:
            src.splice_finish(result)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))
            return

        success, cache_path = MediaArt.get_path(self._artist, None, "artist")

        if not success:
            return

        try:
            # FIXME: I/O blocking
            MediaArt.file_to_jpeg(tmp_file.get_path(), cache_path)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))
            return

        self._in_cache()

        tmp_file.delete_async(
            GLib.PRIORITY_LOW, None, self._delete_callback, None)

    def _close_iostream_callback(self, src, result, data):
        try:
            src.close_finish(result)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))


class ArtistCache(GObject.GObject):
    """Handles retrieval of MediaArt cache art

    Uses signals to indicate success or failure.
    """

    __gtype_name__ = "ArtistCache"

    __gsignals__ = {
        'miss': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'hit': (GObject.SignalFlags.RUN_FIRST, None, (object, ))
    }

    def __repr__(self):
        return "<ArtistCache>"

    def __init__(self):
        super().__init__()

        # FIXME
        self._size = Art.Size.MEDIUM
        self._scale = 1

        # FIXME: async
        self.cache_dir = os.path.join(GLib.get_user_cache_dir(), 'media-art')
        if not os.path.exists(self.cache_dir):
            try:
                Gio.file_new_for_path(self.cache_dir).make_directory(None)
            except GLib.Error as error:
                logger.warning(
                    "Error: {}, {}".format(error.domain, error.message))
                return

    def query(self, coreartist):
        """Start the cache query

        :param CoreSong coresong: The CoreSong object to search art for
        """
        print("query")
        thumb_file = Gio.File.new_for_path(
            coreartist.props.cached_thumbnail_uri)
        if thumb_file:
            thumb_file.read_async(
                GLib.PRIORITY_LOW, None, self._open_stream, None)
            return

        self.emit('miss')

    def _open_stream(self, thumb_file, result, arguments):
        try:
            stream = thumb_file.read_finish(result)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))
            self.emit('miss')
            return

        GdkPixbuf.Pixbuf.new_from_stream_async(
            stream, None, self._pixbuf_loaded, None)

    def _pixbuf_loaded(self, stream, result, data):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(result)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))
            self.emit('miss')
            return

        stream.close_async(GLib.PRIORITY_LOW, None, self._close_stream, None)

        surface = Gdk.cairo_surface_create_from_pixbuf(
            pixbuf, self._scale, None)
        surface = _make_icon_frame(surface, self._size, self._scale)

        self.emit("hit", surface)

    def _close_stream(self, stream, result, data):
        try:
            stream.close_finish(result)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))

    def _cache_hit(self, klass, pixbuf):
        surface = Gdk.cairo_surface_create_from_pixbuf(
            pixbuf, self._scale, None)
        surface = _make_icon_frame(surface, self._size, self._scale)
        self._surface = surface
