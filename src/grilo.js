/*
 * Copyright (c) 2013 Eslam Mostafa <cseslam@gmail.com>.
 * Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>.
 *
 * Gnome Music is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 *
 * The Gnome Music authors hereby grant permission for non-GPL compatible
 * GStreamer plugins to be used and distributed together with GStreamer and
 * Gnome Music. This permission is above and beyond the permissions granted by
 * the GPL license by which Gnome Music is covered. If you modify this code, you may 
 * extend this exception to your version of the code, but you are not obligated 
 * to do so. If you do not wish to do so, delete this exception statement from 
 * your version.
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
 *
 */

const Grl = imports.gi.Grl;
const Lang = imports.lang;
const Signals = imports.signals;
const Tracker = imports.gi.Tracker;
const Query = imports.query;
const tracker = Tracker.SparqlConnection.get (null);

Grl.init (null, 0);
const Grilo = new Lang.Class({
    Name: 'Grilo',

    _init: function() {
        this.registry = Grl.Registry.get_default ();
        this.registry.load_all_plugins();

        let sources = {};
        this.sources = sources;
        this.tracker = null;

        this.registry.connect ("source_added",
            Lang.bind(this, this._onSourceAdded));

        this.registry.connect ("source_removed",
            function (pluginRegistry, mediaSource) {
                log ("source removed");
            });

        if (this.registry.load_all == false) {
            log ("Failed to load plugins.");
        }
    },

    _onSourceAdded: function(pluginRegistry, mediaSource) {
        if (mediaSource.sourceId == "grl-tracker-source") {
            let ops = mediaSource.supported_operations ();
            if (ops & Grl.SupportedOps.SEARCH) {
        print ("Detected new source availabe: '" +
                     mediaSource.get_name () +
                     "' and it supports search");
                this.sources[mediaSource.sourceId] = mediaSource;
                this.tracker = mediaSource;
                if (this.tracker != null)
                    this.emit('ready');
            }
        }
    },

    populateArtists: function (offset, callback) {
        this.populateItems (Query.artist, offset, callback)
    },

    populateAlbums: function (offset, callback, count=50) {
        this.populateItems (Query.album, offset, callback, count)
    },

    populateSongs: function (offset, callback) {
        this.populateItems (Query.songs, offset, callback)
    },

    populateItems: function (query, offset, callback, count=50) {
        var options = Grl.OperationOptions.new(null);
        options.set_flags (Grl.ResolutionFlags.FULL | Grl.ResolutionFlags.IDLE_RELAY);
        options.set_skip (offset);
        options.set_count(count);
        grilo.tracker.query(
            query,
                [Grl.METADATA_KEY_ID, Grl.METADATA_KEY_TITLE, Grl.METADATA_KEY_ARTIST, Grl.METADATA_KEY_ALBUM, Grl.METADATA_KEY_DURATION, Grl.METADATA_KEY_THUMBNAIL, Grl.METADATA_KEY_CREATION_DATE],
                options,
                Lang.bind(this, callback, null));
    },

    getAlbumSongs: function (album_id, callback) {
        var query =  Query.album_songs(album_id);
        var options = Grl.OperationOptions.new(null);
        options.set_flags (Grl.ResolutionFlags.FULL | Grl.ResolutionFlags.IDLE_RELAY);
        grilo.tracker.query(
            query,
                [Grl.METADATA_KEY_ID, Grl.METADATA_KEY_TITLE, Grl.METADATA_KEY_ARTIST, Grl.METADATA_KEY_ALBUM, Grl.METADATA_KEY_DURATION, Grl.METADATA_KEY_THUMBNAIL, Grl.METADATA_KEY_CREATION_DATE],
                options,
                Lang.bind(this, callback, null));
    },

    _searchCallback: function search_cb () {
        log ("yeah");
    },

    search: function (q) {
        for each (let source in this.sources) {
            log (source.get_name () + " - " + q);
            source.search (q, [Grl.METADATA_KEY_ID], 0, 10,
                           Grl.MetadataResolutionFlags.FULL |
                               Grl.MetadataResolutionFlags.IDLE_RELAY,
                           this._searchCallback, source);
        }
    },
});
Signals.addSignalMethods(Grilo.prototype);

let grilo = new Grilo();
