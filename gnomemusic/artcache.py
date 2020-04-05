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
from enum import Enum
from math import pi

import cairo
from gi.repository import Gdk, GdkPixbuf, Gio, Gtk, GLib, GObject

from gnomemusic.corealbum import CoreAlbum
from gnomemusic.coreartist import CoreArtist
from gnomemusic.musiclogger import MusicLogger


def _make_icon_frame(
        icon_surface, art_size=None, scale=1, default_icon=False,
        round_shape=False):
    """Create an Art frame, square or round.

    :param cairo.Surface icon_surface: The surface to use
    :param art_size: The size of the art
    :param int scale: The scale of the art
    :param bool default_icon: Indicates of this is a default icon
    :param bool round_shape: Square or round indicator

    :return: The framed surface
    :rtype: cairo.Surface
    """
    border = 3
    degrees = pi / 180
    radius = 3
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

    if round_shape:
        line_width = 0.6
        ctx.new_sub_path()
        ctx.arc(w / 2, h / 2, (w / 2) - line_width, 0, 2 * pi)
        ctx.set_source_rgba(0, 0, 0, 0.7)
        ctx.set_line_width(line_width)
        ctx.stroke_preserve()
    else:
        # draw outline
        ctx.new_sub_path()
        ctx.arc(w - radius, radius, radius - 0.5, -90 * degrees, 0 * degrees)
        ctx.arc(
            w - radius, h - radius, radius - 0.5, 0 * degrees, 90 * degrees)
        ctx.arc(radius, h - radius, radius - 0.5, 90 * degrees, 180 * degrees)
        ctx.arc(radius, radius, radius - 0.5, 180 * degrees, 270 * degrees)
        ctx.close_path()
        ctx.set_line_width(0.6)
        ctx.set_source_rgba(0, 0, 0, 0.7)
        ctx.stroke_preserve()

    if default_icon:
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
        ctx.set_source_rgba(0, 0, 0, 0.3)
        ctx.mask_surface(icon_surface, w / 3, h / 3)
        ctx.fill()
    else:
        if round_shape:
            matrix.scale(icon_w / (w * scale), icon_h / (h * scale))
        else:
            matrix.scale(
                icon_w / ((w - border * 2) * scale),
                icon_h / ((h - border * 2) * scale))
            matrix.translate(-border, -border)

        ctx.set_source_surface(icon_surface, 0, 0)

        pattern = ctx.get_source()
        pattern.set_matrix(matrix)
        ctx.fill()

    if round_shape:
        ctx.arc(w / 2, h / 2, w / 2, 0, 2 * pi)
    else:
        ctx.rectangle(border, border, w - border * 2, h - border * 2)

    ctx.clip()

    return surface


class DefaultIcon(GObject.GObject):
    """Provides the symbolic fallback and loading icons."""

    class Type(Enum):
        ARTIST = "avatar-default-symbolic"
        ARTIST_LOADING = "content-loading-symbolic"
        LOADING = "content-loading-symbolic"
        MUSIC = "folder-music-symbolic"

    _cache = {}
    _default_theme = Gtk.IconTheme.get_default()

    def __init__(self):
        super().__init__()

    def _make_default_icon(self, icon_type, art_size, scale, round_shape):
        icon_info = self._default_theme.lookup_icon_for_scale(
            icon_type.value, art_size.width / 3, scale, 0)
        icon = icon_info.load_surface()

        icon_surface = _make_icon_frame(
            icon, art_size, scale, True, round_shape=round_shape)

        return icon_surface

    def get(self, icon_type, art_size, scale=1, round_shape=False):
        """Returns the requested symbolic icon

        Returns a cairo surface of the requested symbolic icon in the
        given size and shape.

        :param enum icon_type: The DefaultIcon.Type of the icon
        :param enum art_size: The Art.Size requested
        :param int scale: The scale
        :param bool round_shape: Indicates square or round icon shape

        :return: The symbolic icon
        :rtype: cairo.Surface
        """
        if (icon_type, art_size, scale) not in self._cache.keys():
            new_icon = self._make_default_icon(
                icon_type, art_size, scale, round_shape)
            self._cache[(icon_type, art_size, scale, round_shape)] = new_icon

        return self._cache[(icon_type, art_size, scale, round_shape)]


class ArtCache(GObject.GObject):
    """Handles retrieval of MediaArt cache art

    Uses signals to indicate success or failure and always returns a
    Cairo.Surface.
    """

    __gtype_name__ = "ArtCache"

    __gsignals__ = {
        "result": (GObject.SignalFlags.RUN_FIRST, None, (object, ))
    }

    _log = MusicLogger()

    def __init__(self, size, scale):
        super().__init__()

        self._size = size
        self._scale = scale

        self._coreobject = None
        self._default_icon = None
        self._loading_icon = None

    def query(self, coreobject):
        """Start the cache query

        :param coreobject: The object to search art for
        """
        self._coreobject = coreobject

        if isinstance(coreobject, CoreArtist):
            self._loading_icon = DefaultIcon().get(
                DefaultIcon.Type.ARTIST_LOADING, self._size, self._scale, True)
            self._default_icon = DefaultIcon().get(
                DefaultIcon.Type.ARTIST, self._size, self._scale, True)
        elif isinstance(coreobject, CoreAlbum):
            self._loading_icon = DefaultIcon().get(
                DefaultIcon.Type.LOADING, self._size, self._scale)
            self._default_icon = DefaultIcon().get(
                DefaultIcon.Type.MUSIC, self._size, self._scale)

        thumbnail_uri = coreobject.props.thumbnail
        if thumbnail_uri in ["loading", "", None]:
            self.emit("result", self._loading_icon)
            return
        elif thumbnail_uri == "generic":
            self.emit("result", self._default_icon)
            return

        thumb_file = Gio.File.new_for_uri(thumbnail_uri)
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
        if isinstance(self._coreobject, CoreArtist):
            surface = _make_icon_frame(
                surface, self._size, self._scale, round_shape=True)
        elif isinstance(self._coreobject, CoreAlbum):
            surface = _make_icon_frame(surface, self._size, self._scale)

        self.emit("result", surface)

    def _close_stream(self, stream, result, data):
        try:
            stream.close_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
