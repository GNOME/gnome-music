from gi.repository import Gtk, GdkPixbuf, Gio, GLib, Grl, Gdk
from gettext import gettext as _
import cairo
from math import pi

import os
import re

from gnomemusic.grilo import grilo


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

        title = GLib.uri_unescape_string(basename, None)
        if escaped:
            return GLib.markup_escape_text(title)

        return title

    def __init__(self):
        self.logLookupErrors = False
        self.requested_uris = {}
        self.cacheDir = os.path.join(GLib.get_user_cache_dir(), "media-art")

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
        pixbuf = pixbuf.scale_simple(pixbuf.get_width() - border * 2,
                                     pixbuf.get_height() - border * 2,
                                     0)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                     int(pixbuf.get_width() + border * 2),
                                     int(pixbuf.get_height() + border * 2))
        ctx = cairo.Context(surface)
        self._draw_rounded_path(ctx, 0, 0,
                                pixbuf.get_width() + border * 2,
                                pixbuf.get_height() + border * 2,
                                3)
        result = Gdk.pixbuf_get_from_surface(surface, 0, 0,
                                             pixbuf.get_width() + border * 2,
                                             pixbuf.get_height() + border * 2)

        pixbuf.copy_area(border, border,
                         pixbuf.get_width() - border * 2,
                         pixbuf.get_height() - border * 2,
                         result,
                         border * 2, border * 2)

        return result

    def _draw_rounded_path(self, ctx, x, y, width, height, radius):
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

    def _try_load(self, size, artist, album, i, icon_format, callback):
        if i >= len(self._keybuilder_funcs):
            if icon_format == 'jpeg':
                self._try_load(size, artist, album, 0, 'png', callback)
            else:
                callback(None, None)
            return

        key = self._keybuilder_funcs[i].__call__(artist, album)
        path = GLib.build_filenamev([self.cacheDir, key + '.' + icon_format])
        f = Gio.File.new_for_path(path)

        def on_read_ready(obj, res, data=None):
            try:
                stream = obj.read_finish(res)

                def on_pixbuf_ready(source, res, data=None):
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(res)
                        width = pixbuf.get_width()
                        height = pixbuf.get_height()
                        if width >= size or height >= size:
                            scale = max(width, height) / size
                            callback(pixbuf.scale_simple(width / scale,
                                                         height / scale, 2),
                                     path)

                            return
                    except Exception as error:
                        if self.logLookupErrors:
                            print("ERROR:", error)

                    self._try_load(size, artist, album, i + 1,
                                   icon_format, callback)

                GdkPixbuf.Pixbuf.new_from_stream_async(stream, None,
                                                       on_pixbuf_ready, None)
                return

            except Exception as error:
                if self.logLookupErrors:
                    print("ERROR:", error)

            self._try_load(size, artist, album, i + 1, icon_format, callback)

        f.read_async(GLib.PRIORITY_DEFAULT, None, on_read_ready, None)

    def lookup(self, size, artist, album, callback):
        self._try_load(size, artist, album, 0, 'jpeg', callback)

    def lookup_or_resolve(self, item, width, height, callback):
        artist = item.get_string(Grl.METADATA_KEY_ARTIST) or item.get_author()
        album = item.get_string(Grl.METADATA_KEY_ALBUM)

        def lookup_ready(icon, path=None):
            if icon:
                # Cache the path on the original item for faster retrieval
                item._thumbnail = path
                callback(icon, path)
                return

            def resolve_ready(source, param, item, data, error):
                uri = item.get_thumbnail()
                if uri is None:
                    return

                self.get_from_uri(uri, artist, album, width, height,
                                  callback)

            options = Grl.OperationOptions()
            options.set_flags(Grl.ResolutionFlags.FULL |
                              Grl.ResolutionFlags.IDLE_RELAY)
            try:
                grilo.tracker.resolve(item, [Grl.METADATA_KEY_THUMBNAIL],
                                      options, resolve_ready, None)
            except:
                pass

        self.lookup(height, artist, album, lookup_ready)

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
