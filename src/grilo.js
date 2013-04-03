/*
 * Copyright (c) 2013 Eslam Mostafa <cseslam@gmail.com>.
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

    populateAlbums: function (offset, callback) {
        this.populateItems (Query.album, offset, callback)
    },

    populateSongs: function (offset, callback) {
        this.populateItems (Query.songs, offset, callback)
    },

    populateItems: function (query, offset, callback) {
        var options = Grl.OperationOptions.new(null);
        options.set_flags (Grl.ResolutionFlags.FULL | Grl.ResolutionFlags.IDLE_RELAY);
        options.set_count(50);
        query = query + " OFFSET " + offset;
        print ("populateItems:", query);
        grilo.tracker.query(
            query,
                [Grl.METADATA_KEY_ID, Grl.METADATA_KEY_TITLE, Grl.METADATA_KEY_ARTIST],
                options,
                Lang.bind(this, callback, null));
    },

    getAlbumSongs: function (album_id, callback) {
        var query =  Query.album_songs(album_id);
        print ("getAlbumSongs:", query);
        var options = Grl.OperationOptions.new(null);
        options.set_flags (Grl.ResolutionFlags.FULL | Grl.ResolutionFlags.IDLE_RELAY);
        grilo.tracker.query(
            query,
                [Grl.METADATA_KEY_ID, Grl.METADATA_KEY_TITLE, Grl.METADATA_KEY_ARTIST],
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
