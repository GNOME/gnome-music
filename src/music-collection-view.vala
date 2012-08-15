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

internal enum Music.CollectionType {
    ARTISTS = 0,
    ALBUMS,
    SONGS,
    PLAYLISTS
}

private class Music.BrowseHistory {
    private ArrayList<string> history;
    private HashMap<string, Music.ItemType?> history_types;

    public BrowseHistory () {
        history = new ArrayList<string>(); 
        history_types = new HashMap<string, Music.ItemType?>();
    }

    public void push (string id, Music.ItemType? item_type)
    {
        history.add (id);
        history_types.set (id, item_type);
    }

    public string get_last_item_id () {
        if (history.size >= 2) {
            // (history.size - 1) is the actual item, so we want the previous one
            var last = history.size - 2;
            return history[last];
        }

        return "";
    }

    public Music.ItemType? get_last_item_type () {
        string id = get_last_item_id ();
        return history_types[id];
    }

    public void delete_last_item () {
        // We want to go back one position in the history, so we only need to
        // delete the actual item (history.size - 1).
        var last = history.size - 1;
        var id = get_last_item_id ();
        history.remove_at (last);
        history_types.unset (id);
    }

    public int get_length () {
        return history.size;
    }

    public void clear () {
        history.clear();
        history_types.clear();
    }
}

private class Music.CollectionView {
    public Gtk.Widget actor { get { return scrolled_window; } }

    public signal void browse_history_changed (BrowseHistory browse_history);

    private Music.MusicListStore model;
    private Music.BrowseHistory browse_history;

    private Gtk.ScrolledWindow scrolled_window;
    private Gtk.IconView icon_view;

    public CollectionView () {
        App.app.app_state_changed.connect (on_app_state_changed);

        browse_history = new Music.BrowseHistory ();
        model = new Music.MusicListStore (); 
        setup_view ();
        model.connect_signals();
    }

    private void setup_view () {
        icon_view = new Gtk.IconView.with_model (model);
        icon_view.get_style_context ().add_class ("music-bg");
        //icon_view.activate_on_single_click (true);
        icon_view.set_selection_mode (Gtk.SelectionMode.SINGLE);
        icon_view.item_activated.connect (on_item_activated);
        icon_view.set_pixbuf_column (MusicListStoreColumn.ART);
        icon_view.set_text_column (MusicListStoreColumn.TITLE);

        scrolled_window = new Gtk.ScrolledWindow (null, null);
        scrolled_window.hscrollbar_policy = Gtk.PolicyType.NEVER;
        scrolled_window.add (icon_view);

        icon_view.show ();
        scrolled_window.show ();
    }

    public void browse_history_back () {
        var last_item_id = browse_history.get_last_item_id ();
        Music.ItemType? last_item_type = browse_history.get_last_item_type ();
        browse_history.delete_last_item ();
        model.load_item (last_item_id, last_item_type);
    }

    private void on_app_state_changed (Music.AppState old_state, Music.AppState new_state) {
        browse_history.clear();

        switch (new_state) {
            case Music.AppState.ARTISTS:
                browse_history.push ("all_artists", null);
                model.load_all_artists();
                break;
            case Music.AppState.ALBUMS:
                browse_history.push ("all_albums", null);
                model.load_all_albums();
                break;
            case Music.AppState.SONGS:
                browse_history.push ("all_songs", null);
                model.load_all_songs();
                break;
            case Music.AppState.PLAYLISTS:
            case Music.AppState.PLAYLIST:
            case Music.AppState.PLAYLIST_NEW:
                break;
        }
    }

    private void on_item_activated (Gtk.TreePath path) {
        Gtk.TreeIter iter;
        GLib.Value id;
        GLib.Value type;
        GLib.Value name;

        model.get_iter (out iter, path);
        model.get_value (iter, MusicListStoreColumn.ID, out id);
        model.get_value (iter, MusicListStoreColumn.TYPE, out type);
        model.get_value (iter, MusicListStoreColumn.TITLE, out name);

        var item_id = (string) id;
        var item_type = (Music.ItemType) type;
        var item_name = (string) name;

        switch (item_type) {
            case Music.ItemType.ARTIST:
                App.app.app_state_changed.disconnect (on_app_state_changed);
                App.app.app_state = Music.AppState.ALBUMS;
                App.app.app_state_changed.connect (on_app_state_changed);
                
                model.load_artist_albums(item_name);
                break;
            case Music.ItemType.ALBUM:
                App.app.app_state_changed.disconnect (on_app_state_changed);
                App.app.app_state = Music.AppState.SONGS;
                App.app.app_state_changed.connect (on_app_state_changed);

                model.load_album_songs (item_name);
                break;
            case Music.ItemType.SONG:
                model.load_all_songs();
                break;
        }

        browse_history.push (item_id, item_type);
        browse_history_changed (browse_history);

    }
}
