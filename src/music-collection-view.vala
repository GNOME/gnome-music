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

internal enum CollectionType {
    ARTISTS = 0,
    ALBUMS,
    SONGS,
    PLAYLISTS
}

private class Music.CollectionView {
    public Gtk.Widget actor { get { return scrolled_window; } }

    private Music.MusicListStore model;
    private Gtk.ScrolledWindow scrolled_window;
    private Gtk.IconView icon_view;

    public CollectionView () {
        App.app.app_state_changed.connect (on_app_state_changed);

        model = new Music.MusicListStore (); 
        setup_view ();
        model.connect_signals();
    }

    private void setup_view () {
        icon_view = new Gtk.IconView.with_model (model);
        icon_view.get_style_context ().add_class ("music-bg");
        //icon_view.activate_on_single_click (true);
        icon_view.set_selection_mode (Gtk.SelectionMode.SINGLE);
        icon_view.item_activated.connect ((view, path) => {
            select_item (path);
        });

        icon_view.set_pixbuf_column (MusicListStoreColumn.ART);
        icon_view.set_text_column (MusicListStoreColumn.TITLE);

        scrolled_window = new Gtk.ScrolledWindow (null, null);
        scrolled_window.hscrollbar_policy = Gtk.PolicyType.NEVER;
        scrolled_window.add (icon_view);
        scrolled_window.show_all ();
    }

    private void on_app_state_changed (Music.AppState old_state, Music.AppState new_state) {
        switch (new_state) {
            case Music.AppState.ARTISTS:
                model.load_all_artists();
                break;
            case Music.AppState.ALBUMS:
                model.load_all_albums();
                break;
            case Music.AppState.SONGS:
                model.load_all_songs();
                break;
            case Music.AppState.PLAYLISTS:
            case Music.AppState.PLAYLIST:
            case Music.AppState.PLAYLIST_NEW:
                break;
        }
    }

    private void select_item (Gtk.TreePath path) {
        Gtk.TreeIter iter;
        GLib.Value type;
        GLib.Value name;

        model.get_iter (out iter, path);
        model.get_value (iter, MusicListStoreColumn.TYPE, out type);
        model.get_value (iter, MusicListStoreColumn.TITLE, out name);

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

    }
}
