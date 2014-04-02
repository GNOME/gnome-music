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


from gi.repository import Gtk, GdkPixbuf, Gio, GLib, Grl, Gdk, MediaArt
from gettext import gettext as _
import cairo
from math import pi
import threading
import os
from gnomemusic import log
import logging
logger = logging.getLogger(__name__)


class LookupRequest:

    @log
    def __init__(self, item, width, height, callback, data=None):
        self.item = item
        self.width = width or -1
        self.height = height or -1
        self.callback = callback
        self.data = data
        self.artist = item.get_string(Grl.METADATA_KEY_ARTIST) or item.get_string(Grl.METADATA_KEY_AUTHOR) or ''
        self.album = item.get_string(Grl.METADATA_KEY_ALBUM) or ''
        self.path = MediaArt.get_path(self.artist, self.album, "album", None)[0]
        self.started = False

    @log
    def start(self):
        self.started = True
        f = Gio.File.new_for_path(self.path)
        f.read_async(GLib.PRIORITY_DEFAULT, None, self._on_read_ready, None)

    @log
    def finish(self, pixbuf):
        if pixbuf:
            # Cache the path on the original item for faster retrieval
            self.item.set_thumbnail(GLib.filename_to_uri(self.path, None))
        self.callback(pixbuf, self.path, self.data)

    @log
    def _on_read_ready(self, obj, res, data=None):
        try:
            stream = obj.read_finish(res)

            GdkPixbuf.Pixbuf.new_from_stream_async(stream, None, self._on_pixbuf_ready, None)
            return

        except Exception as error:
            if AlbumArtCache.get_default().logLookupErrors:
                print('ERROR:', error)

        self._on_load_fail()

    @log
    def _on_pixbuf_ready(self, source, res, data=None):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(res)
            if self.width < 0 and self.height < 0:
                self.finish(pixbuf)
                return

            width = pixbuf.get_width()
            height = pixbuf.get_height()
            if width >= self.width or height >= self.height:
                if width > height and self.width < 0:
                    self.height *= (height / width)
                elif height > width and self.height < 0:
                    self.width *= (width / height)
                scale = max(width / self.width, height / self.height)
                pixbuf = pixbuf.scale_simple(width / scale, height / scale, 2)
                self.finish(pixbuf)
                return
        except Exception as error:
            if AlbumArtCache.get_default().logLookupErrors:
                print('ERROR:', error)

        self._on_load_fail()

    @log
    def _on_load_fail(self):
        options = Grl.OperationOptions()
        options.set_flags(Grl.ResolutionFlags.FULL |
                          Grl.ResolutionFlags.IDLE_RELAY)

        uri = self.item.get_thumbnail()
        if uri is None:
            self.finish(None)
            return

        AlbumArtCache.get_default().get_from_uri(
            uri, self.artist, self.album, self.width, self.height,
            self.callback, self.data
        )


class GetUriRequest:

    @log
    def __init__(self, uri, artist, album, callback, data=None):
        self.uri = uri
        self.artist = artist
        self.album = album
        self.callback = callback
        self.data = data
        self.callbacks = []
        self.path = ''
        self.path = MediaArt.get_path(artist, album, "album", None)[0]
        self.stream = None
        self.started = False

    @log
    def start(self):
        self.started = True
        f = Gio.File.new_for_uri(self.uri)
        f.read_async(300, None, self._on_read_ready, None)

    @log
    def _on_read_ready(self, outstream, res, user_data=None):
        try:
            self.stream = outstream.read_finish(res)

            try:
                streamInfo =\
                    self.stream.query_info('standard::content-type', None)
                contentType = streamInfo.get_content_type()

                if contentType == 'image/png':
                    self.path += '.png'
                elif contentType == 'image/jpeg':
                    self.path += '.jpeg'
                else:
                    print('Thumbnail format not supported, not caching')
                    self.stream.close(None)
                    return
            except Exception as e:
                print('Failed to query thumbnail content type')
                self.path += '.jpeg'
                return

            newFile = Gio.File.new_for_path(self.path)
            newFile.replace_async(None, False,
                                  Gio.FileCreateFlags.REPLACE_DESTINATION,
                                  300, None, self._on_replace_ready, None)

        except Exception as e:
            print(e)

    @log
    def _on_replace_ready(self, new_file, res, user_data=None):
        outstream = new_file.replace_finish(res)
        outstream.splice_async(self.stream,
                               Gio.IOStreamSpliceFlags.NONE,
                               300, None, self._on_splice_ready, None)

    @log
    def _on_splice_ready(self, outstream, res, user_data=None):
        for values in self.callbacks:
            width, height, callback, data = values
            try:
                pixbuf =\
                    GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        self.path, height, width, True)
                callback(pixbuf, self.path, data)
            except Exception as e:
                print('Failed to load image: %s' % e.message)
                callback(None, None, data)
        self.callback(self, self.data)


class AlbumArtCache:
    instance = None
    degrees = pi / 180

    @classmethod
    def get_default(self):
        if self.instance:
            return self.instance
        else:
            self.instance = AlbumArtCache()
        return self.instance

    @classmethod
    def get_media_title(self, media, escaped=False):
        title = media.get_title()
        if title:
            if escaped:
                return GLib.markup_escape_text(title)
            else:
                return title
        uri = media.get_url()
        if uri is None:
            return _("Untitled")

        uri_file = Gio.File.new_for_path(uri)
        basename = uri_file.get_basename()

        try:
            title = GLib.uri_unescape_string(basename, '')
        except:
            title = _("Untitled")
            pass
        if escaped:
            return GLib.markup_escape_text(title)

        return title

    @log
    def __init__(self):
        self.logLookupErrors = False
        self.requested_uris = {}
        self.cacheDir = os.path.join(GLib.get_user_cache_dir(), 'media-art')
        self.frame_cache = {}
        self.frame_lock = threading.Lock()

        try:
            Gio.file_new_for_path(self.cacheDir).make_directory(None)
        except:
            pass

    @log
    def make_default_icon(self, width, height):
        # get a small pixbuf with the given path
        icon = Gtk.IconTheme.get_default().load_icon('folder-music-symbolic', max(width, height) / 4, 0)

        # create an empty pixbuf with the requested size
        result = GdkPixbuf.Pixbuf.new(icon.get_colorspace(),
                                      True,
                                      icon.get_bits_per_sample(),
                                      icon.get_width() * 4,
                                      icon.get_height() * 4)
        result.fill(0xffffffff)
        icon.composite(result,
                       icon.get_width() * 3 / 2,
                       icon.get_height() * 3 / 2,
                       icon.get_width(),
                       icon.get_height(),
                       icon.get_width() * 3 / 2,
                       icon.get_height() * 3 / 2,
                       1, 1,
                       GdkPixbuf.InterpType.NEAREST, 0xff)
        return self._make_icon_frame(result)

    @log
    def _make_icon_frame(self, pixbuf):
        border = 1.5
        w = pixbuf.get_width()
        h = pixbuf.get_height()
        pixbuf = pixbuf.scale_simple(w - border * 2,
                                     h - border * 2,
                                     0)

        result = self._draw_rounded_path(0, 0, w, h, 3)

        pixbuf.copy_area(border, border,
                         w - border * 4,
                         h - border * 4,
                         result,
                         border * 2, border * 2)

        return result

    @log
    def _draw_rounded_path(self, x, y, width, height, radius):
        key = "%dx%d@%dx%d:%d" % (width, height, x, y, radius)
        self.frame_lock.acquire()
        if key not in self.frame_cache:
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
            ctx = cairo.Context(surface)
            ctx.new_sub_path()
            ctx.arc(x + width - radius, y + radius, radius - 0.5,
                    -90 * self.degrees, 0 * self.degrees)
            ctx.arc(x + width - radius, y + height - radius, radius - 0.5,
                    0 * self.degrees, 90 * self.degrees)
            ctx.arc(x + radius, y + height - radius, radius - 0.5,
                    90 * self.degrees, 180 * self.degrees)
            ctx.arc(x + radius, y + radius, radius - 0.5, 180 * self.degrees,
                    270 * self.degrees)
            ctx.close_path()
            ctx.set_line_width(0.6)
            ctx.set_source_rgb(0.2, 0.2, 0.2)
            ctx.stroke_preserve()
            ctx.set_source_rgb(1, 1, 1)
            ctx.fill()
            self.frame_cache[key] = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)
        res = self.frame_cache[key].copy()
        self.frame_lock.release()
        return res

    @log
    def lookup(self, item, width, height, callback, data=None):
        request = LookupRequest(item, width, height, callback, data)
        request.start()

    @log
    def get_from_uri(self, uri, artist, album, width, height, callback, data=None):
        if not uri:
            return

        if uri not in self.requested_uris:
            request = GetUriRequest(uri, artist, album, self._on_get_uri_request_finish, data)
            self.requested_uris[uri] = request
        else:
            request = self.requested_uris[uri]

        request.callbacks.append([width, height, callback, data])
        if not request.started:
            request.start()

    @log
    def _on_get_uri_request_finish(self, request, data=None):
        del self.requested_uris[request.uri]
