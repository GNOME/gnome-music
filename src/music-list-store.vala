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
    ALBUM_ART,
    URL
}

internal class Music.MusicListStore : ListStore {
    public signal void finished ();

    private HashMap<string, Grl.Source> source_list = new HashMap<string, Grl.Source> ();

    public MusicListStore () {
        Object ();
       
        var registry = Grl.Registry.get_default ();

		registry.source_added.connect (source_added_cb);
		registry.source_removed.connect (source_removed_cb);

		if (registry.load_all_plugins () == false) {
			error ("Failed to load plugins.");
		}

        Type[] types = { typeof (uint),
                         typeof (string),
                         typeof (string),
                         typeof (string),
                         typeof (string),
                         typeof (Gdk.Pixbuf),
                         typeof (string)};
        this.set_column_types (types);
    }

    private void source_added_cb (Grl.Source source) {
        // FIXME: We're only handling Tracker by now
        if (source.get_id() != "grl-tracker-source") {
            return;
        }

        debug ("Checking source: %s", source.get_id());

		var ops = source.supported_operations ();
		if ((ops & Grl.SupportedOps.BROWSE) != 0) {
			debug ("Detected new source availabe: '%s' and it supports browsing", source.get_name ());
			source_list.set (source.get_id(), source as Grl.Source);
            this.fill_list_store (source.get_id(), null);
		}
        else {
            debug ("Source '%s' don't support browsing", source.get_name());
        }
	}

	public void source_removed_cb (Grl.Source source) {
        foreach (var id in source_list.keys) {
            if (id == source.get_id()) {
		        debug ("Source '%s' is gone", source.get_name ());
                source_list.unset (id);
            }
        }
	}

    private async void fill_list_store (string source_id, Grl.Media? root) {
        if (!(source_id in source_list.keys)) {
            return;
        }

        unowned GLib.List keys = Grl.MetadataKey.list_new (Grl.MetadataKey.ID, Grl.MetadataKey.TITLE); //, Grl.MetadataKey.URL);

        var source = source_list[source_id];
        debug ("browsing %s", source.get_name ());

        var options = new Grl.OperationOptions (source.get_caps (Grl.SupportedOps.BROWSE));
        options.set_skip (0);
        options.set_count (100);
//        options.set_flags (Grl.ResolutionFlags.FULL | Grl.ResolutionFlags.IDLE_RELAY);

        source.browse (root, keys, options, browse_cb);
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

            if (media != null) {
                if (media is MediaBox) {
                    debug ("Browsing %s", media.get_title());
                    this.fill_list_store (source.get_id(), media);
                }
                if (media is MediaAudio) {
                    var mediaAudio = media as MediaAudio;
                    debug ("Song: %s ", mediaAudio.get_thumbnail ()); 

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
                            MusicListStoreColumn.ALBUM_ART,
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
