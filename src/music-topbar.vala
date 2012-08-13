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

public enum Music.TopbarPage {
    COLLECTION = 0,
    SELECTION,
    PLAYLIST
}

private class Music.Topbar {
    public Gtk.Widget actor { get { return notebook; } }

    private Gtk.Notebook notebook;

    /* COLLECTION */
    public signal void collection_back_btn_clicked ();
    private Gtk.Button collection_new_btn;
    private Gtk.Button collection_back_btn;
    private Gtk.RadioButton collection_artists_btn;
    private Gtk.RadioButton collection_albums_btn;
    private Gtk.RadioButton collection_songs_btn;
    private Gtk.RadioButton collection_playlists_btn;
    private Gtk.Button collection_select_btn;

    /* SELECTION buttons */
    private Gtk.Button selection_back_btn;
    private Gtk.Button selection_remove_btn;
    private Gtk.Label selection_name_label; 
    private Gtk.Label selection_count_label;
    private Gtk.Button selection_cancel_btn;
    private Gtk.Button selection_add_btn;

    /* PLAYLIST buttons */
    private Gtk.Button playlist_back_btn;
    private Gtk.Button playlist_new_btn;
    private Gtk.Label playlist_name_label;
    private Gtk.Button playlist_select_btn;

    public Topbar () {
        setup_ui ();
        App.app.app_state_changed.connect ((old_state, new_state) => {
            on_app_state_changed (old_state, new_state);
        });
    }

    private void setup_ui () {
        notebook = new Gtk.Notebook ();

        /* TopbarPage.COLLECTION */
        var eventbox = new Gtk.EventBox ();
        eventbox.get_style_context ().add_class ("music-topbar");

        var hbox = new Gtk.Box (Orientation.HORIZONTAL, 0);
        var alignment = new Gtk.Alignment (0, 0, 1, 1);
        alignment.set_padding (5, 5, 5, 5);
        alignment.add (hbox);

        eventbox.add (alignment);
        notebook.append_page (eventbox, null);

        var toolbar_start = new Gtk.Box (Orientation.HORIZONTAL, 0);
        hbox.pack_start (toolbar_start);

        collection_new_btn = new Gtk.Button.with_label (_("New"));
        collection_new_btn.clicked.connect ((button) => {
            App.app.app_state = Music.AppState.PLAYLIST_NEW;
        });
        toolbar_start.pack_start (collection_new_btn, false, false, 0);

        collection_back_btn = new Gtk.Button ();
        collection_back_btn.set_image (new Gtk.Image.from_icon_name ("go-previous-symbolic", IconSize.BUTTON));
        collection_back_btn.clicked.connect (on_collection_back_btn_clicked);
        toolbar_start.pack_start (collection_back_btn, false, false, 0);

        var toolbar_center = new Gtk.Box (Orientation.HORIZONTAL, 0);
        toolbar_center.get_style_context ().add_class (Gtk.STYLE_CLASS_LINKED);
        hbox.pack_start (toolbar_center, false, false, 0);

        collection_artists_btn = new Gtk.RadioButton.with_label (null, _("Artists"));
        collection_artists_btn.set_mode (false);
        collection_artists_btn.toggled.connect ((button) => {
            if (button.get_active() == true) {
                App.app.app_state = Music.AppState.ARTISTS;
            }
        });
        toolbar_center.pack_start (collection_artists_btn, false, false, 0);

        collection_albums_btn = new Gtk.RadioButton.with_label (collection_artists_btn.get_group(), _("Albums"));
        collection_albums_btn.set_mode (false);
        collection_albums_btn.toggled.connect ((button) => {
            if (button.get_active() == true) {
                App.app.app_state = Music.AppState.ALBUMS;
            }
        });
        toolbar_center.pack_start (collection_albums_btn, false, false, 0);

        collection_songs_btn = new Gtk.RadioButton.with_label (collection_artists_btn.get_group(), _("Songs"));
        collection_songs_btn.set_mode (false);
        collection_songs_btn.toggled.connect ((button) => {
            if (button.get_active() == true) {
                App.app.app_state = Music.AppState.SONGS;
            }
        });
        toolbar_center.pack_start (collection_songs_btn, false, false, 0);

        collection_playlists_btn = new Gtk.RadioButton.with_label (collection_artists_btn.get_group(), _("Playlists"));
        collection_playlists_btn.set_mode (false);
        collection_playlists_btn.toggled.connect ((button) => {
            if (button.get_active() == true) {
                App.app.app_state = Music.AppState.PLAYLISTS;
            }
        });
        toolbar_center.pack_start (collection_playlists_btn, false, false, 0);

        var toolbar_end = new Gtk.Box (Orientation.HORIZONTAL, 0);

        collection_select_btn = new Gtk.Button ();
        collection_select_btn.set_image (new Gtk.Image.from_icon_name ("emblem-default-symbolic", IconSize.BUTTON));
        collection_select_btn.clicked.connect (() => {
            App.app.selection_mode = true;
        });

        update_collection_select_btn_sensitivity ();
        toolbar_end.pack_start (collection_select_btn, false, false, 0);

        alignment = new Gtk.Alignment (1, (float)0.5, 0, 0);
        alignment.add (toolbar_end);
        hbox.pack_start (alignment);

        /* TopbarPage.SELECTION */
        eventbox = new Gtk.EventBox ();
        eventbox.get_style_context ().add_class ("music-selection-mode");

        hbox = new Gtk.Box (Orientation.HORIZONTAL, 0);
        alignment = new Gtk.Alignment (0, 0, 1, 1);
        alignment.set_padding (5, 5, 5, 5);
        alignment.add (hbox);

        eventbox.add (alignment);
        notebook.append_page (eventbox, null);

        toolbar_start = new Gtk.Box (Orientation.HORIZONTAL, 5);
        hbox.pack_start (toolbar_start);

        selection_back_btn = new Gtk.Button ();
        selection_back_btn.get_style_context ().add_class ("dark");
        selection_back_btn.set_image (new Gtk.Image.from_icon_name ("go-previous-symbolic", IconSize.BUTTON));
        selection_back_btn.clicked.connect ((button) => {
        });
        toolbar_start.pack_start (selection_back_btn, false, false, 0);

        selection_remove_btn = new Gtk.Button.from_stock ("gtk-remove");
        selection_remove_btn.get_style_context ().add_class ("dark");
        selection_remove_btn.clicked.connect ((button) => {
        });
        toolbar_start.pack_start (selection_remove_btn, false, false, 0);

        toolbar_center = new Gtk.Box (Orientation.HORIZONTAL, 0);
        hbox.pack_start (toolbar_center, false, false, 0);

        selection_name_label = new Gtk.Label (_("Collection name"));
        selection_count_label = new Gtk.Label ("");
        toolbar_center.pack_start (selection_name_label, false, false, 0);
        toolbar_center.pack_start (selection_count_label, false, false, 0);

        toolbar_end = new Gtk.Box (Orientation.HORIZONTAL, 5);

        selection_cancel_btn = new Gtk.Button.with_label (_("Cancel"));
        selection_cancel_btn.get_style_context ().add_class ("dark");
        selection_cancel_btn.clicked.connect ((button) => {
        });
        toolbar_end.pack_start (selection_cancel_btn, false, false, 0);

        selection_add_btn = new Gtk.Button.from_stock ("gtk-add");
        selection_add_btn.clicked.connect ((button) => {
        });
        toolbar_end.pack_start (selection_add_btn, false, false, 0);

        alignment = new Gtk.Alignment (1, (float)0.5, 0, 0);
        alignment.add (toolbar_end);
        hbox.pack_start (alignment);

        /* TopbarPage.PLAYLIST */
        eventbox = new Gtk.EventBox ();
        eventbox.get_style_context ().add_class ("music-topbar");

        hbox = new Gtk.Box (Orientation.HORIZONTAL, 0);
        alignment = new Gtk.Alignment (0, 0, 1, 1);
        alignment.set_padding (5, 5, 5, 5);
        alignment.add (hbox);

        eventbox.add (alignment);
        notebook.append_page (eventbox, null);

        toolbar_start = new Gtk.Box (Orientation.HORIZONTAL, 5);
        hbox.pack_start (toolbar_start);

        playlist_back_btn = new Gtk.Button ();
        playlist_back_btn.set_image (new Gtk.Image.from_icon_name ("go-previous-symbolic", IconSize.BUTTON));
        playlist_back_btn.clicked.connect ((button) => {
        });
        toolbar_start.pack_start (playlist_back_btn, false, false, 0);

        toolbar_center = new Gtk.Box (Orientation.HORIZONTAL, 0);
        hbox.pack_start (toolbar_center, false, false, 0);

        playlist_name_label = new Gtk.Label (_("Collection name"));
        toolbar_center.pack_start (playlist_name_label, false, false, 0);

        toolbar_end = new Gtk.Box (Orientation.HORIZONTAL, 5);

        playlist_select_btn = new Gtk.Button ();
        playlist_select_btn.set_image (new Gtk.Image.from_icon_name ("emblem-default-symbolic", IconSize.BUTTON));
        playlist_select_btn.clicked.connect (() => {
            App.app.selection_mode = true;
        });

        toolbar_end.pack_start (playlist_select_btn, false, false, 0);

        alignment = new Gtk.Alignment (1, (float)0.5, 0, 0);
        alignment.add (toolbar_end);
        hbox.pack_start (alignment);

        notebook.show_tabs = false;
        notebook.show_all ();

        /* Let's init the widgets visibility */
        collection_new_btn.set_visible (false);
        collection_back_btn.set_visible (false);
    }

    public void set_collection_back_button_visible (bool visible) {
        collection_back_btn.set_visible (visible);
    }
                
    private void on_app_state_changed (Music.AppState old_state, Music.AppState new_state) {
        switch (new_state) {
            case Music.AppState.ARTISTS:
            case Music.AppState.ALBUMS:
            case Music.AppState.SONGS:
            case Music.AppState.PLAYLISTS:
                notebook.set_current_page (TopbarPage.COLLECTION);
                break;
            case Music.AppState.PLAYLIST:
                notebook.set_current_page (TopbarPage.COLLECTION);
                break;
            case Music.AppState.PLAYLIST_NEW:
                notebook.set_current_page (TopbarPage.COLLECTION);
                break;
        }
    }

    private void on_collection_back_btn_clicked (Gtk.Button button) {
        collection_back_btn_clicked ();
    }

    private void update_collection_select_btn_sensitivity () {
//        collection_select_btn.sensitive = App.app.collection.items.length != 0;
    }

    private void update_selection_count_label () {
        /*
        var items = App.app.selected_items.length ();
        if (items > 0)
            selection_count_label.set_markup ("<b>" + ngettext ("%d selected", "%d selected", items).printf (items) + "</b>");
        else
            selection_count_label.set_markup ("<i>" + _("Click on items to select them") + "</i>");
        */
    }
}
