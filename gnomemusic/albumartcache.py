# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
# Copyright (c) 2013 Guillaume Quintard <guillaume.quintard@gmail.com>
# Copyright (c) 2013 Lubosz Sarnecki <lubosz@gmail.com>
# Copyright (c) 2013 Sai Suman Prayaga <suman.sai14@gmail.com>
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
gi.require_version('MediaArt', '2.0')
from gi.repository import (Gdk, GdkPixbuf, Gio, GLib, GObject, Gtk, MediaArt,
                           Gst, GstTag, GstPbutils)

from gnomemusic import log
from gnomemusic.grilo import grilo
import gnomemusic.utils as utils


logger = logging.getLogger(__name__)


class Queue(GObject.GObject):
    """An operations queue"""

    def __init__(self):
        super().__init__()

        self._max_simultaneous_lookups = 10
        self._lookup_queue = []
        self._n_lookups = 0

    @log
    def push(self, func, argument):
        """Push a lookup counter or queue the lookup if needed"""

        # If reached the limit, queue the operation.
        if self._n_lookups >= self._max_simultaneous_lookups:
            self._lookup_queue.append((func, argument))
            return False
        else:
            func(argument)
            self._n_lookups += 1
            return True

    @log
    def pop(self):
        """Pops a lookup counter and consume the lookup queue if needed"""
        self._n_lookups -= 1

        # An available lookup slot appeared! Let's continue looking up
        # artwork then.
        if (self._n_lookups < self._max_simultaneous_lookups
                and self._lookup_queue):
            (func, argument) = self._lookup_queue.pop(0)
            func(argument)


@log
def _make_icon_frame(pixbuf, art_size=None, scale=1):
    border = 3 * scale
    degrees = pi / 180
    radius = 3 * scale

    ratio = pixbuf.get_height() / pixbuf.get_width()

    # Scale down the image according to the biggest axis
    if ratio > 1:
        w = int(art_size.width / ratio * scale)
        h = art_size.height * scale
    else:
        w = art_size.width * scale
        h = int(art_size.height * ratio * scale)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
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

    border_pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, w, h)

    surface = Gdk.cairo_surface_create_from_pixbuf(border_pixbuf,
                                                   scale,
                                                   None)

    return surface


class DefaultIcon(GObject.GObject):
    """Provides the symbolic fallback and loading icons."""

    class Type(Enum):
        loading = 'content-loading-symbolic'
        music = 'folder-music-symbolic'

    _cache = {}
    _scale = 1

    def __repr__(self):
        return '<DefaultIcon>'

    @log
    def __init__(self, scale=1):
        super().__init__()

        self._scale = scale

    @log
    def _make_default_icon(self, icon_type, art_size=None):
        width = art_size.width * self._scale
        height = art_size.height * self._scale

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

        icon_surface = _make_icon_frame(result, art_size, self._scale)

        return icon_surface

    @log
    def get(self, icon_type, art_size):
        """Returns the requested symbolic icon

        Returns a GdkPixbuf of the requested symbolic icon
        in the given size.

        :param enum icon_type: The DefaultIcon.Type of the icon
        :param enum art_size: The ArtSize requested

        :return: The symbolic icon
        :rtype: GdkPixbuf
        """
        if (icon_type, art_size) not in self._cache.keys():
            new_icon = self._make_default_icon(icon_type, art_size)
            self._cache[(icon_type, art_size)] = new_icon

        return self._cache[(icon_type, art_size)]


class Art(GObject.GObject):

    __gsignals__ = {
        'finished': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    _blacklist = {}
    _cache_queue = Queue()
    _embedded_queue = Queue()
    _remote_queue = Queue()

    class Size(Enum):
        """Enum for icon sizes"""
        XSMALL = (34, 34)
        SMALL = (48, 48)
        MEDIUM = (128, 128)
        LARGE = (256, 256)
        XLARGE = (512, 512)

        def __init__(self, width, height):
            """Intialize width and height"""
            self.width = width
            self.height = height

    @log
    def __init__(self, image, size, media):
        super().__init__()

        self._iter = None
        self._embedded = False
        self._remote = False

        # FIXME: A pixbuf instead of an image means this art is
        # requested by a treeview.
        if isinstance(image, GdkPixbuf.Pixbuf):
            self._pixbuf = image
            self._image = Gtk.Image()
        else:
            self._image = image

        self._size = size
        self._media = media
        self._media_url = media.get_url()

        self._image.set_property("width-request", size.width)
        self._image.set_property("height-request", size.height)

        self._scale = self._image.get_scale_factor()

        self._surface = DefaultIcon(self._scale).get(
            DefaultIcon.Type.loading, self._size)

        self._image.set_from_surface(self._surface)

        if self._in_blacklist():
            self._no_art_available()
            return

        cache = Cache()
        cache.connect('miss', self._cache_miss)
        cache.connect('hit', self._cache_hit)
        self._cache_queue.push(cache.query, self._media)

    def _cache_miss(self, klass):
        self._cache_queue.pop()

        embedded_art = EmbeddedArt()
        embedded_art.connect('found', self._embedded_art_found)
        embedded_art.connect('unavailable', self._embedded_art_unavailable)

        self._embedded_queue.push(embedded_art.query, self._media)

    def _cache_hit(self, klass, pixbuf):
        self._cache_queue.pop()

        surface = _make_icon_frame(pixbuf, self._size, self._scale)
        self._surface = surface
        self._image.set_from_surface(self._surface)
        self.emit('finished')

    def _embedded_art_found(self, klass):
        self._embedded_queue.pop()

        cache = Cache()
        cache.connect('miss', self._cache_miss)
        cache.connect('hit', self._cache_hit)

        self._cache_queue.push(cache.query, self._media)

    def _embedded_art_unavailable(self, klass):
        self._embedded_queue.pop()

        remote_art = RemoteArt()
        remote_art.connect('retrieved', self._remote_art_retrieved)
        remote_art.connect('unavailable', self._remote_art_unavailable)

        self._remote_queue.push(remote_art.query, self._media)

    def _remote_art_retrieved(self, klass):
        self._remote_queue.pop()

        cache = Cache()
        cache.connect('miss', self._cache_miss)
        cache.connect('hit', self._cache_hit)

        self._cache_queue.push(cache.query, self._media)

    def _remote_art_unavailable(self, klass):
        self._remote_queue.pop()

        self._add_to_blacklist()
        self._no_art_available()

    def _no_art_available(self):
        self._surface = DefaultIcon(self._scale).get(
            DefaultIcon.Type.music, self._size)

        self._image.set_from_surface(self._surface)
        self.emit('finished')

    def _add_to_blacklist(self):
        album = utils.get_album_title(self._media)
        artist = utils.get_artist_name(self._media)

        if artist not in self._blacklist:
            self._blacklist[artist] = []

        album_stripped = MediaArt.strip_invalid_entities(album)
        self._blacklist[artist].append(album_stripped)

    def _in_blacklist(self):
        album = utils.get_album_title(self._media)
        artist = utils.get_artist_name(self._media)
        album_stripped = MediaArt.strip_invalid_entities(album)

        if artist in self._blacklist:
            if album_stripped in self._blacklist[artist]:
                return True

        return False

    @GObject.Property
    @log
    def pixbuf(self):
        return Gdk.pixbuf_get_from_surface(
            self._surface, 0, 0, self._surface.get_width(),
            self._surface.get_height())

    @GObject.Property(type=Gtk.TreeIter)
    @log
    def iter(self):
        return self._iter

    @iter.setter
    @log
    def iter(self, iter_):
        self._iter = iter_

# 1. libmediaart
# 2  embedded -> libmediaart
# 3  remote -> libmediaart


class Cache(GObject.GObject):

    __gsignals__ = {
        'miss': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'hit': (GObject.SignalFlags.RUN_FIRST, None, (GObject.GObject, ))
    }

    def __init__(self):
        super().__init__()

        self._media_art = MediaArt.Process.new()

        # FIXME: async
        self.cache_dir = os.path.join(GLib.get_user_cache_dir(), 'media-art')
        if not os.path.exists(self.cache_dir):
            try:
                Gio.file_new_for_path(self.cache_dir).make_directory(None)
            except GLib.Error as error:
                logger.warn(
                    "Error: {}, {}".format(error.__class__, error.message))
                return

    def query(self, media):
        album = utils.get_album_title(media)
        artist = utils.get_artist_name(media)

        success, thumb_file = MediaArt.get_file(artist, album, "album")

        if (success
                and thumb_file.query_exists()):
            thumb_file.read_async(
                GLib.PRIORITY_LOW, None, self._open_stream, None)
            return

        self.emit('miss')

    def _open_stream(self, thumb_file, result, arguments):
        try:
            stream = thumb_file.read_finish(result)
        except GLib.Error as error:
            logger.warn(
                "Error: {}, {}".format(error.__class__, error.message))
            stream.close_async(
                GLib.PRIORITY_LOW, None, self._close_stream, None)
            self.emit('miss')
            return

        GdkPixbuf.Pixbuf.new_from_stream_async(
            stream, None, self._pixbuf_loaded, None)

    def _pixbuf_loaded(self, stream, result, data):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(result)
        except GLib.Error as error:
            logger.warn("Error: {}, {}".format(error.__class__, error.message))
            stream.close_async(
                GLib.PRIORITY_LOW, None, self._close_stream, None)
            self.emit('miss')
            return

        stream.close_async(GLib.PRIORITY_LOW, None, self._close_stream, None)
        self.emit('hit', pixbuf)

    def _close_stream(self, stream, result, data):
        stream.close_finish(result)
        # TODO: Try except


class EmbeddedArt(GObject.GObject):

    __gsignals__ = {
        'found': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'unavailable': (
            GObject.SignalFlags.RUN_FIRST, None, ()
        )
    }

    def __init__(self):
        super().__init__()

        try:
            Gst.init(None)
            self._discoverer = GstPbutils.Discoverer.new(Gst.SECOND)
            # self._discoverer.connect('discovered', self._discovered)
            # self._discoverer.start()
        except GLib.Error as error:
            logger.warn("Error: {}, {}".format(error.__class__, error.message))
            return

        self._path = None

    def query(self, media):
        album = utils.get_album_title(media)
        artist = utils.get_artist_name(media)

        success, path = MediaArt.get_path(artist, album, "album")
        if not success:
            self.emit('unavailable')
            # self._discoverer.stop()
            return

        self._path = path
        try:
            info_ = self._discoverer.discover_uri(media.get_url())
        except GLib.Error as error:
            logger.warn("Error: {}, {}".format(error.__class__, error.message))
            self.emit('unavailable')
            # self._discoverer.stop()
            return

        self._discovered(info_)

    # FIXME: async is triggering a bug.
    # def _discovered(self, discoverer, info, error):
    def _discovered(self, info):
        tags = info.get_tags()
        index = 0

        # FIXME: tags should not return as None, but it sometimes is.
        # So as a workaround until we figure out what is wrong check
        # for it.
        # https://bugzilla.gnome.org/show_bug.cgi?id=780980
        # if (error is not None
        #        or tags is None):
        #    self._discoverer.stop()
        #    self.emit('unavailable')
        #    return

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
                # self._discoverer.stop()
                return
            except GLib.Error as error:
                logger.warn(
                    "Error: {}, {}".format(error.__class__, error.message))

        self.emit('unavailable')
        # self._discoverer.stop()


class RemoteArt(GObject.GObject):

    __gsignals__ = {
        'retrieved': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'unavailable': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    @log
    def __init__(self):
        super().__init__()

        self._artist = None
        self._album = None

    @log
    def query(self, media):
        """Lookup remote art

        Lookup remote art through Grilo and if found copy locally. Call
        _lookup_local to finish retrieving suitable art.
        """
        self._album = utils.get_album_title(media)
        self._artist = utils.get_artist_name(media)

        grilo.get_album_art_for_item(media, self._remote_album_art)

    @log
    def _delete_async_callback(self, src, result, data):
        try:
            src.delete_finish(result)
        except GLib.Error as error:
            logger.warn("Error: {}, {}".format(error.__class__, error.message))

    @log
    def _splice_async_callback(self, src, result, data):
        tmp_file, iostream = data

        try:
            src.splice_finish(result)
        except GLib.Error as error:
            logger.warn("Error: {}, {}".format(error.__class__, error.message))
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
            logger.warn("Error: {}, {}".format(error.__class__, error.message))
            self.emit('unavailable')
            return

        self.emit('retrieved')

        tmp_file.delete_async(
            GLib.PRIORITY_LOW, None, self._delete_async_callback, None)

    @log
    def _read_async_callback(self, src, result, data):
        try:
            istream = src.read_finish(result)
        except GLib.Error as error:
            logger.warn("Error: {}, {}".format(error.__class__, error.message))
            self.emit('unavailable')
            return

        try:
            [tmp_file, iostream] = Gio.File.new_tmp()
        except GLib.Error as error:
            logger.warn("Error: {}, {}".format(error.__class__, error.message))
            self.emit('unavailable')
            return

        ostream = iostream.get_output_stream()
        # FIXME: Passing the iostream here, otherwise it gets
        # closed. PyGI specific issue?
        ostream.splice_async(
            istream, Gio.OutputStreamSpliceFlags.CLOSE_SOURCE |
            Gio.OutputStreamSpliceFlags.CLOSE_TARGET, GLib.PRIORITY_LOW,
            None, self._splice_async_callback, [tmp_file, iostream])

    @log
    def _remote_album_art(self, source, param, item, count, error):
        if error:
            logger.warn("Grilo error {}".format(error))
            self.emit('unavailable')
            return

        thumb_uri = item.get_thumbnail()

        if thumb_uri is None:
            self.emit('unavailable')
            return

        src = Gio.File.new_for_uri(thumb_uri)
        src.read_async(
            GLib.PRIORITY_LOW, None, self._read_async_callback, None)
