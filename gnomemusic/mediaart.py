import logging
from enum import Enum
from math import pi

import cairo
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, GObject, Gtk

logger = logging.getLogger(__name__)

def _make_icon_frame(icon_surface, art_size=None, scale=1, default_icon=False):
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

    # draw outline
    ctx.new_sub_path()
    ctx.arc(w - radius, radius, radius - 0.5, -90 * degrees, 0 * degrees)
    ctx.arc(w - radius, h - radius, radius - 0.5, 0 * degrees, 90 * degrees)
    ctx.arc(radius, h - radius, radius - 0.5, 90 * degrees, 180 * degrees)
    ctx.arc(radius, radius, radius - 0.5, 180 * degrees, 270 * degrees)
    ctx.close_path()
    ctx.set_line_width(0.6)
    ctx.set_source_rgba(0, 0, 0, 0.7)
    ctx.stroke_preserve()

    matrix = cairo.Matrix()

    if default_icon:
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
        ctx.set_source_rgba(0, 0, 0, 0.3)
        ctx.mask_surface(icon_surface, w / 3, h / 3)
        ctx.fill()
    else:
        matrix.scale(
            icon_w / ((w - border * 2) * scale),
            icon_h / ((h - border * 2) * scale))
        matrix.translate(-border, -border)
        ctx.set_source_surface(icon_surface, 0, 0)

        pattern = ctx.get_source()
        pattern.set_matrix(matrix)
        ctx.fill()

    ctx.rectangle(border, border, w - border * 2, h - border * 2)
    ctx.clip()

    return surface


class DefaultIcon(GObject.GObject):
    """Provides the symbolic fallback and loading icons."""

    class Type(Enum):
        LOADING = 'content-loading-symbolic'
        MUSIC = 'folder-music-symbolic'

    _cache = {}
    _default_theme = Gtk.IconTheme.get_default()

    def __repr__(self):
        return '<DefaultIcon>'

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

class MediaArt(GObject.GObject):
    """Handles retrieval of MediaArt cache art

    Uses signals to indicate success or failure.
    """

    __gtype_name__ = "MediaArt"

    __gsignals__ = {
        "result": (GObject.SignalFlags.RUN_FIRST, None, (object, ))
    }

    def __init__(self, size, scale):
        super().__init__()

        self._size = size
        self._scale = scale

        self._default_icon = DefaultIcon().get(
            DefaultIcon.Type.MUSIC, self._size, self._scale)

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
                logger.warning(
                    "Error: {}, {}".format(error.domain, error.message))

    def query(self, corealbum):
        """Start the cache query

        :param CoreSong coresong: The CoreSong object to search art for
        """
        thumbnail_uri = corealbum.props.thumbnail
        if thumbnail_uri == "generic":
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
            logger.warning("Error: {}, {}".format(error.domain, error.message))
            self.emit("result", self._default_icon)
            return

        GdkPixbuf.Pixbuf.new_from_stream_async(
            stream, None, self._pixbuf_loaded, None)

    def _pixbuf_loaded(self, stream, result, data):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(result)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))
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
            logger.warning("Error: {}, {}".format(error.domain, error.message))
