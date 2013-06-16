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
const Cairo = imports.cairo;
const GdkPixbuf = imports.gi.GdkPixbuf;
const GLib = imports.gi.GLib;
const Gtk = imports.gi.Gtk;
const Gdk = imports.gi.Gdk;
const Gio = imports.gi.Gio;
const Regex = GLib.Regex;
const Path = GLib.Path;
const Grl = imports.gi.Grl;

const Grilo = imports.grilo;
const grilo = Grilo.grilo;

const InvalidChars = /[()<>\[\]{}_!@#$^&*+=|\\\/\"'?~]/g;
const ReduceSpaces = /\t|\s+/g;

const AlbumArtCache = new Lang.Class({
    Name: "AlbumArtCache",
    Extends: GLib.Object,

    _init: function() {
        this.parent();
        this.logLookupErrors = false;
        this.requested_uris = {};
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

    _tryLoad: function(size, artist, album, i, format, callback) {
        var key, path, file;

        if (i >= this._keybuilder_funcs.length) {
            if (format == 'jpeg')
                this._tryLoad(size, artist, album, 0, 'png', callback);
            else
                callback(null);
            return;
        }

        key = this._keybuilder_funcs[i].call(this, artist, album);
        path = GLib.build_filenamev([this.cacheDir, key + '.' + format]);
        file = Gio.File.new_for_path(path);

        file.read_async(GLib.PRIORITY_DEFAULT, null, Lang.bind(this,
            function(object, res) {
                try {
                    let stream = object.read_finish(res);
                    GdkPixbuf.Pixbuf.new_from_stream_async(stream, null, Lang.bind(this,
                        function(source, res) {
                            try {
                                let pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(res),
                                    width = pixbuf.get_width(),
                                    height = pixbuf.get_height();
                                if (width >= size || height >= size) {
                                    let scale = Math.max(width, height)/size;
                                    callback(pixbuf.scale_simple(width/scale, height/scale, 2), path);

                                    return;
                                }
                            }
                            catch (error) {
                                if (this.logLookupErrors)
                                    print ("ERROR:", error);
                            }

                            this._tryLoad(size, artist, album, ++i, format, callback);
                        }));

                    return;
                }
                catch (error) {
                    if (this.logLookupErrors)
                        print ("ERROR:", error);
                }

                this._tryLoad(size, artist, album, ++i, format, callback);
            }));
    },

    lookup: function(size, artist, album, callback) {
        if (artist == null) {
            artist = " ";
        }

        if (album == null) {
            album = " ";
        }

        this._tryLoad(size, artist, album, 0, 'jpeg', callback);
    },

    lookupOrResolve: function(item, width, height, callback) {
        let artist = null;
        if (item.get_author() != null)
            artist = item.get_author();
        if (item.get_string(Grl.METADATA_KEY_ARTIST) != null)
            artist = item.get_string(Grl.METADATA_KEY_ARTIST);
        let album = item.get_string(Grl.METADATA_KEY_ALBUM);

        this.lookup(height, artist, album, Lang.bind(this, function(icon, path) {
            if (icon != null) {
                // Cache the path on the original item for faster retrieval
                item._thumbnail = path;
                callback(icon, path);
                return;
            }

            let options = Grl.OperationOptions.new(null);
            options.set_flags(Grl.ResolutionFlags.FULL | Grl.ResolutionFlags.IDLE_RELAY);
            grilo.tracker.resolve(item, [Grl.METADATA_KEY_THUMBNAIL], options,
                                  Lang.bind(this, function(source, param, item) {
                                      let uri = item.get_thumbnail();
                                      if (!uri)
                                          return;

                                      this.getFromUri(uri, artist, album, width, height,
                                                      function(image, path) {
                                                          item._thumbnail = path;
                                                          callback(image, path);
                                                      });
                                  }));
        }));
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
        if (this.requested_uris[uri] == undefined) {
            this.requested_uris[uri] = [[callback, width, height]];
        }
        else if (this.requested_uris[uri].length > 0) {
            this.requested_uris[uri].push([callback, width, height]);
            return;
        }

        let key = this._keybuilder_funcs[0].call(this, artist, album);
        let file = Gio.File.new_for_uri(uri);

        file.read_async(300, null, Lang.bind(this, function(source, res) {
            try {
                let stream = file.read_finish(res);
                let path = GLib.build_filenamev([this.cacheDir, key]);

                try {
                    let streamInfo = stream.query_info('standard::content-type', null);
                    let contentType = streamInfo.get_content_type();

                    if (contentType == 'image/png') {
                        path += '.png';
                    } else if (contentType == 'image/jpeg') {
                        path += '.jpeg';
                    } else {
                        log('Thumbnail is not in a supported format, not caching');
                        stream.close(null);
                        return;
                    }
                } catch(e) {
                    log('Failed to query thumbnail content type (%s), assuming JPG'.format(e.message));
                    path += '.jpeg';
                    return;
                }

                let newFile = Gio.File.new_for_path(path);

                newFile.replace_async(null, false, Gio.FileCreateFlags.REPLACE_DESTINATION,
                    300, null, Lang.bind(this, function (new_file, res, error) {
                    let outstream = new_file.replace_finish(res);
                    outstream.splice_async(stream, Gio.IOStreamSpliceFlags.NONE, 300, null,
                        Lang.bind(this, function(outstream, res, error) {
                            if (outstream.splice_finish(res) > 0) {
                               for (let i=0; i<this.requested_uris[uri].length; i++) {
                                   let callback = this.requested_uris[uri][i][0];
                                   let width = this.requested_uris[uri][i][1];
                                   let height = this.requested_uris[uri][i][2];

                                   let pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, height, width, true);
                                   callback(pixbuf, path);
                               }
                               delete this.requested_uris[uri];
                            }
                        }, null));
                }));
            }
            catch (error) {
                print (error);
            }
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
        let border = 1.5;
        pixbuf = pixbuf.scale_simple(pixbuf.get_width() - border * 2,
                                     pixbuf.get_height() - border * 2,
                                     0);

        let surface =  new Cairo.ImageSurface (Cairo.Format.ARGB32,
                                               pixbuf.get_width() + border * 2,
                                               pixbuf.get_height() + border * 2);
        let ctx = new Cairo.Context(surface);
        this.drawRoundedPath(ctx, 0, 0,
                             pixbuf.get_width()  + border * 2,
                             pixbuf.get_height()  + border * 2,
                             3);
        let result = Gdk.pixbuf_get_from_surface(surface, 0, 0,
            pixbuf.get_width() + border * 2, pixbuf.get_height() + border * 2);

        pixbuf.copy_area(border, border,
                        pixbuf.get_width() - border * 2,
                        pixbuf.get_height() - border * 2,
                        result,
                        border * 2, border * 2);

        return result;
    },

    drawRoundedPath: function (ctx, x, y, width, height, radius, preserve) {
        let degrees = Math.PI / 180;
        ctx.newSubPath();
        ctx.arc(x + width - radius, y + radius, radius - 0.5, -90 * degrees, 0 * degrees);
        ctx.arc(x + width - radius, y + height - radius, radius - 0.5, 0 * degrees, 90 * degrees);
        ctx.arc(x + radius, y + height - radius, radius - 0.5, 90 * degrees, 180 * degrees);
        ctx.arc(x + radius, y + radius, radius - 0.5, 180 * degrees, 270 * degrees);
        ctx.closePath();
        ctx.setLineWidth(0.6);
        ctx.setSourceRGB(0.2, 0.2, 0.2);
        ctx.strokePreserve();
        ctx.setSourceRGB(1, 1, 1);
        ctx.fill()
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
