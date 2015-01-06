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


from gi.repository import Gtk, GdkPixbuf, Gio, GLib, Gdk, MediaArt
from gettext import gettext as _
import cairo
from math import pi
import os
from threading import Thread, Lock
from gnomemusic import log
from gnomemusic.grilo import grilo
import logging
from queue import Queue
logger = logging.getLogger(__name__)

WORKER_THREADS = 2


@log
def _make_icon_frame(pixbuf, path=None):
    border = 1.5
    degrees = pi / 180
    radius = 3

    w = pixbuf.get_width()
    h = pixbuf.get_height()
    new_pixbuf = pixbuf.scale_simple(w - border * 2,
                                     h - border * 2,
                                     0)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surface)
    ctx.new_sub_path()
    ctx.arc(w - radius, radius, radius - 0.5, -90 * degrees, 0 * degrees)
    ctx.arc(w - radius, h - radius, radius - 0.5, 0 * degrees, 90 * degrees)
    ctx.arc(radius, h - radius, radius - 0.5, 90 * degrees, 180 * degrees)
    ctx.arc(radius, radius, radius - 0.5, 180 * degrees, 270 * degrees)
    ctx.close_path()
    ctx.set_line_width(0.6)
    ctx.set_source_rgb(0.2, 0.2, 0.2)
    ctx.stroke_preserve()
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()
    border_pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, w, h)

    new_pixbuf.copy_area(border, border,
                         w - border * 4,
                         h - border * 4,
                         border_pixbuf,
                         border * 2, border * 2)
    return border_pixbuf


class AlbumArtCache:
    instance = None
    blacklist = {}
    itr_queue = []
    threading_lock = Lock()

    @classmethod
    def get_default(self):
        if not self.instance:
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

    def worker(self, id):
        while True:
            try:
                item = self.thread_queue.get()
                item.setDaemon(True)
                item.start()
                item.join(30)
                self.thread_queue.task_done()
            except Exception as e:
                logger.warn("worker %d item %s: error %s" % (id, item, str(e)))

    @log
    def __init__(self):
        try:
            self.cacheDir = os.path.join(GLib.get_user_cache_dir(), 'media-art')
            if not os.path.exists(self.cacheDir):
                Gio.file_new_for_path(self.cacheDir).make_directory(None)
        except Exception as e:
            logger.warn("Error: %s" % e)

        try:
            self.thread_queue = Queue()
            for i in range(WORKER_THREADS):
                t = Thread(target=self.worker, args=(i,))
                t.setDaemon(True)
                t.start()
        except Exception as e:
            logger.warn("Error: %s" % e)

    @log
    def get_default_icon(self, width, height, is_loading=False):
        # get a small pixbuf with the given path
        icon_name = 'folder-music-symbolic'
        if is_loading:
            icon_name = 'content-loading-symbolic'
        icon = Gtk.IconTheme.get_default().load_icon(icon_name, max(width, height) / 4, 0)

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
                       GdkPixbuf.InterpType.NEAREST, 0x33)
        return _make_icon_frame(result)

    @log
    def lookup(self, item, width, height, callback, itr, artist, album):
        try:
            # Make sure we don't lookup the same iterators several times
            with self.threading_lock:
                if itr:
                    if itr.user_data in self.itr_queue:
                        return
                    self.itr_queue.append(itr.user_data)

            t = Thread(target=self.lookup_worker, args=(item, width, height, callback, itr, artist, album))
            self.thread_queue.put(t)
        except Exception as e:
            logger.warn("Error: %s, %s" % (e.__class__, e))

    @log
    def lookup_worker(self, item, width, height, callback, itr, artist, album):
        try:

            if artist in self.blacklist and album in self.blacklist[artist]:
                self.finish(item, None, None, callback, itr)
                return

            path = None
            mediaart_tuple = MediaArt.get_path(artist, album, "album", None)
            for i in mediaart_tuple:
                if isinstance(i, str):
                    path = i
                    break

            if not os.path.exists(path):
                GLib.idle_add(self.cached_thumb_not_found, item, width, height, path, callback, itr, artist, album)
                return
            width = width or -1
            height = height or -1
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, width, height, True)
            self.finish(item, _make_icon_frame(pixbuf), path, callback, itr)
        except Exception as e:
            logger.warn("Error: %s" % e)

    @log
    def finish(self, item, pixbuf, path, callback, itr):
        try:
            if path:
                item.set_thumbnail(GLib.filename_to_uri(path, None))
            GLib.idle_add(callback, pixbuf, path, itr)
        except Exception as e:
            logger.warn("Error: %s" % e)

    @log
    def cached_thumb_not_found(self, item, width, height, path, callback, itr, artist, album):
        try:
            uri = item.get_thumbnail()
            if uri is None:
                grilo.get_album_art_for_item(item, self.album_art_for_item_callback,
                                             (item, width, height, path, callback, itr, artist, album))
                return

            t = Thread(target=self.download_worker, args=(item, width, height, path, callback, itr, artist, album, uri))
            self.thread_queue.put(t)
        except Exception as e:
            logger.warn("Error: %s" % e)

    @log
    def album_art_for_item_callback(self, source, param, item, count, data, error):
        old_item, width, height, path, callback, itr, artist, album = data
        try:
            if item is None:
                return

            uri = item.get_thumbnail()
            if uri is None:
                # Blacklist artist-album combination
                if artist not in self.blacklist:
                    self.blacklist[artist] = []
                self.blacklist[artist].append(album)

                logger.warn("can't find URL for album '%s' by %s" % (album, artist))
                noArtworkIcon = self.get_default_icon(width, height, False)
                self.finish(item, noArtworkIcon, None, callback, itr)
                return

            t = Thread(target=self.download_worker, args=(item, width, height, path, callback, itr, artist, album, uri))
            self.thread_queue.put(t)
        except Exception as e:
            logger.warn("Error: %s" % e)

    @log
    def download_worker(self, item, width, height, path, callback, itr, artist, album, uri):
        try:
            src = Gio.File.new_for_uri(uri)
            dest = Gio.File.new_for_path(path)
            src.copy(dest, Gio.FileCopyFlags.OVERWRITE)
            self.lookup_worker(item, width, height, callback, itr, artist, album)
        except Exception as e:
            logger.warn("Error: %s" % e)
