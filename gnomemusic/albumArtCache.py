from gi.repository import GdkPixbuf, Gio, GLib, Grl, Gdk
import cairo
from math import pi

import os
import re

from gnomemusic.grilo import Grilo as grilo


class AlbumArtCache:
    instance = None

    @classmethod
    def getDefault(self):
        if self.instance:
            return self.instance
        else:
            self.instance = AlbumArtCache()
        return self.instance

    def __init__(self):
        self.logLookupErrors = False
        self.requested_uris = {}
        self.cacheDir = os.path.join(GLib.get_user_cache_dir(), "media-art")

        self._keybuilder_funcs = [
            lambda artist, album:
            "album-" + self.normalizeAndHash(artist) +
            "-" + self.normalizeAndHash(album),
            lambda artist, album:
            "album-" + self.normalizeAndHash(album) +
            "-" + self.normalizeAndHash(None)
        ]

        try:
            Gio.file_new_for_path(self.cacheDir).make_directory(None)
        except:
            pass

    def makeDefaultIcon(self, width, height):
        path = "/usr/share/icons/gnome/scalable/places/folder-music-symbolic.svg"
        # get a small pixbuf with the given path
        icon = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 
                    -1 if width < 0 else width/4,
                    -1 if height < 0 else height/4,
                    True)

        # create an empty pixbuf with the requested size
        result = GdkPixbuf.Pixbuf.new(icon.get_colorspace(),
                True,
                icon.get_bits_per_sample(),
                icon.get_width()*4,
                icon.get_height()*4)
        result.fill(0xffffffff)
        icon.composite(result,
                        icon.get_width()*3/2,
                        icon.get_height()*3/2,
                        icon.get_width(),
                        icon.get_height(),
                        icon.get_width()*3/2,
                        icon.get_height()*3/2,
                        1, 1,
                        GdkPixbuf.InterpType.NEAREST, 0xff)
        return self.makeIconFrame(result)

    def makeIconFrame(self, pixbuf):
        border = 1.5
        pixbuf = pixbuf.scale_simple(pixbuf.get_width() - border * 2,
                                     pixbuf.get_height() - border * 2,
                                     0)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                     int(pixbuf.get_width() + border * 2),
                                     int(pixbuf.get_height() + border * 2))
        ctx = cairo.Context(surface)
        self.drawRoundedPath(ctx, 0, 0,
                             pixbuf.get_width()  + border * 2,
                             pixbuf.get_height()  + border * 2,
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

    def drawRoundedPath(self, ctx, x, y, width, height, radius):
            degrees = pi / 180;
            ctx.new_sub_path()
            ctx.arc(x + width - radius, y + radius, radius - 0.5, -90 * degrees, 0 * degrees)
            ctx.arc(x + width - radius, y + height - radius, radius - 0.5, 0 * degrees, 90 * degrees)
            ctx.arc(x + radius, y + height - radius, radius - 0.5, 90 * degrees, 180 * degrees)
            ctx.arc(x + radius, y + radius, radius - 0.5, 180 * degrees, 270 * degrees)
            ctx.close_path()
            ctx.set_line_width(0.6)
            ctx.set_source_rgb(0.2, 0.2, 0.2)
            ctx.stroke_preserve()
            ctx.set_source_rgb(1, 1, 1)
            ctx.fill()

    def _tryLoad(self, size, artist, album, i, format, callback):
        if i >= len(self._keybuilder_funcs):
            if format == 'jpeg':
                self._tryLoad(size, artist, album, 0, 'png', callback)
            else:
                callback(None)
            return

        key = self._keybuilder_funcs[i].__call__( artist, album)
        path = GLib.build_filenamev([self.cacheDir, key + '.' + format])
        file = Gio.File.new_for_path(path)

        def on_read_ready(object, res, data=None):
            try:
                stream = object.read_finish(res)

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
                    except GLib.Error as error:
                        if self.logLookupErrors:
                            print("ERROR:", error)

                    self._tryLoad(size, artist, album, ++i, format, callback)

                GdkPixbuf.Pixbuf.new_from_stream_async(stream, None,
                                                       on_pixbuf_ready, None)
                return

            except GLib.Error as error:
                if (self.logLookupErrors):
                    print("ERROR:", error)

            self._tryLoad(size, artist, album, ++i, format, callback)

        file.read_async(GLib.PRIORITY_DEFAULT, None, on_read_ready, None)

    def lookup(self, size, artist, album, callback):
        self._tryLoad(size, artist, album, 0, 'jpeg', callback)

    def lookupOrResolve(self, item, width, height, callback):
        artist = None
        if item.get_author() is not None:
            artist = item.get_author()
        if item.get_string(Grl.METADATA_KEY_ARTIST) is not None:
            artist = item.get_string(Grl.METADATA_KEY_ARTIST)
        album = item.get_string(Grl.METADATA_KEY_ALBUM)

        def lookup_ready(icon, path):
            if icon is not None:
                # Cache the path on the original item for faster retrieval
                item._thumbnail = path
                callback(icon, path)
                return

            def resolve_ready(source, param, item):
                uri = item.get_thumbnail()
                if uri is not None:
                    return

                def get_from_uri_ready(image, path):
                    item._thumbnail = path
                    callback(image, path)
                self.getFromUri(uri, artist, album, width, height,
                                get_from_uri_ready)

            options = Grl.OperationOptions.new(None)
            options.set_flags(Grl.ResolutionFlags.FULL |
                              Grl.ResolutionFlags.IDLE_RELAY)
            grilo.tracker.resolve(item, [Grl.METADATA_KEY_THUMBNAIL],
                                  options, resolve_ready)

        self.lookup(height, artist, album, lookup_ready)

    def normalizeAndHash(self, input_str):
        normalized = " "

        if input_str is not None and len(input_str) > 0:
            normalized = self.stripInvalidEntities(input_str)
            normalized = GLib.utf8_normalize(normalized, -1,
                                             GLib.NormalizeMode.NFKD)
            normalized = normalized.lower()

        return GLib.compute_checksum_for_string(GLib.ChecksumType.MD5,
                                                normalized, -1)

    def stripFindNextBlock(self, original, open_char, close_char):
        open_pos = original.find(open_char)
        if open_pos >= 0:
            close_pos = original.find(close_char, open_pos + 1)
            if close_pos >= 0:
                return [True, open_pos, close_pos]

        return [False, -1, -1]

    def stripInvalidEntities(self, original):
        blocks_done = False
        invalid_chars = '[()<>\[\]{}_!@#$^&*+=|\\\/\"\'?~]'
        blocks = [['(', ')'], ['{', '}'], ['[', ']'], ['<', '>']]
        str_no_blocks = ""
        p = original

        while not blocks_done:
            pos1 = -1
            pos2 = -1

            for block_pair in blocks:
                # Go through blocks, find the earliest block we can
                [success, start, end] = self.stripFindNextBlock(p,
                                                                block_pair[0],
                                                                block_pair[1])
                if success:
                    if pos1 == -1 or start < pos1:
                        pos1 = start
                        pos2 = end

            # If either are -1 we didn't find any
            if pos1 == -1:
                # This means no blocks were found
                str_no_blocks += p
                blocks_done = True
            else:
                # Append the test BEFORE the block
                if pos1 > 0:
                    str_no_blocks += p[0:pos1]

                p = p[pos2 + 1:]

                # Do same again for position AFTER block
                if len(p) == 0:
                    blocks_done = True

        # Now convert chars to lower case
        str = str_no_blocks.lower()

        # Now strip invalid chars
        str = re.sub(invalid_chars, '', str)

        # Now convert tabs and multiple spaces into space
        str = re.sub('\t|\s+', ' ', str)

        # Now strip leading/trailing white space
        return str.strip()
