/*
 * Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>.
 * Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>.
 * Copyright (c) 2013 Matteo Settenvini <matteo@member.fsf.org>
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

        this.requested_uris = [];
        this.cacheDir = GLib.build_filenamev([
            GLib.get_user_cache_dir(),
            "media-art"
        ]);
        try {
            var file = Gio.file_new_for_path(this.cacheDir);
            file.make_directory(null);
        }
        catch (error) {
        }
    },

    lookup: function(size, artist, album) {
        var key, path;

        if (artist == null) {
            artist = " ";
        }

        if (album == null) {
            album = " ";
        }

        for (var i = 0; i < this._keybuilder_funcs.length; i++)
        {
            try {
                key = this._keybuilder_funcs[i].call (this, artist, album);
                path = GLib.build_filenamev([this.cacheDir, key + ".jpeg"]);

                return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, -1, true);
            }
            catch (error) {
                if (this.logLookupErrors)
                    log(error);
            }
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
        if (this.requested_uris.indexOf(uri) >= 0) return;

        this.requested_uris.push(uri);

        let key = this._keybuilder_funcs[0].call(this, artist, album),
            path = GLib.build_filenamev([
                this.cacheDir, key + ".jpeg"
            ]),
            file = Gio.File.new_for_uri(uri);

        print("missing", album, artist);

        file.read_async(300, null, Lang.bind(this, function(source, res, user_data) {
            let stream = file.read_finish(res),
                new_file = Gio.File.new_for_path(path);
                new_file.append_to_async(Gio.IOStreamSpliceFlags.NONE,
                    300, null, Lang.bind(this, function (new_file, res, error) {
                    let outstream = new_file.append_to_finish(res);
                    outstream.splice_async(stream, Gio.IOStreamSpliceFlags.NONE, 300, null,
                        Lang.bind(this, function(outstream, res, error) {
                            if (outstream.splice_finish(res) > 0)
                               callback(GdkPixbuf.Pixbuf.new_from_file_at_scale(path, height, width, true));
                        }, null));
                }));
        }));
    },

    makeDefaultIcon: function(w, h) {
        let path = "/usr/share/icons/gnome/scalable/places/folder-music-symbolic.svg";
        //get a small pixbuf with the given path
        let icon = GdkPixbuf.Pixbuf.new_from_file_at_scale(path,
                    w < 0 ? -1 : w/4,
                    h < 0 ? -1 : h/4,
                    true);

        //create an empty pixbuf with the requested size
        let result = GdkPixbuf.Pixbuf.new(icon.get_colorspace(),
                true,
                icon.get_bits_per_sample(),
                icon.get_width()*4,
                icon.get_height()*4);
        result.fill(0xffffffff);
        icon.composite(result,
                        icon.get_width()*3/2,
                        icon.get_height()*3/2,
                        icon.get_width(),
                        icon.get_height(),
                        icon.get_width()*3/2,
                        icon.get_height()*3/2,
                        1, 1,
                        GdkPixbuf.InterpType.NEAREST, 0xff)
        return this.makeIconFrame(result);
    },

    makeIconFrame: function (pixbuf) {
        var border = 3;
        var color = 0xffffffff;
        var result = GdkPixbuf.Pixbuf.new(pixbuf.get_colorspace(),
                                true,
                                pixbuf.get_bits_per_sample(),
                                pixbuf.get_width(),
                                pixbuf.get_height());
        result.fill(color);
        pixbuf.copy_area(border, border,
                        pixbuf.get_width() - (border * 2), pixbuf.get_height() - (border * 2),
                        result,
                        border, border);

        pixbuf = result;

        border = 1;
        color = 0x00000044;
        var result2 = GdkPixbuf.Pixbuf.new(pixbuf.get_colorspace(),
                                true,
                                pixbuf.get_bits_per_sample(),
                                pixbuf.get_width(),
                                pixbuf.get_height());
        result2.fill(color);
        pixbuf.copy_area(border, border,
                        pixbuf.get_width() - (border * 2), pixbuf.get_height() - (border * 2),
                        result2,
                        border, border);

        return result2;
    },

    _keybuilder_funcs: [
        function (artist, album) { return "album-" + this.normalizeAndHash(artist) + "-" + this.normalizeAndHash(album); },
        function (artist, album) { return "album-" + this.normalizeAndHash(artist, false, true) + "-" + this.normalizeAndHash(album, false, true); },
        function (artist, album) { return "album-" + this.normalizeAndHash(" ", false, true) + "-" + this.normalizeAndHash(album, false, true); },
        function (artist, album) { return "album-" + this.normalizeAndHash(artist + "\t" + album, true, true); }
    ]

});

AlbumArtCache.instance = null;

AlbumArtCache.getDefault = function() {
    if (AlbumArtCache.instance == null) {
        AlbumArtCache.instance = new AlbumArtCache();
    }

    return AlbumArtCache.instance;
};
