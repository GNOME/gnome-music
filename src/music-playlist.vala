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

private class Music.Playlist: Object, Gee.Iterable<Grl.Media> {
	public signal void song_selected (Grl.Media media, int index);
	public signal void changed ();
	public signal void shuffle_mode_changed (bool mode);

	private Gee.ArrayList<Grl.Media> list;
	private int current_index = 0;

	private bool _shuffle;
	private GLib.Settings settings;


	private Gee.HashMap<string, Grl.Source> source_list = new Gee.HashMap<string, Grl.Source> ();

	public Playlist () {
        set_grl ();
        list = new Gee.ArrayList<Grl.Media> ();

        settings = new GLib.Settings ("org.gnome.Music");
        settings.changed.connect (on_settings_key_changed);
	}

	public bool shuffle {
        get { return _shuffle; }
        set {
            _shuffle = value;
            settings.set_boolean ("shuffle", value);
        }
    }

	public void select (Grl.Media media) {
		if (media in list) {
			current_index = list.index_of (media);
			song_selected (media, current_index);
		}
	}

	public void load_next () {
		if (current_index + 1 < list.size) {
			current_index++;
			song_selected (list[current_index], current_index);
		}
	}

	public void load_previous () {
		if (current_index > 0) {
			current_index--;
			song_selected (list[current_index], current_index);	
		}
	}

	public void load_album (Grl.Media media) {
		if (media is Grl.MediaBox) {
			list.clear();

            unowned GLib.List keys = Grl.MetadataKey.list_new (Grl.MetadataKey.ID,
                                                               Grl.MetadataKey.TITLE,
                                                               Grl.MetadataKey.URL);

            Grl.Caps caps = null;
            Grl.OperationOptions options = new Grl.OperationOptions(caps);
            options.set_skip (0);
            options.set_count (1000000);
            options.set_flags (Grl.ResolutionFlags.NORMAL);

            var id = media.get_id ();

            var query = @"SELECT rdf:type (?song)
                                 ?song
                                 tracker:id(?song) AS id
                                 tracker:coalesce (nie:title(?song), nfo:fileName(?song)) AS title
                                 ?duration
                                 nie:url(?song) AS url
                                 tracker:coalesce (nie:title(?album), '') AS site
                                 tracker:coalesce (nmm:artistName(?artist), '') AS author
                          WHERE { ?song a nmm:MusicPiece;
                                        nfo:duration ?duration;
                                        nmm:musicAlbum ?album FILTER (tracker:id (?album) = $id ) .
                                  OPTIONAL { ?song nmm:musicAlbum ?album } .
                                  OPTIONAL { ?album nmm:albumArtist ?artist }
                          }";

            foreach (var source in source_list.values) {
                source.query (query, keys, options, (source, query_id, media, remaining, error) => {
                    load_item_cb (media, remaining);
                });
            }
        }
	}

	private void load_item_cb (Grl.Media? media,
                               uint remaining) {
        if (media != null) {
        	list.add (media);
        }

        if (remaining == 0) {
        	changed();
        }
    }

	private void set_grl () {
        var registry = Grl.Registry.get_default ();

		registry.source_added.connect (source_added_cb);
		registry.source_removed.connect (source_removed_cb);
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

    private void on_settings_key_changed (string key) {
        if (key == "shuffle") {
        	shuffle_mode_changed (settings.get_boolean ("shuffle"));
        }
    }

	//Iterator methods

	public Type element_type {
        get { return typeof (Grl.Media); }
    }

    public Gee.Iterator<Grl.Media> iterator () {
        return list.iterator();
    }
}