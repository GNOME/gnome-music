from gi.repository import GdkPixbuf, Gio, GLib, Grl

import os
import re

from gnomemusic.grilo import Grilo


class AlbumArtCache:
    instance = None

    @classmethod
    def getDefault(self):
        if self.instance:
            return self.instance
        else:
            self.instance = AlbumArtCache()
        return self.instance

    def makeDefaultIcon(self, width, height):
        pass

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

    def _tryLoad(self, size, artist, album, i, format, callback):
        if i >= self._keybuilder_funcs.length:
            if format == 'jpeg':
                self._tryLoad(size, artist, album, 0, 'png', callback)
            else:
                callback(None)
            return

        key = self._keybuilder_funcs[i].call(self, artist, album)
        path = GLib.build_filenamev([self.cacheDir, key + '.' + format])
        file = Gio.File.new_for_path(path)

        def on_read_ready(object, res):
            try:
                stream = object.read_finish(res)

                def on_pixbuf_ready(source, res):
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
                                                       on_pixbuf_ready)
                return

            except GLib.Error as error:
                if (self.logLookupErrors):
                    print("ERROR:", error)

            self._tryLoad(size, artist, album, ++i, format, callback)

        file.read_async(GLib.PRIORITY_DEFAULT, None, on_read_ready)

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

        if input_str is not None and input_str.length() > 0:
            normalized = self.stripInvalidEntities(input_str)
            normalized = GLib.utf8_normalize(normalized, -1,
                                             GLib.NormalizeMode.NFKD)
            normalized = normalized.toLowerCase()

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
                if p.length == 0:
                    blocks_done = True

        # Now convert chars to lower case
        str = str_no_blocks.lower()

        # Now strip invalid chars
        str = re.sub(invalid_chars, '', str)

        # Now convert tabs and multiple spaces into space
        str = re.sub('\t|\s+', ' ', str)

        # Now strip leading/trailing white space
        return str.strip()
