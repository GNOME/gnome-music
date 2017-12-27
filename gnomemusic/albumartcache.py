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


class LookupQueue(object):
    """A queue for IO operations"""

    _max_simultaneous_lookups = 12
    _lookup_queue = []
    _n_lookups = 0

    @classmethod
    @log
    def push(cls, cache, item, art_size, callback, itr):
        """Push a lookup counter or queue the lookup if needed"""

        # If reached the limit, queue the operation.
        if cls._n_lookups >= cls._max_simultaneous_lookups:
            cls._lookup_queue.append((cache, item, art_size, callback, itr))
            return False
        else:
            cls._n_lookups += 1
            return True

    @classmethod
    @log
    def pop(cls):
        """Pops a lookup counter and consume the lookup queue if needed"""

        cls._n_lookups -= 1

        # An available lookup slot appeared! Let's continue looking up
        # artwork then.
        if (cls._n_lookups < cls._max_simultaneous_lookups
                and cls._lookup_queue):
            (cache, item, art_size, callback, itr) = cls._lookup_queue.pop(0)
            cache.lookup(item, art_size, callback, itr)


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


class ArtSize(Enum):
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


class AlbumArtCache(GObject.GObject):
    """Album art retrieval class

    On basis of a given media item looks up album art in the following order:
    1) already existing in cache
    2) from embedded images
    3) from local images
    3) remotely
    """
    _instance = None
    blacklist = {}
    _scale = 1

    def __repr__(self):
        return '<AlbumArtCache>'

    @log
    def __init__(self, scale=1):
        super().__init__()

        self._scale = scale

        self.cache_dir = os.path.join(GLib.get_user_cache_dir(), 'media-art')
        if not os.path.exists(self.cache_dir):
            try:
                Gio.file_new_for_path(self.cache_dir).make_directory(None)
            except Exception as err:
                logger.warn("Error: %s, %s", err.__class__, err)
                return

        Gst.init(None)
        self._discoverer = GstPbutils.Discoverer.new(Gst.SECOND)
        self._discoverer.connect('discovered', self._discovered_cb)
        self._discoverer.start()

        self._discoverer_items = {}

        self._media_art = None
        try:
            self._media_art = MediaArt.Process.new()
        except Exception as err:
            logger.warn("Error: %s, %s", err.__class__, err)

    @log
    def lookup(self, item, art_size, callback, itr):
        """Find art for the given item

        :param item: Grilo media item
        :param ArtSize art_size: Size of the icon
        :param callback: Callback function when retrieved
        :param itr: Iter to return with callback
        """
        if LookupQueue.push(self, item, art_size, callback, itr):
            self._lookup_local(item, art_size, callback, itr)

    @log
    def _lookup_local(self, item, art_size, callback, itr):
        """Checks if there is already a local art file, if not calls
        the embedded lookup function"""
        album = utils.get_album_title(item)
        artist = utils.get_artist_name(item)

        def stream_open(thumb_file, result, arguments):
            try:
                stream = thumb_file.read_finish(result)
            except Exception as err:
                logger.warn("Error: %s, %s", err.__class__, err)
                do_callback(None)
                return

            GdkPixbuf.Pixbuf.new_from_stream_async(stream,
                                                   None,
                                                   pixbuf_loaded,
                                                   None)

        def pixbuf_loaded(stream, result, data):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(result)
            except Exception as err:
                logger.warn("Error: %s, %s", err.__class__, err)
                do_callback(None)
                return

            do_callback(pixbuf)
            return

        def do_callback(pixbuf):

            # Lookup finished, decrease the counter
            LookupQueue.pop()

            if not pixbuf:
                surface = DefaultIcon(self._scale).get(DefaultIcon.Type.music,
                                                       art_size)
            else:
                surface = _make_icon_frame(pixbuf, art_size, self._scale)

                # Sets the thumbnail location for MPRIS to use.
                item.set_thumbnail(GLib.filename_to_uri(thumb_file.get_path(),
                                                        None))

            GLib.idle_add(callback, surface, itr)
            return

        success, thumb_file = MediaArt.get_file(artist, album, "album")

        if (success
                and thumb_file.query_exists()):
            thumb_file.read_async(GLib.PRIORITY_LOW,
                                  None,
                                  stream_open,
                                  None)
            return

        stripped_album = MediaArt.strip_invalid_entities(album)
        if (artist in self.blacklist
                and stripped_album in self.blacklist[artist]):
            do_callback(None)
            return

        # When we reach here because it fails to retrieve the artwork,
        # do a long round trip (either through _lookup_embedded or
        # _lookup_remote) and call self.lookup() again. Thus, decrease
        # global lookup counter.
        LookupQueue.pop()

        self._lookup_embedded(item, art_size, callback, itr)

    @log
    def _discovered_cb(self, discoverer, info, error):
        item, art_size, callback, itr, cache_path = \
            self._discoverer_items[info.get_uri()]

        album = utils.get_album_title(item)
        artist = utils.get_artist_name(item)
        tags = info.get_tags()
        index = 0

        def art_retrieved(result):
            if not result:
                if artist not in self.blacklist:
                    self.blacklist[artist] = []

                album_stripped = MediaArt.strip_invalid_entities(album)
                self.blacklist[artist].append(album_stripped)

            self.lookup(item, art_size, callback, itr)

        # FIXME: tags should not return as None, but it sometimes is.
        # So as a workaround until we figure out what is wrong check
        # for it.
        # https://bugzilla.gnome.org/show_bug.cgi?id=780980
        if (error is not None
                or tags is None):
            art_retrieved(False)
            return

        while True:
            success, sample = tags.get_sample_index(Gst.TAG_IMAGE, index)
            if not success:
                break
            index += 1
            struct = sample.get_info()
            success, image_type = struct.get_enum('image-type',
                                                  GstTag.TagImageType)
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
                MediaArt.buffer_to_jpeg(map_info.data, mime, cache_path)
                art_retrieved(True)
                return
            except Exception as err:
                logger.warn("Error: %s, %s", err.__class__, err)

        try:
            self._media_art.uri(MediaArt.Type.ALBUM,
                                MediaArt.ProcessFlags.NONE, item.get_url(),
                                artist, album, None)
            if os.path.exists(cache_path):
                art_retrieved(True)
                return
        except Exception as err:
            logger.warn("Trying to process misc albumart: %s, %s",
                        err.__class__, err)

        self._lookup_remote(item, art_size, callback, itr)

    @log
    def _lookup_embedded(self, item, art_size, callback, itr):
        """Lookup embedded cover

        Lookup embedded art through Gst.Discoverer. If found
        copy locally and call _lookup_local to finish retrieving
        suitable art, otherwise follow up with _lookup_remote.
        """
        album = utils.get_album_title(item)
        artist = utils.get_artist_name(item)

        success, cache_path = MediaArt.get_path(artist, album, "album")
        if not success:
            self._lookup_remote(item, callback, itr, art_size)

        self._discoverer_items[item.get_url()] = [item, art_size, callback,
                                                  itr, cache_path]
        self._discoverer.discover_uri_async(item.get_url())

    @log
    def _lookup_remote(self, item, art_size, callback, itr):
        """Lookup remote art

        Lookup remote art through Grilo and if found copy locally. Call
        _lookup_local to finish retrieving suitable art.
        """
        album = utils.get_album_title(item)
        artist = utils.get_artist_name(item)

        @log
        def delete_cb(src, result, data):
            try:
                src.delete_finish(result)
            except Exception as err:
                logger.warn("Error: %s, %s", err.__class__, err)

        @log
        def splice_cb(src, result, data):
            tmp_file, iostream = data

            try:
                src.splice_finish(result)
            except Exception as err:
                logger.warn("Error: %s, %s", err.__class__, err)
                art_retrieved(False)
                return

            success, cache_path = MediaArt.get_path(artist, album, "album")
            try:
                # FIXME: I/O blocking
                MediaArt.file_to_jpeg(tmp_file.get_path(), cache_path)
            except Exception as err:
                logger.warn("Error: %s, %s", err.__class__, err)
                art_retrieved(False)
                return

            art_retrieved(True)

            tmp_file.delete_async(GLib.PRIORITY_LOW,
                                  None,
                                  delete_cb,
                                  None)

        @log
        def async_read_cb(src, result, data):
            try:
                istream = src.read_finish(result)
            except Exception as err:
                logger.warn("Error: %s, %s", err.__class__, err)
                art_retrieved(False)
                return

            try:
                [tmp_file, iostream] = Gio.File.new_tmp()
            except Exception as err:
                logger.warn("Error: %s, %s", err.__class__, err)
                art_retrieved(False)
                return

            ostream = iostream.get_output_stream()
            # FIXME: Passing the iostream here, otherwise it gets
            # closed. PyGI specific issue?
            ostream.splice_async(istream,
                                 Gio.OutputStreamSpliceFlags.CLOSE_SOURCE |
                                 Gio.OutputStreamSpliceFlags.CLOSE_TARGET,
                                 GLib.PRIORITY_LOW,
                                 None,
                                 splice_cb,
                                 [tmp_file, iostream])

        @log
        def album_art_for_item_cb(source, param, item, count, error):
            if error:
                logger.warn("Grilo error %s", error)
                art_retrieved(False)
                return

            thumb_uri = item.get_thumbnail()

            if thumb_uri is None:
                art_retrieved(False)
                return

            src = Gio.File.new_for_uri(thumb_uri)
            src.read_async(GLib.PRIORITY_LOW,
                           None,
                           async_read_cb,
                           None)

        @log
        def art_retrieved(result):
            if not result:
                if artist not in self.blacklist:
                    self.blacklist[artist] = []

                album_stripped = MediaArt.strip_invalid_entities(album)
                self.blacklist[artist].append(album_stripped)

            self.lookup(item, art_size, callback, itr)

        grilo.get_album_art_for_item(item, album_art_for_item_cb)
