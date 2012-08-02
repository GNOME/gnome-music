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

private class Music.Player: Music.UI {
    public Gtk.Widget actor { get { return eventbox; } }

    private const uint height = 50;

    private Gtk.EventBox eventbox;

    private Gtk.Button play_btn;
    private Gtk.Button prev_btn;
    private Gtk.Button next_btn;
    private Gtk.Button rate_btn;
    private Gtk.ToggleButton shuffle_btn;

    public Player () {
        setup_player ();
    }

    private void setup_player () {
        eventbox = new Gtk.EventBox ();
        eventbox.get_style_context ().add_class ("music-player");

        var box = new Gtk.Box (Orientation.HORIZONTAL, 0);
        var alignment = new Gtk.Alignment (0, 0, 1, 1);
        alignment.set_padding (15, 15, 15, 15);
        alignment.add (box);
        eventbox.add (alignment);

        var toolbar_start = new Gtk.Box (Orientation.HORIZONTAL, 0);
        toolbar_start.get_style_context ().add_class (Gtk.STYLE_CLASS_LINKED);
        box.pack_start (toolbar_start);

        prev_btn = new Gtk.Button ();
        prev_btn.set_image (new Gtk.Image.from_icon_name ("media-skip-backward-symbolic", IconSize.BUTTON));
        prev_btn.clicked.connect ((button) => { App.app.ui_state = UIState.WIZARD; });
        toolbar_start.pack_start (prev_btn, false, false, 0);

        play_btn = new Gtk.Button ();
        play_btn.set_image (new Gtk.Image.from_icon_name ("media-playback-start-symbolic", IconSize.BUTTON));
        play_btn.clicked.connect ((button) => { App.app.ui_state = UIState.WIZARD; });
        toolbar_start.pack_start (play_btn, false, false, 0);

        next_btn = new Gtk.Button ();
        next_btn.set_image (new Gtk.Image.from_icon_name ("media-skip-forward-symbolic", IconSize.BUTTON));
        next_btn.clicked.connect ((button) => { App.app.ui_state = UIState.WIZARD; });
        toolbar_start.pack_start (next_btn, false, false, 0);

        var toolbar_center = new Gtk.Box (Orientation.HORIZONTAL, 0);
        toolbar_center.get_style_context ().add_class (Gtk.STYLE_CLASS_LINKED);
        box.pack_start (toolbar_center, false, false, 0);

        var toolbar_end = new Gtk.Box (Orientation.HORIZONTAL, 5);

        rate_btn = new Gtk.Button ();
        rate_btn.set_image (new Gtk.Image.from_icon_name ("bookmark-new-symbolic", IconSize.BUTTON));
        rate_btn.clicked.connect ((button) => { App.app.ui_state = UIState.WIZARD; });
        toolbar_end.pack_start (rate_btn, false, false, 0);

        shuffle_btn = new Gtk.ToggleButton ();
        shuffle_btn.set_image (new Gtk.Image.from_icon_name ("media-playlist-shuffle-symbolic", IconSize.BUTTON));
        shuffle_btn.clicked.connect ((button) => { App.app.ui_state = UIState.WIZARD; });
        toolbar_end.pack_start (shuffle_btn, false, false, 0);

        alignment = new Gtk.Alignment (1, (float)0.5, 0, 0);
        alignment.add (toolbar_end);
        box.pack_start (alignment);

        alignment.show_all ();
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
