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

const invalid_chars = /[()<>\[\]{}_!@#$^&*+=|\\\/\"'?~]/g;
const convert_chars = /[\t]/g;
const blocks = ["()", "{}", "[]", "<>"];


function escapeRegExp(str) {
    return str.replace(/[\(\)\[\]\<\>\{\}\_\!\@\#\$\^\&\*\+\=\|\\\/\"\'\?\~]/g, "\\$&");
}

String.prototype.printf = function() {
   var content = this;

   for (let i = 0; i < arguments.length; i++) {
        let replacement = '{' + i + '}';

        content = content.replace(replacement, arguments[i]);
   }

   return content;
};

const AlbumArtCache = new Lang.Class({
    Name: "AlbumArtCache",
    Extends: GLib.Object,

    _init: function() {
        this.parent();
        this.block_regexes = [];
        this.space_compress_regex = new RegExp("\\s+");

        for (let i in blocks) {
            let block = blocks[i],
                block_re = escapeRegExp(block[0]) + "[^" + escapeRegExp(block[1]) + "]*" + escapeRegExp(block[1]);

            this.block_regexes.push(new RegExp(block_re));
        }

        this.cache_dir = GLib.build_filenamev([GLib.get_user_cache_dir (), "media-art"]);
    },

    lookup: function(size, artist_, album_) {
        var artist = artist_,
            album = album_;

        if (artist == null) {
            artist = " " ;
        }

        if (album == null) {
            album = " ";
        }

        try {
            let key = "album-" + this.normalizeAndHash(artist) + "-" + this.normalizeAndHash(album);
            let path = GLib.build_filenamev([this.cache_dir, key + ".jpeg"]);

            return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, -1, true);
        }

        catch (error) {
            //print (error)
        }

        try {
            let key = "album-" + this.normalizeAndHash(artist, false, true) + "-" + this.normalizeAndHash(album, false, true);
            let path = GLib.build_filenamev([this.cache_dir, key + ".jpeg"]);

            return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, -1, true);
        }

        catch (error) {
            //print (error)
        }

        try {
            let key = "album-" + this.normalizeAndHash(" ", false, true) + "-" + this.normalizeAndHash(album, false, true);
            let path = GLib.build_filenamev([this.cache_dir, key + ".jpeg"]);

            return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, -1, true);
        }

        catch (error) {
            //print (error)
        }

        try {
            let key = "album-" + this.normalizeAndHash(artist + "\t" + album, true, true);
            let path = GLib.build_filenamev ([this.cache_dir, key + ".jpeg"]);

            return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, -1, true);
        }

        catch (error) {
            //print (error)
        }

        return null;
    },

    normalizeAndHash: function(input, utf8_only, utf8) {
        var normalized = " ";

        if (input != null && input != "") {
            if (utf8_only) {
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

        for (let i in this.block_regexes) {
            let re = this.block_regexes[i];

            result = result.replace(re, '');
        }

        result = result
            .replace(invalid_chars, '')
            .replace(convert_chars, ' ')
            .replace(this.space_compress_regex, ' ');

        return result;
    },

    getFromUri: function(uri, artist, album, width, height, callback) {
        if (uri != null) {
            print ("missing", album, artist)
            let key = "album-" + this.normalizeAndHash(artist) + "-" + this.normalizeAndHash(album);
            let path = GLib.build_filenamev([this.cache_dir, key + ".jpeg"]);
            var file = Gio.File.new_for_uri(uri);
            file.read_async(300, null, Lang.bind(this,
                function(source, res, user_data) {
                    var stream = file.read_finish(res);
                    var icon = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream, height, width, true, null);
                    var new_file = Gio.File.new_for_path(path);
                    file.copy(new_file, Gio.FileCopyFlags.NONE, null, null)
                    callback(icon);
            }));
        }
    }

});

AlbumArtCache.instance = null;

AlbumArtCache.getDefault = function() {
    if (AlbumArtCache.instance == null) {
        AlbumArtCache.instance = new AlbumArtCache();
    }

    return AlbumArtCache.instance;
};
