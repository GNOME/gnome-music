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
    COLLECTION,
    SELECTION,
    PLAYLIST
}

private class Music.Topbar: Music.UI {
    public Gtk.Widget actor { get { return notebook; } }

    private const uint height = 50;

    private Notebook notebook;

    /* COLLECTION buttons */
    private Gtk.Button collection_new_btn;
    private Gtk.ToggleButton collection_artists_btn;
    private Gtk.ToggleButton collection_albums_btn;
    private Gtk.ToggleButton collection_songs_btn;
    private Gtk.ToggleButton collection_playlists_btn;
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
        setup_topbar ();

        App.app.notify["selected-items"].connect (() => {
            update_selection_count_label ();
        });
    }

    private void setup_topbar () {
        notebook = new Gtk.Notebook ();
        notebook.set_size_request (50, (int) height);

        /* TopbarPage.COLLECTION */
        var hbox = new Gtk.Box (Orientation.HORIZONTAL, 0);
        var alignment = new Gtk.Alignment (0, 0, 1, 1);
        alignment.set_padding (5, 5, 5, 5);
        alignment.add (hbox);
        notebook.append_page (alignment, null);

        var toolbar_start = new Gtk.Box (Orientation.HORIZONTAL, 0);
        hbox.pack_start (toolbar_start);

        collection_new_btn = new Gtk.Button.with_label (_("New"));
        collection_new_btn.clicked.connect ((button) => { App.app.ui_state = UIState.WIZARD; });
        toolbar_start.pack_start (collection_new_btn, false, false, 0);

        var toolbar_center = new Gtk.Box (Orientation.HORIZONTAL, 0);
        toolbar_center.get_style_context ().add_class (Gtk.STYLE_CLASS_LINKED);
        hbox.pack_start (toolbar_center, false, false, 0);

        collection_artists_btn = new Gtk.ToggleButton.with_label (_("Artists"));
        collection_artists_btn.clicked.connect ((button) => {
        });
        toolbar_center.pack_start (collection_artists_btn, false, false, 0);

        collection_albums_btn = new Gtk.ToggleButton.with_label (_("Albums"));
        collection_albums_btn.clicked.connect ((button) => {
        });
        toolbar_center.pack_start (collection_albums_btn, false, false, 0);

        collection_songs_btn = new Gtk.ToggleButton.with_label (_("Songs"));
        collection_songs_btn.clicked.connect ((button) => {
        });
        toolbar_center.pack_start (collection_songs_btn, false, false, 0);

        collection_playlists_btn = new Gtk.ToggleButton.with_label (_("Playlists"));
        collection_playlists_btn.clicked.connect ((button) => {
        });
        toolbar_center.pack_start (collection_playlists_btn, false, false, 0);

        var toolbar_end = new Gtk.Box (Orientation.HORIZONTAL, 0);

        collection_select_btn = new Gtk.Button ();
        collection_select_btn.set_image (new Gtk.Image.from_icon_name ("emblem-default-symbolic", IconSize.BUTTON));
        collection_select_btn.clicked.connect (() => {
            App.app.selection_mode = true;
        });
        App.app.notify["selection-mode"].connect (() => {
            notebook.page = App.app.selection_mode ?
                TopbarPage.SELECTION : notebook.page = TopbarPage.COLLECTION;
        });

        update_collection_select_btn_sensitivity ();
        toolbar_end.pack_start (collection_select_btn, false, false, 0);

        alignment = new Gtk.Alignment (1, (float)0.5, 0, 0);
        alignment.add (toolbar_end);
        hbox.pack_start (alignment);

        /* TopbarPage.SELECTION */
        var eventbox = new Gtk.EventBox ();
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
        selection_back_btn.clicked.connect ((button) => { App.app.ui_state = UIState.WIZARD; });
        toolbar_start.pack_start (selection_back_btn, false, false, 0);

        selection_remove_btn = new Gtk.Button.from_stock ("gtk-remove");
        selection_remove_btn.clicked.connect ((button) => { App.app.ui_state = UIState.WIZARD; });
        toolbar_start.pack_start (selection_remove_btn, false, false, 0);

        toolbar_center = new Gtk.Box (Orientation.HORIZONTAL, 0);
        hbox.pack_start (toolbar_center, false, false, 0);

        selection_name_label = new Gtk.Label (_("Collection name"));
        selection_count_label = new Gtk.Label ("");
        toolbar_center.pack_start (selection_name_label, false, false, 0);
        toolbar_center.pack_start (selection_count_label, false, false, 0);

        toolbar_end = new Gtk.Box (Orientation.HORIZONTAL, 5);

        selection_cancel_btn = new Gtk.Button.with_label (_("Cancel"));
        selection_cancel_btn.clicked.connect ((button) => { App.app.ui_state = UIState.WIZARD; });
        toolbar_end.pack_start (selection_cancel_btn, false, false, 0);

        selection_add_btn = new Gtk.Button.from_stock ("gtk-add");
        selection_add_btn.clicked.connect ((button) => { App.app.ui_state = UIState.WIZARD; });
        toolbar_end.pack_start (selection_add_btn, false, false, 0);

        alignment = new Gtk.Alignment (1, (float)0.5, 0, 0);
        alignment.add (toolbar_end);
        hbox.pack_start (alignment);


        /* TopbarPage.PLAYLIST */
        hbox = new Gtk.Box (Orientation.HORIZONTAL, 0);
        alignment = new Gtk.Alignment (0, 0, 1, 1);
        alignment.set_padding (5, 5, 5, 5);
        alignment.add (hbox);
        notebook.append_page (alignment, null);

        toolbar_start = new Gtk.Box (Orientation.HORIZONTAL, 5);
        hbox.pack_start (toolbar_start);

        playlist_back_btn = new Gtk.Button ();
        playlist_back_btn.set_image (new Gtk.Image.from_icon_name ("go-previous-symbolic", IconSize.BUTTON));
        playlist_back_btn.clicked.connect ((button) => { App.app.ui_state = UIState.WIZARD; });
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
        notebook.set_current_page (1);
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

    public override void ui_state_changed () {
        /*
        switch (ui_state) {
        case UIState.COLLECTION:
            notebook.page = TopbarPage.COLLECTION;
            selection_back_btn.hide ();
            spinner_btn.hide ();
            collection_select_btn.show ();
            new_btn.show ();
            break;

        case UIState.CREDS:
            new_btn.hide ();
            selection_back_btn.show ();
            spinner_btn.show ();
            collection_select_btn.hide ();
            break;

        case UIState.DISPLAY:
            break;

        case UIState.PROPERTIES:
            notebook.page = TopbarPage.PROPERTIES;
            break;

        case UIState.WIZARD:
            notebook.page = TopbarPage.WIZARD;
            break;

        default:
            break;
        }
        */
    }
}
