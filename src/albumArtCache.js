/*
 * Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>.
 *
 * Gnome Music is free software; you can Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 *
 * Gnome Music is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with Gnome Music; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
 *
 */

const Lang = imports.lang;
const GdkPixbuf = imports.gi.GdkPixbuf;
const GLib = imports.gi.GLib;
const Gio = imports.gi.Gio;
const Regex = GLib.Regex;
const Path = GLib.Path;
const Grl = imports.gi.Grl;

const InvalidChars = /[()<>\[\]{}_!@#$^&*+=|\\\/\"'?~]/g;
const ReduceSpaces = /\t|\s+/g;

const AlbumArtCache = new Lang.Class({
    Name: "AlbumArtCache",
    Extends: GLib.Object,

    _init: function() {
        this.parent();
        this.logLookupErrors = false;

        this.cacheDir = GLib.build_filenamev([
            GLib.get_user_cache_dir(),
            "media-art"
        ]);
    },

    lookup: function(size, artist, album) {
        var key, path;

        if (artist == null) {
            artist = " ";
        }

        if (album == null) {
            album = " ";
        }

        try {
            key = "album-" + this.normalizeAndHash(artist) + "-" + this.normalizeAndHash(album);
            path = GLib.build_filenamev([this.cacheDir, key + ".jpeg"]);

            return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, -1, true);
        }

        catch (error) {
            if (this.logLookupErrors) log(error);
        }

        try {
            key = "album-" + this.normalizeAndHash(artist, false, true) + "-" + this.normalizeAndHash(album, false, true);
            path = GLib.build_filenamev([this.cacheDir, key + ".jpeg"]);

            return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, -1, true);
        }

        catch (error) {
            if (this.logLookupErrors) log(error);
        }

        try {
            key = "album-" + this.normalizeAndHash(" ", false, true) + "-" + this.normalizeAndHash(album, false, true);
            path = GLib.build_filenamev([this.cacheDir, key + ".jpeg"]);

            return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, -1, true);
        }

        catch (error) {
            if (this.logLookupErrors) log(error);
        }

        try {
            key = "album-" + this.normalizeAndHash(artist + "\t" + album, true, true);
            path = GLib.build_filenamev([this.cacheDir, key + ".jpeg"]);

            return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, -1, true);
        }

        catch (error) {
            if (this.logLookupErrors) log(error);
        }

        return null;
    },

    normalizeAndHash: function(input, utf8Only, utf8) {
        var normalized = " ";

        if (input != null && input != "") {
            if (utf8Only) {
                normalized = input;
            }

            else {
                normalized = this.stripInvalidEntities(input);
                normalized = normalized.toLowerCase();
            }

            if (utf8) {
                normalized = GLib.utf8_normalize(normalized, -1, 2)
            }
        }

        return GLib.compute_checksum_for_string(GLib.ChecksumType.MD5, normalized, -1);
    },

    stripInvalidEntities: function(original) {
        var result = original;

        result = result
            .replace(InvalidChars, '')
            .replace(ReduceSpaces, ' ');

        return result;
    },

    getFromUri: function(uri, artist, album, width, height, callback) {
        if (uri == null) return;

        let key = "album-" + this.normalizeAndHash(artist) + "-" + this.normalizeAndHash(album),
            path = GLib.build_filenamev([
                this.cacheDir, key + ".jpeg"
            ]),
            file = Gio.File.new_for_uri(uri);

        print("missing", album, artist);

        file.read_async(300, null, function(source, res, user_data) {
            var stream = file.read_finish(res),
                icon = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream, height, width, true, null),
                new_file = Gio.File.new_for_path(path);

            file.copy(new_file, Gio.FileCopyFlags.NONE, null, null);
            callback(icon);
        });
    }

});

AlbumArtCache.instance = null;

AlbumArtCache.getDefault = function() {
    if (AlbumArtCache.instance == null) {
        AlbumArtCache.instance = new AlbumArtCache();
    }

    return AlbumArtCache.instance;
};