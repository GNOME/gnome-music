# Copyright © 2018 The GNOME Music developers
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
from PIL import Image, ImageFilter
import gi
gi.require_version('GstTag', '1.0')
gi.require_version('MediaArt', '2.0')
from gi.repository import (Gdk, GdkPixbuf, Gio, GLib, GObject, Gtk, MediaArt,
                           Gst, GstTag, GstPbutils)

from gnomemusic import log
from gnomemusic.grilo import grilo
import gnomemusic.utils as utils


logger = logging.getLogger(__name__)


@log
def _make_icon_frame(pixbuf, art_size=None, scale=1):
    border = 3
    degrees = pi / 180
    radius = 3

    ratio = pixbuf.get_height() / pixbuf.get_width()

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
    ctx.set_source_rgb(0.2, 0.2, 0.2)
    ctx.stroke_preserve()

    # fill the center
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()

    matrix = cairo.Matrix()
    matrix.scale(pixbuf.get_width() / (w - border * 2),
                 pixbuf.get_height() / (h - border * 2))
    matrix.translate(-border, -border)

    # paste the scaled pixbuf in the center
    Gdk.cairo_set_source_pixbuf(ctx, pixbuf, 0, 0)
    pattern = ctx.get_source()
    pattern.set_matrix(matrix)
    ctx.rectangle(border, border, w - border * 2, h - border * 2)
    ctx.fill()

    return surface


class DefaultIcon(GObject.GObject):
    """Provides the symbolic fallback and loading icons."""

    class Type(Enum):
        LOADING = 'content-loading-symbolic'
        MUSIC = 'folder-music-symbolic'

    _cache = {}

    def __repr__(self):
        return '<DefaultIcon>'

    @log
    def __init__(self):
        super().__init__()

    @log
    def _make_default_icon(self, icon_type, art_size, scale):
        width = art_size.width * scale
        height = art_size.height * scale

        icon = Gtk.IconTheme.get_default().load_icon(icon_type.value,
                                                     max(width, height) / 4,
                                                     0)

        # create an empty pixbuf with the requested size
        result = GdkPixbuf.Pixbuf.new(icon.get_colorspace(),
                                      True,
                                      icon.get_bits_per_sample(),
                                      width,
                                      height)
        result.fill(0xffffffff)

        icon.composite(result,
                       icon.get_width() * 3 / 2,
                       icon.get_height() * 3 / 2,
                       icon.get_width(),
                       icon.get_height(),
                       icon.get_width() * 3 / 2,
                       icon.get_height() * 3 / 2,
                       1, 1, GdkPixbuf.InterpType.HYPER, 0x33)

        icon_surface = _make_icon_frame(result, art_size, scale)

        return icon_surface

    @log
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


class Art(GObject.GObject):
    """Retrieves art for an album or song

    This is the control class for retrieving art.
    It looks for art in
    1. The MediaArt cache
    2. Embedded or in the directory
    3. Remotely
    """

    __gsignals__ = {
        'finished': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    _blacklist = {}

    class Size(Enum):
        """Enum for icon sizes"""
        XSMALL = (34, 34)
        SMALL = (48, 48)
        MEDIUM = (128, 128)
        LARGE = (256, 256)
        XLARGE = (512, 512)
        XXLARGE = (1024, 1024)

        def __init__(self, width, height):
            """Intialize width and height"""
            self.width = width
            self.height = height

    def __repr__(self):
        return '<Art>'

    @log
    def __init__(self, size, media, scale=1):
        super().__init__()

        self._size = size
        self._media = media
        self._media_url = self._media.get_url()
        self._surface = None
        self._scale = scale

    @log
    def lookup(self):
        """Starts the art lookup sequence"""
        if self._in_blacklist():
            self._no_art_available()
            return

        cache = Cache()
        cache.connect('miss', self._cache_miss)
        cache.connect('hit', self._cache_hit)
        cache.query(self._media)

    @log
    def _cache_miss(self, klass):
        embedded_art = EmbeddedArt()
        embedded_art.connect('found', self._embedded_art_found)
        embedded_art.connect('unavailable', self._embedded_art_unavailable)
        embedded_art.query(self._media)

    @log
    def _cache_hit(self, klass, pixbuf):
        surface = _make_icon_frame(pixbuf, self._size, self._scale)
        self._surface = surface
        self._set_grilo_thumbnail_path()

        self.emit('finished')

    @log
    def _embedded_art_found(self, klass):
        cache = Cache()
        # In case of an error in local art retrieval, there are two
        # options:
        # 1. Go and check for remote art instead
        # 2. Consider it a fail and add it to the blacklist
        # Go with option 1 here, because it gives the user the biggest
        # chance of getting artwork.
        cache.connect('miss', self._embedded_art_unavailable)
        cache.connect('hit', self._cache_hit)
        cache.query(self._media)

    @log
    def _embedded_art_unavailable(self, klass):
        remote_art = RemoteArt()
        remote_art.connect('retrieved', self._remote_art_retrieved)
        remote_art.connect('unavailable', self._remote_art_unavailable)
        remote_art.query(self._media)

    @log
    def _remote_art_retrieved(self, klass):
        cache = Cache()
        cache.connect('miss', self._remote_art_unavailable)
        cache.connect('hit', self._cache_hit)
        cache.query(self._media)

    @log
    def _remote_art_unavailable(self, klass):
        self._add_to_blacklist()
        self._no_art_available()

    @log
    def _no_art_available(self):
        self._surface = DefaultIcon().get(
            DefaultIcon.Type.MUSIC, self._size, self._scale)

        self.emit('finished')

    @log
    def _add_to_blacklist(self):
        album = utils.get_album_title(self._media)
        artist = utils.get_artist_name(self._media)

        if artist not in self._blacklist:
            self._blacklist[artist] = []

        album_stripped = MediaArt.strip_invalid_entities(album)
        self._blacklist[artist].append(album_stripped)

    @log
    def _in_blacklist(self):
        album = utils.get_album_title(self._media)
        artist = utils.get_artist_name(self._media)
        album_stripped = MediaArt.strip_invalid_entities(album)

        if artist in self._blacklist:
            if album_stripped in self._blacklist[artist]:
                return True

        return False

    def _set_grilo_thumbnail_path(self):
        # TODO: This sets the thumbnail path for the Grilo Media object
        # to be used by MPRIS. However, calling this by default for
        # every cache hit is unnecessary.
        album = utils.get_album_title(self._media)
        artist = utils.get_artist_name(self._media)

        success, thumb_file = MediaArt.get_file(artist, album, "album")
        if success:
            self._media.set_thumbnail(
                GLib.filename_to_uri(thumb_file.get_path(), None))

    @GObject.Property
    @log
    def surface(self):
        if self._surface is None:
            self._surface = DefaultIcon().get(
                DefaultIcon.Type.LOADING, self._size, self._scale)

        return self._surface


class ArtImage(Art):
    """Extends Art class to support Gtk.Image specifically"""

    def __repr__(self):
        return '<ArtImage>'

    @log
    def __init__(self, size, media):
        super().__init__(size, media)

        self._image = None
        self._blurred_surface = None
        self._blurred_size = None
        self._label_color = None

    @log
    def _cache_hit(self, klass, pixbuf):
        super()._cache_hit(klass, pixbuf)

        self._image.set_from_surface(self._surface)

    @log
    def _no_art_available(self):
        super()._no_art_available()

        self._image.set_from_surface(self._surface)

    @GObject.Property
    @log
    def image(self):
        """Returns the image object of the ArtImage class

        :returns: The current image available in the class
        :rtype: Gtk.Image
        """

        return self._image.set_from_surface(self._surface)

    @image.setter
    @log
    def image(self, image):
        """Set the image of the Art class instance""

        And starts the lookup process, automatically updating the image
        when found.
        :param Gtk.Image image: An Gtk.Image object
        """

        self._image = image

        self._image.set_property("width-request", self._size.width)
        self._image.set_property("height-request", self._size.height)

        self._scale = self._image.get_scale_factor()

        self._surface = DefaultIcon().get(
            DefaultIcon.Type.LOADING, self._size, self._scale)

        self._image.set_from_surface(self._surface)

        self.lookup()

    @log
    def get_blurred_surface(self, width, height):
        """Compute the blurred cairo surface of an ArtImage.

        self._surface is resized and then blurred with a gaussian
        filter. The dominant color of the blurred image is extracted
        to detect which color (white or black) can be displayed on this
        surface.
        :param int width: requested width surface
        :param int height: requested height surface
        :returns: blurred cairo surface and foreground color
        :rtype: (cairo.surface, Gdk.RGBA)
        """
        if not self._surface:
            return None, None

        size = (self._surface.get_width(), self._surface.get_height())
        full_size = (width, height)

        if (self._blurred_surface
                and self._blurred_size[0] >= full_size[0]
                and self._blurred_size[1] >= full_size[1]):
            return self._blurred_surface, self._label_color

        # convert cairo surface to a pillow image
        img = Image.frombuffer(
            "RGBA", size, self._surface.get_data(), "raw", "RGBA", 0, 1)

        # resize and blur the image
        ratio = full_size[0] / full_size[1]
        h = int((1 / ratio) * full_size[1])
        diff = full_size[1] - h
        img_cropped = img.crop(
            (0, diff // 2, size[0], size[1] - diff // 2))
        img_scaled = img_cropped.resize(full_size, Image.BICUBIC)
        img_blurred = img_scaled.filter(ImageFilter.GaussianBlur(30))

        # convert the image to a cairo suface
        arr = bytearray(img_blurred.tobytes('raw', 'RGBA'))
        self._blurred_surface = cairo.ImageSurface.create_for_data(
            arr, cairo.FORMAT_ARGB32, img_blurred.width, img_blurred.height)

        self._blurred_size = (
            self._blurred_surface.get_width(),
            self._blurred_surface.get_height()
        )

        # compute dominant color of the blurred image to update
        # foreground color in white or black
        b, g, r, a = img_blurred.split()
        img_blurred_rgb = Image.merge('RGB', (r, g, b))
        dominant_color = utils.dominant_color(img_blurred_rgb)
        white_ratio = utils.contrast_ratio(*dominant_color, 1., 1., 1.)
        black_ratio = utils.contrast_ratio(*dominant_color, 0., 0., 0.)
        if white_ratio > black_ratio:
            self._label_color = Gdk.RGBA(1.0, 1.0, 1.0, 1.0)
        else:
            self._label_color = Gdk.RGBA(0.0, 0.0, 0.0, 0.0)

        return self._blurred_surface, self._label_color


class Cache(GObject.GObject):
    """Handles retrieval of MediaArt cache art

    Uses signals to indicate success or failure.
    """

    __gsignals__ = {
        'miss': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'hit': (GObject.SignalFlags.RUN_FIRST, None, (GObject.GObject, ))
    }

    def __repr__(self):
        return '<Cache>'

    @log
    def __init__(self):
        super().__init__()

        self._media_art = MediaArt.Process.new()

        # FIXME: async
        self.cache_dir = os.path.join(GLib.get_user_cache_dir(), 'media-art')
        if not os.path.exists(self.cache_dir):
            try:
                Gio.file_new_for_path(self.cache_dir).make_directory(None)
            except GLib.Error as error:
                logger.warning(
                    "Error: {}, {}".format(error.domain, error.message))
                return

    @log
    def query(self, media):
        """Start the cache query

        :param Grl.Media media: The media object to search art for
        """
        album = utils.get_album_title(media)
        artist = utils.get_artist_name(media)

        success, thumb_file = MediaArt.get_file(artist, album, "album")

        if (success
                and thumb_file.query_exists()):
            thumb_file.read_async(
                GLib.PRIORITY_LOW, None, self._open_stream, None)
            return

        self.emit('miss')

    @log
    def _open_stream(self, thumb_file, result, arguments):
        try:
            stream = thumb_file.read_finish(result)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))
            self.emit('miss')
            return

        GdkPixbuf.Pixbuf.new_from_stream_async(
            stream, None, self._pixbuf_loaded, None)

    @log
    def _pixbuf_loaded(self, stream, result, data):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(result)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))
            self.emit('miss')
            return

        stream.close_async(GLib.PRIORITY_LOW, None, self._close_stream, None)
        self.emit('hit', pixbuf)

    @log
    def _close_stream(self, stream, result, data):
        try:
            stream.close_finish(result)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))


class EmbeddedArt(GObject.GObject):
    """Lookup local art

    1. Embedded through Gstreamer
    2. Available in the directory through MediaArt
    """

    __gsignals__ = {
        'found': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'unavailable': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __repr__(self):
        return '<EmbeddedArt>'

    @log
    def __init__(self):
        super().__init__()

        try:
            Gst.init(None)
            GstPbutils.pb_utils_init()
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))
            return

        self._media_art = MediaArt.Process.new()

        self._album = None
        self._artist = None
        self._media = None
        self._path = None

    @log
    def query(self, media):
        """Start the local query

        :param Grl.Media media: The media object to search art for
        """
        if media.get_url() is None:
            self.emit('unavailable')
            return

        self._album = utils.get_album_title(media)
        self._artist = utils.get_artist_name(media)
        self._media = media

        try:
            discoverer = GstPbutils.Discoverer.new(Gst.SECOND)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))
            self._lookup_cover_in_directory()
            return

        discoverer.connect('discovered', self._discovered)
        discoverer.start()

        success, path = MediaArt.get_path(self._artist, self._album, "album")

        if not success:
            self.emit('unavailable')
            discoverer.stop()
            return

        self._path = path

        success = discoverer.discover_uri_async(self._media.get_url())

        if not success:
            logger.warning("Could not add url to discoverer.")
            self.emit('unavailable')
            discoverer.stop()
            return

    @log
    def _discovered(self, discoverer, info, error):
        tags = info.get_tags()
        index = 0

        # FIXME: tags should not return as None, but it sometimes is.
        # So as a workaround until we figure out what is wrong check
        # for it.
        # https://bugzilla.gnome.org/show_bug.cgi?id=780980
        if (error is not None
                or tags is None):
            if error:
                logger.warning("Discoverer error: {}, {}".format(
                    Gst.CoreError(error.code), error.message))
            discoverer.stop()
            self.emit('unavailable')
            return

        while True:
            success, sample = tags.get_sample_index(Gst.TAG_IMAGE, index)
            if not success:
                break
            index += 1
            struct = sample.get_info()
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
                self.emit('found')
                discoverer.stop()
                return
            except GLib.Error as error:
                logger.warning("Error: {}, {}".format(
                    MediaArt.Error(error.code), error.message))

        discoverer.stop()

        self._lookup_cover_in_directory()

    @log
    def _lookup_cover_in_directory(self):
        # Find local art in cover.jpeg files.
        self._media_art.uri_async(
            MediaArt.Type.ALBUM, MediaArt.ProcessFlags.NONE,
            self._media.get_url(), self._artist, self._album,
            GLib.PRIORITY_LOW, None, self._uri_async_cb, None)

    @log
    def _uri_async_cb(self, src, result, data):
        try:
            success = self._media_art.uri_finish(result)
            if success:
                self.emit('found')
                return
        except GLib.Error as error:
            if MediaArt.Error(error.code) == MediaArt.Error.SYMLINK_FAILED:
                # This error indicates that the coverart has already
                # been linked by another concurrent lookup.
                self.emit('found')
                return
            else:
                logger.warning("Error: {}, {}".format(
                    MediaArt.Error(error.code), error.message))

        self.emit('unavailable')


class RemoteArt(GObject.GObject):
    """Looks for remote art through Grilo

    Uses Grilo coverart providers to retrieve art.
    """

    __gsignals__ = {
        'retrieved': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'unavailable': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __repr__(self):
        return '<RemoteArt>'

    @log
    def __init__(self):
        super().__init__()

        self._artist = None
        self._album = None

    @log
    def query(self, media):
        """Start the remote query

        :param Grl.Media media: The media object to search art for
        """
        self._album = utils.get_album_title(media)
        self._artist = utils.get_artist_name(media)

        # FIXME: It seems this Grilo query does not always return,
        # especially on queries with little info.
        grilo.get_album_art_for_item(media, self._remote_album_art)

    @log
    def _delete_callback(self, src, result, data):
        try:
            src.delete_finish(result)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))

    @log
    def _splice_callback(self, src, result, data):
        tmp_file, iostream = data

        iostream.close_async(
            GLib.PRIORITY_LOW, None, self._close_iostream_callback, None)

        try:
            src.splice_finish(result)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))
            self.emit('unavailable')
            return

        success, cache_path = MediaArt.get_path(
            self._artist, self._album, "album")

        if not success:
            self.emit('unavailable')
            return

        try:
            # FIXME: I/O blocking
            MediaArt.file_to_jpeg(tmp_file.get_path(), cache_path)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))
            self.emit('unavailable')
            return

        self.emit('retrieved')

        tmp_file.delete_async(
            GLib.PRIORITY_LOW, None, self._delete_callback, None)

    @log
    def _close_iostream_callback(self, src, result, data):
        try:
            src.close_finish(result)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))

    @log
    def _read_callback(self, src, result, data):
        try:
            istream = src.read_finish(result)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))
            self.emit('unavailable')
            return

        try:
            [tmp_file, iostream] = Gio.File.new_tmp()
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(error.domain, error.message))
            self.emit('unavailable')
            return

        ostream = iostream.get_output_stream()
        # FIXME: Passing the iostream here, otherwise it gets
        # closed. PyGI specific issue?
        ostream.splice_async(
            istream, Gio.OutputStreamSpliceFlags.CLOSE_SOURCE |
            Gio.OutputStreamSpliceFlags.CLOSE_TARGET, GLib.PRIORITY_LOW,
            None, self._splice_callback, [tmp_file, iostream])

    @log
    def _remote_album_art(self, source, param, item, count, error):
        if error:
            logger.warning("Grilo error {}".format(error))
            self.emit('unavailable')
            return

        thumb_uri = item.get_thumbnail()

        if thumb_uri is None:
            self.emit('unavailable')
            return

        src = Gio.File.new_for_uri(thumb_uri)
        src.read_async(
            GLib.PRIORITY_LOW, None, self._read_callback, None)
