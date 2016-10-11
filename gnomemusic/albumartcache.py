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
from gettext import gettext as _
import gi
gi.require_version('MediaArt', '2.0')
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, GObject, Gtk, MediaArt

from gnomemusic import log
from gnomemusic.grilo import grilo
import gnomemusic.utils as utils


logger = logging.getLogger(__name__)


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

    new_pixbuf = pixbuf.scale_simple(w - border * 2,
                                     h - border * 2,
                                     GdkPixbuf.InterpType.HYPER)

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

    # paste the scaled pixbuf in the center
    Gdk.cairo_set_source_pixbuf(ctx, new_pixbuf, border, border)
    ctx.paint()

    border_pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, w, h)

    surface = Gdk.cairo_surface_create_from_pixbuf(border_pixbuf,
                                                   scale,
                                                   None)

    return surface


class ArtSize(Enum):
    """Enum for icon sizes"""
    xsmall = (34, 34)
    small = (48, 48)
    medium = (128, 128)
    large = (256, 256)
    xlarge = (512, 512)

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
        GObject.GObject.__init__(self)
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

    On basis of a given media item looks up album art locally and if
    not found remotely.
    """
    _instance = None
    blacklist = {}
    _scale = 1

    def __repr__(self):
        return '<AlbumArtCache>'

    @log
    def __init__(self, scale=1):
        GObject.GObject.__init__(self)
        self._scale = scale

        self.cache_dir = os.path.join(GLib.get_user_cache_dir(), 'media-art')
        if not os.path.exists(self.cache_dir):
            try:
                Gio.file_new_for_path(self.cache_dir).make_directory(None)
            except Exception as err:
                logger.warn("Error: %s, %s", err.__class__, err)
                return

    @log
    def lookup(self, item, art_size, callback, itr):
        """Find art for the given item

        :param item: Grilo media item
        :param ArtSize art_size: Size of the icon
        :param callback: Callback function when retrieved
        :param itr: Iter to return with callback
        """
        self._lookup_local(item, callback, itr, art_size)

    @log
    def _lookup_local(self, item, callback, itr, art_size):
        """Checks if there is already a local art file, if not calls
        the remote lookup function"""
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

        self._lookup_remote(item, callback, itr, art_size)

    @log
    def _lookup_remote(self, item, callback, itr, art_size):
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
