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

internal enum Music.MusicListStoreColumn {
    TYPE = 0,
    ID,
    TITLE,
    ART,
    URL,
    DURATION,
    TRACK,
    ARTIST,
    ALBUM
}

internal enum Music.ItemType {
    ARTIST,
    ALBUM,
    SONG
}

internal class Music.MusicListStore : ListStore {
    public signal void finished ();

    private HashMap<string, Grl.Source> source_list = new HashMap<string, Grl.Source> ();
    private string running_query;
    private string running_query_params;

    public MusicListStore () {
        Object ();
       
        Type[] types = { typeof (Music.ItemType),       // MusicListStoreColumn.TYPE
                         typeof (string),       // MusicListStoreColumn.ID
                         typeof (string),       // MusicListStoreColumn.TITLE
                         typeof (Gdk.Pixbuf),   // MusicListStoreColumn.ART
                         typeof (string),       // MusicListStoreColumn.URL
                         typeof (string),       // MusicListStoreColumn.DURATION
                         typeof (uint),         // MusicListStoreColumn.TRACK
                         typeof (string),       // MusicListStoreColumn.ARTIST
                         typeof (string)};      // MusicListStoreColumn.ALBUM
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

    public void load_all_artists () {
        running_query = "load_all_artists";
        running_query_params = "";

        debug ("LOAD_ALL_ARTISTS");

        var query =  """SELECT ?artist
                            tracker:id(?artist) AS id
                            nmm:artistName(?artist) AS title
                        WHERE { ?artist a nmm:Artist}
                     """;

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
            source.query (query, keys, options, load_all_artists_cb);
        }
    }

    private void load_all_artists_cb (Grl.Source source,
                                      uint query_id,
                                      Grl.Media? media,
                                      uint remaining,
                                      GLib.Error? error) {
        if (media != null) {
            var pixbuf = new Gdk.Pixbuf.from_file (Path.build_filename (Config.PKGDATADIR, "album-art-default.png"));

            TreeIter iter;
            this.append (out iter);
            this.set (iter,
                    MusicListStoreColumn.TYPE,
                    Music.ItemType.ARTIST,
                    MusicListStoreColumn.ID,
                    media.get_id(),
                    MusicListStoreColumn.ART,
                    pixbuf,
                    MusicListStoreColumn.TITLE,
                    media.get_title ());
        }
    }

    public void load_all_albums () {
        running_query = "load_all_albums";
        running_query_params = "";

        debug ("LOAD_ALL_ALBUMS");

        var query =  """SELECT ?album
                            tracker:id(?album) AS id
                            nmm:albumTitle(?album) AS title
                        WHERE { ?album a nmm:MusicAlbum}
                     """;

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
            source.query (query, keys, options, load_all_albums_cb);
        }
    }

    private void load_all_albums_cb (Grl.Source source,
                                     uint query_id,
                                     Grl.Media? media,
                                     uint remaining,
                                     GLib.Error? error) {
        if (media != null) {
            var pixbuf = new Gdk.Pixbuf.from_file (Path.build_filename (Config.PKGDATADIR, "album-art-default.png"));

            TreeIter iter;
            this.append (out iter);
            this.set (iter,
                    MusicListStoreColumn.TYPE,
                    Music.ItemType.ALBUM,
                    MusicListStoreColumn.ID,
                    media.get_id(),
                    MusicListStoreColumn.ART,
                    pixbuf,
                    MusicListStoreColumn.TITLE,
                    media.get_title ());
        }
    }

    public void load_artist_albums (string artist) {
        running_query = "load_artist_albums";
        running_query_params = artist;

        debug ("LOAD_ARTIST_ALBUMS (%s)", artist);

        var query = @"SELECT ?album tracker:id(?album) AS id nmm:albumTitle(?album) AS title WHERE { ?album nmm:albumArtist [nmm:artistName '$artist'] }";

        this.clear ();

        unowned GLib.List keys = Grl.MetadataKey.list_new (Grl.MetadataKey.ID,
                                                           Grl.MetadataKey.TITLE,
                                                           Grl.MetadataKey.THUMBNAIL,
                                                           Grl.MetadataKey.URL);
        Caps caps = null;
        OperationOptions options = new OperationOptions(caps);
        options.set_skip (0);
        options.set_count (10000);
        options.set_flags (ResolutionFlags.NORMAL);

        foreach (var source in source_list.values) {
            source.query (query, keys, options, load_artist_albums_cb);
        }
    }

    private void load_artist_albums_cb (Grl.Source source,
                                     uint query_id,
                                     Grl.Media? media,
                                     uint remaining,
                                     GLib.Error? error) {
        if (media != null) {
            var pixbuf = new Gdk.Pixbuf.from_file (Path.build_filename (Config.PKGDATADIR, "album-art-default.png"));

            TreeIter iter;
            this.append (out iter);
            this.set (iter,
                    MusicListStoreColumn.TYPE,
                    Music.ItemType.ALBUM,
                    MusicListStoreColumn.ID,
                    media.get_id(),
                    MusicListStoreColumn.ART,
                    pixbuf,
                    MusicListStoreColumn.TITLE,
                    media.get_title ());
        }
    }

    public void load_all_songs () {
        running_query = "load_all_songs";
        running_query_params = "";

        debug ("LOAD_ALL_SONGS");

        var query =  """SELECT ?song
                            tracker:id(?song) AS id
                            nie:title(?song) AS title
                        WHERE { ?song a nmm:MusicPiece }
                     """;

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
            source.query (query, keys, options, load_all_songs_cb);
        }
    }

    private void load_all_songs_cb (Grl.Source source,
                                     uint query_id,
                                     Grl.Media? media,
                                     uint remaining,
                                     GLib.Error? error) {
        if (media != null) {
            var pixbuf = new Gdk.Pixbuf.from_file (Path.build_filename (Config.PKGDATADIR, "album-art-default.png"));

            TreeIter iter;
            this.append (out iter);
            this.set (iter,
                    MusicListStoreColumn.TYPE,
                    Music.ItemType.ALBUM,
                    MusicListStoreColumn.ID,
                    media.get_id(),
                    MusicListStoreColumn.ART,
                    pixbuf,
                    MusicListStoreColumn.TITLE,
                    media.get_title ());
        }
    }

    public void load_artist_songs (string artist) {
        this.clear ();
    }

    public void load_album_songs (string album) {
        running_query = "load_album_songs";
        running_query_params = album;

        debug ("LOAD_ALBUM_SONGS: %s", album);

        var query = @"SELECT ?song tracker:id(?song) AS id nie:title(?song) AS title WHERE { ?song nmm:musicAlbum [nmm:albumTitle '$album'] }";

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
            source.query (query, keys, options, load_album_songs_cb);
        }
    }

    private void load_album_songs_cb (Grl.Source source,
                                     uint query_id,
                                     Grl.Media? media,
                                     uint remaining,
                                     GLib.Error? error) {
        if (media != null) {
            var pixbuf = new Gdk.Pixbuf.from_file (Path.build_filename (Config.PKGDATADIR, "album-art-default.png"));

            TreeIter iter;
            this.append (out iter);
            this.set (iter,
                    MusicListStoreColumn.TYPE,
                    Music.ItemType.ALBUM,
                    MusicListStoreColumn.ID,
                    media.get_id(),
                    MusicListStoreColumn.ART,
                    pixbuf,
                    MusicListStoreColumn.TITLE,
                    media.get_title ());
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
                case "load_artist_albums":
                    load_artist_albums (running_query_params);
                    break;
                case "load_all_songs":
                    load_all_songs ();
                    break;
                case "load_album_songs":
                    load_album_songs (running_query_params);
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
