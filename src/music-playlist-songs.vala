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
using Gee;

private class Music.PlaylistSongs {
    public Gtk.Widget actor { get { return alignment; } }
    private Gtk.Alignment alignment;
    private Gtk.Table table;

    private HashMap<string, Grl.Source> source_list = new HashMap<string, Grl.Source> ();

    public PlaylistSongs () {
        set_grl ();

        alignment = new Gtk.Alignment ((float)0.5, (float)0.5, 0, 0);
        alignment.show_all ();
    }

    public void load (Grl.Media media) {
        table = new Gtk.Table (0, 3, false);
        table.set_col_spacings (10);
        table.set_row_spacings (10);
        table.show();

        var child = alignment.get_child ();
        if (child != null) {
            alignment.remove (child);
        }
        alignment.add (table);

        if (media is Grl.MediaBox) {
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
                                 nie:title(?song) AS title
                                 ?duration
                          WHERE { ?song a nmm:MusicPiece;
                                        nfo:duration ?duration;
                                        nmm:musicAlbum ?album FILTER (tracker:id (?album) = $id ) }";

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
            table.resize (table.n_rows+1, 3);

            var title = new Gtk.Label (media.get_title ());
            title.set_alignment (0, (float)0.5);
            title.show();

            var duration = media.get_duration ();
            var length = new Gtk.Label (Music.seconds_to_string (duration));
            length.set_alignment (1, (float)0.5);
            length.get_style_context ().add_class ("dim-label");
            length.show();

            table.attach_defaults (title, 1, 2, table.n_rows-1, table.n_rows);
            table.attach_defaults (length, 2, 3, table.n_rows-1, table.n_rows);


        }
    }

    private void set_grl () {
        var registry = Grl.Registry.get_default ();

		registry.source_added.connect (source_added_cb);
		registry.source_removed.connect (source_removed_cb);

		if (registry.load_all_plugins () == false) {
			error ("Failed to load plugins.");
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
