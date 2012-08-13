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
    TRACK = 0,
    TITLE,
    DURATION,
    ARTIST,
    ALBUM,
    ART,
    URL
}

internal class Music.MusicListStore : ListStore {
    public signal void finished ();

    private HashMap<string, Grl.Source> source_list = new HashMap<string, Grl.Source> ();
    private string running_query;
    private string running_query_params;

    public MusicListStore () {
        Object ();
       
        Type[] types = { typeof (uint),
                         typeof (string),
                         typeof (string),
                         typeof (string),
                         typeof (string),
                         typeof (Gdk.Pixbuf),
                         typeof (string)};
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

        var query =  """SELECT ?artist
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
                    MusicListStoreColumn.ART,
                    pixbuf,
                    MusicListStoreColumn.TITLE,
                    media.get_title ());
        }
    }

    public void load_all_albums () {
        running_query = "load_all_albums";
        running_query_params = "";

        var query =  """SELECT ?album
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
                    MusicListStoreColumn.ART,
                    pixbuf,
                    MusicListStoreColumn.TITLE,
                    media.get_title ());
        }
    }

    public void load_artist_albums (string artist) {
    }

    public void load_all_songs () {
        running_query = "load_all_songs";
        running_query_params = "";

        var query =  """SELECT ?song
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
                    MusicListStoreColumn.ART,
                    pixbuf,
                    MusicListStoreColumn.TITLE,
                    media.get_title ());
        }
    }



    public void load_artist_songs (string artist) {
    }

    public void load_album_songs (string album) {
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

    private void browse_cb (Grl.Source source,
                            uint browse_id,
                            Grl.Media? media,
                            uint remaining,
                            GLib.Error? error) {
        try {
            if (error != null) {
                critical ("Error: %s", error.message);
            }

            debug ("MEDIA: %s REMAINING: %u", media.get_title (), remaining);

            if (media != null) {
                if (media is MediaBox) {
                    debug ("Browsing %s", media.get_title());
                }
                if (media is MediaAudio) {
                    var mediaAudio = media as MediaAudio;
                    debug ("Song: %s ", mediaAudio.get_title ()); 

                    Gdk.Pixbuf pixbuf;
                    var thumbnail = mediaAudio.get_thumbnail ();
                    if (thumbnail != null) {
                        pixbuf = new Gdk.Pixbuf.from_file (thumbnail);
                    }
                    else {
                        pixbuf = new Gdk.Pixbuf.from_file (Path.build_filename (Config.PKGDATADIR, "album-art-default.png"));
                    }

                    TreeIter iter;
                    this.append (out iter);
                    this.set (iter,
                            MusicListStoreColumn.TRACK,
                            mediaAudio.get_track_number (),
                            MusicListStoreColumn.ALBUM,
                            mediaAudio.get_album (),
                            MusicListStoreColumn.ART,
                            pixbuf,
                            MusicListStoreColumn.TITLE,
                            mediaAudio.get_title (),
                            MusicListStoreColumn.URL,
                            mediaAudio.get_url (),
                            MusicListStoreColumn.DURATION,
                            mediaAudio.get_duration (),
                            MusicListStoreColumn.ARTIST,
                            mediaAudio.get_artist());
                }
            }

            if (remaining == 0) {
                debug ("%s finished", source.get_name ());
            }
        } catch (Error error) {
            critical ("Something failed: %s", error.message);
        }

    }
}
