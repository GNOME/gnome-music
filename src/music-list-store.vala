/*
 * Copyright (C) 2012 Cesar Garcia Tapia <tapia@openshine.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

using Gtk;
using Grl;
using Gee;

private enum Music.ModelColumns {
    ID = Gd.MainColumns.ID,
    ART = Gd.MainColumns.ICON,
    TITLE = Gd.MainColumns.PRIMARY_TEXT,
    INFO = Gd.MainColumns.SECONDARY_TEXT,
    SELECTED = Gd.MainColumns.SELECTED,
    TYPE = Gd.MainColumns.LAST,
    MEDIA,
    LAST
}

private enum Music.ItemType {
    ARTIST,
    ALBUM,
    SONG
}

internal class Music.MusicListStore : ListStore {
    public signal void finished ();

    private HashMap<string, Grl.Source> source_list = new HashMap<string, Grl.Source> ();
    private string running_query;
    private string running_query_params;
    private Music.ItemType running_query_type;

    private Music.AlbumArtCache cache;
    private int ICON_SIZE = 96;

    public MusicListStore () {
        Object ();

        cache = AlbumArtCache.get_default ();

        Type[] types = { typeof (string),               // Music.ModelColumns.ID
                         typeof (string),
                         typeof (string),               // Music.ModelColumns.TITLE
                         typeof (string),               // Music.ModelColumns.INFO
                         typeof (Gdk.Pixbuf),           // Music.ModelColumns.ART
                         typeof (long),
                         typeof (bool),                 // Music.ModelColumns.SELECTED
                         typeof (Music.ItemType),       // Music.ModelColumns.TYPE
                         typeof (Grl.Media),            // Music.ModelColumns.MEDIA
                       };
       
        this.set_column_types (types);
    }

    public void connect_signals () {
        var registry = Grl.Registry.get_default ();

		registry.source_added.connect (source_added_cb);
		registry.source_removed.connect (source_removed_cb);

		if (registry.load_all_plugins () == false) {
			error ("Failed to load plugins.");
		}
    }

    public void load_item (string id, Music.ItemType? type) {
        if (type != null) {
            switch (type) {
                case Music.ItemType.ARTIST:
                    load_artist_albums_by_id (id);
                    break;
                case Music.ItemType.ALBUM:
                    load_album_songs_by_id (id);
                    break;
                case Music.ItemType.SONG:
                    break;
            }
        }
        else {
            switch (id) {
                case "all_artists":
                    load_all_artists ();
                    break;
                case "all_albums":
                    load_all_albums ();
                    break;
                case "all_songs":
                    load_all_songs ();
                    break;
            }
        }
    }

    private void load_all_artists () {
        running_query = "load_all_artists";
        running_query_params = "";
        running_query_type = Music.ItemType.ARTIST;

        var query =  "SELECT ?artist
                             tracker:id(?artist) AS id
                             nmm:artistName(?artist) AS title
                      WHERE { ?artist a nmm:Artist}
                      ORDER BY ?title";

        make_query (query);
    }

    private void load_all_albums () {
        running_query = "load_all_albums";
        running_query_params = "";
        running_query_type = Music.ItemType.ALBUM;

        var query = "SELECT ?album
                            tracker:id(?album) AS id
                            ?title
                            ?author
                            SUM(?length) AS duration
                            tracker:coalesce (fn:year-from-dateTime(?date), 'Unknown')
                     WHERE {
                            ?album a nmm:MusicAlbum ;
                                   nie:title ?title;
                                   nmm:albumArtist [ nmm:artistName ?author ] .
                            ?song nmm:musicAlbum ?album ;
                                  nfo:duration ?length
                            OPTIONAL { ?song nie:informationElementDate ?date }
                     } 
                     GROUP BY ?album
                     ORDER BY ?author ?title";

        make_query (query);
    }

    private void load_artist_albums_by_id (string id) {
        running_query = "load_artist_albums_by_id";
        running_query_params = id;
        running_query_type = Music.ItemType.ALBUM;

        var query = @"SELECT ?album
                             tracker:id(?album) AS id
                             ?title
                             nmm:artistName(?artist) AS author
                             SUM(?length) AS duration
                             tracker:coalesce (fn:year-from-dateTime(?date), 'Unknown')
                      WHERE { ?album a nmm:MusicAlbum;
                                     nie:title ?title;
                                     nmm:albumArtist ?artist FILTER (tracker:id (?artist) = $id) .
                              ?song nmm:musicAlbum ?album ;
                                    nfo:duration ?length .
                              OPTIONAL { ?song nie:informationElementDate ?date }
                      }
                      GROUP BY ?album
                      ORDER BY ?title";

        make_query (query);
    }

    private void load_all_songs () {
        running_query = "load_all_songs";
        running_query_params = "";
        running_query_type = Music.ItemType.SONG;

        var query =  "SELECT ?song
                             tracker:id(?song) AS id
                             nie:title(?song) AS title
                      WHERE { ?song a nmm:MusicPiece }";

        make_query (query);
    }

    private void load_album_songs_by_id (string id) {
        running_query = "load_album_songs_by_id";
        running_query_params = id;
        running_query_type = Music.ItemType.SONG;

        var query = @"SELECT ?song
                             tracker:id(?song) AS id
                             nie:title(?song) AS title
                      WHERE { ?song a nmm:MusicPiece;
                              nmm:musicAlbum ?album FILTER (tracker:id (?album) = $id ) }";

        make_query (query);
    }

    private void make_query (string query) {
        this.clear ();

        unowned GLib.List keys = Grl.MetadataKey.list_new (Grl.MetadataKey.ID,
                                                           Grl.MetadataKey.TITLE,
                                                           Grl.MetadataKey.THUMBNAIL,
                                                           Grl.MetadataKey.URL);

        Caps caps = null;
        OperationOptions options = new OperationOptions(caps);
        options.set_skip (0);
        options.set_count (1000000);
        options.set_flags (ResolutionFlags.NORMAL);

        foreach (var source in source_list.values) {
            source.query (query, keys, options, (source, query_id, media, remaining, error) => {
                load_item_cb (media, remaining);
            });
        }
    }

    private void load_item_cb (Grl.Media? media,
                               uint remaining) {
        if (media != null) {
            TreeIter iter;
            append (out iter);

            switch (running_query_type) {
                case Music.ItemType.ARTIST:
                    var pixbuf = cache.lookup (ICON_SIZE, media.get_title (), null);

                    set (iter, Music.ModelColumns.ID, media.get_id());
                    set (iter, Music.ModelColumns.ART, pixbuf);
                    set (iter, Music.ModelColumns.TITLE, media.get_title ());
                    set (iter, Music.ModelColumns.INFO, "");
                    set (iter, Music.ModelColumns.SELECTED, false);
                    set (iter, Music.ModelColumns.TYPE, Music.ItemType.ARTIST);
                    set (iter, Music.ModelColumns.MEDIA, media);
                    break;
                case Music.ItemType.ALBUM:
                    var pixbuf = cache.lookup (ICON_SIZE, media.get_author (), media.get_title());

                    set (iter, Music.ModelColumns.ID, media.get_id());
                    set (iter, Music.ModelColumns.ART, pixbuf);
                    set (iter, Music.ModelColumns.TITLE, media.get_title ());
                    set (iter, Music.ModelColumns.INFO, media.get_author ());
                    set (iter, Music.ModelColumns.SELECTED, false);
                    set (iter, Music.ModelColumns.TYPE, Music.ItemType.ALBUM);
                    set (iter, Music.ModelColumns.MEDIA, media);
                    break;
                case Music.ItemType.SONG:
                    set (iter, Music.ModelColumns.ID, media.get_id());
                    set (iter, Music.ModelColumns.ART, new Gdk.Pixbuf.from_file (media.get_thumbnail()));
                    set (iter, Music.ModelColumns.TITLE, media.get_title ());
                    set (iter, Music.ModelColumns.INFO, "");
                    set (iter, Music.ModelColumns.SELECTED, false);
                    set (iter, Music.ModelColumns.TYPE, Music.ItemType.SONG);
                    set (iter, Music.ModelColumns.MEDIA, media);
                    break;
            }
        }
    }

    private void re_run_query () {
        if (running_query != null) {
            switch (running_query) {
                case "load_all_artists":
                    load_all_artists ();
                    break;
                case "load_all_albums":
                    load_all_albums ();
                    break;
                case "load_all_songs":
                    load_all_songs ();
                    break;
                case "load_artist_albums_by_id":
                    load_artist_albums_by_id (running_query_params);
                    break;
            }
        }
    }

    private void source_added_cb (Grl.Source source) {
        // FIXME: We're only handling Tracker by now
        if (source.get_id() != "grl-tracker-source") {
            return;
        }

        debug ("Checking source: %s", source.get_id());

		var ops = source.supported_operations ();
		if ((ops & Grl.SupportedOps.QUERY) != 0) {
			debug ("Detected new source availabe: '%s' and it supports queries", source.get_name ());
			source_list.set (source.get_id(), source as Grl.Source);

            re_run_query ();
		}
	}

	private void source_removed_cb (Grl.Source source) {
        foreach (var id in source_list.keys) {
            if (id == source.get_id()) {
		        debug ("Source '%s' is gone", source.get_name ());
                source_list.unset (id);
            }
        }
	}
}
