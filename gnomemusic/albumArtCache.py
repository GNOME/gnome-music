from gi.repository import Gtk, GdkPixbuf, Gio, GLib, Grl, Gdk
from gettext import gettext as _
import cairo
from math import pi

import threading
import os
import re


class LookupRequest:
    def __init__(self, item, width, height, callback, data=None):
        self.item = item
        self.width = width or -1
        self.height = height or -1
        self.callback = callback
        self.data = data
        self.path = ''
        self.key = ''
        self.key_index = 0
        self.icon_format = 'jpeg'
        self.artist = item.get_string(Grl.METADATA_KEY_ARTIST) or item.get_string(Grl.METADATA_KEY_AUTHOR)
        self.album = item.get_string(Grl.METADATA_KEY_ALBUM)
        self.started = False

    def start(self):
        self.started = True
        self._try_load()

    def finish(self, pixbuf):
        if pixbuf:
            # Cache the path on the original item for faster retrieval
            self.item.set_thumbnail(self.path)
        self.callback(pixbuf, self.path, self.data)

    def _try_load(self):
        if self.key_index >= 2:
            if self.icon_format == 'jpeg':
                self.key_index = 0
                self.icon_format = 'png'
            else:
                self._on_try_load_finished(None)
                return

        self.key = AlbumArtCache.get_default()._keybuilder_funcs[self.key_index].__call__(self.artist, self.album)
        self.path = GLib.build_filenamev([AlbumArtCache.get_default().cacheDir, '%s.%s' % (self.key, self.icon_format)])
        f = Gio.File.new_for_path(self.path)

        f.read_async(GLib.PRIORITY_DEFAULT, None, self._on_read_ready, None)

    def _on_read_ready(self, obj, res, data=None):
        try:
            stream = obj.read_finish(res)

            GdkPixbuf.Pixbuf.new_from_stream_async(stream, None, self._on_pixbuf_ready, None)
            return

        except Exception as error:
            if AlbumArtCache.get_default().logLookupErrors:
                print("ERROR:", error)

        self.key_index += 1
        self._try_load()

    def _on_pixbuf_ready(self, source, res, data=None):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(res)
            if self.width < 0 and self.height < 0:
                self._on_try_load_finished(pixbuf)
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
                self._on_try_load_finished(pixbuf)
                return
        except Exception as error:
            if AlbumArtCache.get_default().logLookupErrors:
                print("ERROR:", error)

        self.key_index += 1
        self._try_load()

    def _on_try_load_finished(self, icon, data=None):
        if icon:
            self.finish(icon)
            return

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
    def __init__(self, uri, artist, album, callback, data=None):
        self.uri = uri
        self.artist = artist
        self.album = album
        self.callback = callback
        self.data = data
        self.callbacks = []
        self.path = ''
        self.key = AlbumArtCache.get_default()._keybuilder_funcs[0].__call__(artist, album)
        self.path = GLib.build_filenamev([AlbumArtCache.get_default().cacheDir, self.key])
        self.stream = None
        self.started = False

    def start(self):
        self.started = True
        f = Gio.File.new_for_uri(self.uri)
        f.read_async(300, None, self._on_read_ready, None)

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

    def _on_replace_ready(self, new_file, res, user_data=None):
        outstream = new_file.replace_finish(res)
        outstream.splice_async(self.stream,
                               Gio.IOStreamSpliceFlags.NONE,
                               300, None, self._on_splice_ready, None)

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

    blocks = re.compile('(\[(.*?)\]|\{(.*?)\}|\<(.*?)\>|\((.*?)\))', re.DOTALL)
    invalid_chars = re.compile('[()<>\[\]{}_!@#$^&*+=|\\\/"\'?~]', re.DOTALL)
    multiple_spaces = re.compile('\t|\s+', re.DOTALL)

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

        title = GLib.uri_unescape_string(basename, "")
        if escaped:
            return GLib.markup_escape_text(title)

        return title

    def __init__(self):
        self.logLookupErrors = False
        self.requested_uris = {}
        self.cacheDir = os.path.join(GLib.get_user_cache_dir(), "media-art")
        self.frame_cache = {}
        self.frame_lock = threading.Lock()

        self._keybuilder_funcs = [
            lambda artist, album:
            "album-" + self._normalize_and_hash(artist) +
            "-" + self._normalize_and_hash(album),
            lambda artist, album:
            "album-" + self._normalize_and_hash(album) +
            "-" + self._normalize_and_hash(None)
        ]

        try:
            Gio.file_new_for_path(self.cacheDir).make_directory(None)
        except:
            pass

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

    def _make_icon_frame(self, pixbuf):
        border = 1.5
        w = pixbuf.get_width()
        h = pixbuf.get_height()
        pixbuf = pixbuf.scale_simple(w - border * 2,
                                     h - border * 2,
                                     0)

        result = self._draw_rounded_path(0, 0,
                                w, h,
                                3)
                                             
        pixbuf.copy_area(border, border,
                         w - border * 4,
                         h - border * 4,
                         result,
                         border * 2, border * 2)

        return result

    def _draw_rounded_path(self, x, y, width, height, radius):
        key = "%dx%d@%dx%d:%d" % (width, height, x, y, radius)
        if not key in self.frame_cache:
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                    width, height)
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
            self.frame_lock.acquire()
            self.frame_cache[key] = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)
            self.frame_lock.release()
        return self.frame_cache[key].copy()

    def lookup(self, item, width, height, callback, data=None):
        request = LookupRequest(item, width, height, callback, data)
        request.start()

    def _normalize_and_hash(self, input_str):
        normalized = " "

        if input_str and len(input_str) > 0:
            normalized = self._strip_invalid_entities(input_str)
            normalized = GLib.utf8_normalize(normalized, -1,
                                             GLib.NormalizeMode.NFKD)
            normalized = normalized.lower()

        return GLib.compute_checksum_for_string(GLib.ChecksumType.MD5,
                                                normalized, -1)

    def _strip_invalid_entities(self, original):
        # Strip blocks
        string = self.blocks.sub('', original)
        # Strip invalid chars
        string = self.invalid_chars.sub('', string)
        # Remove double spaces
        string = self.multiple_spaces.sub(' ', string)
        # Remove trailing spaces and convert to lowercase
        return string.strip().lower()

    def get_from_uri(self, uri, artist, album, width, height, callback, data=None):
        if not uri:
            return

        if not uri in self.requested_uris:
            request = GetUriRequest(uri, artist, album, self._on_get_uri_request_finish, data)
            self.requested_uris[uri] = request
        else:
            request = self.requested_uris[uri]

        request.callbacks.append([width, height, callback, data])
        if not request.started:
            request.start()

    def _on_get_uri_request_finish(self, request, data=None):
        del self.requested_uris[request.uri]
