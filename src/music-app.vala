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
using Gdk;

private enum Music.AppState {
    ARTISTS = 0,
    ALBUMS,
    SONGS,
    PLAYLISTS,
    PLAYLIST,
    PLAYLIST_NEW
}

private enum Music.AppPage {
    COLLECTIONS = 0,
    PLAYLIST 
}

private class Music.App {
    public static App app;
    public Gtk.ApplicationWindow window;
    private bool maximized { get { return WindowState.MAXIMIZED in window.get_window ().get_state (); } }
    public GLib.Settings settings;

    public Gtk.Box layout;
    public Music.Topbar topbar;
    public Music.Player player;
    public Music.CollectionView collectionView;
    public Music.PlaylistView playlistView;
    public Gtk.Notebook notebook;

    private Gtk.Application application;

    public Music.BrowseHistory browse_history;

    private uint configure_id;
    public static const uint configure_id_timeout = 100;  // 100ms

    public signal void browse_back (string item_id, Music.ItemType? item_type); 

    public signal void app_state_changed (Music.AppState old_state, Music.AppState new_state);
    private Music.AppState _app_state; 
    public Music.AppState app_state {
        get {
            return _app_state;
        }
        set {
            var old_app_state = _app_state;
            _app_state = value;
            app_state_changed (old_app_state, _app_state);
        }
    }

    public App () {
        app = this;
        application = new Gtk.Application ("org.gnome.Music", 0);
        settings = new GLib.Settings ("org.gnome.Music");

        setup_menu ();
        setup_ui (); 

        browse_history = new Music.BrowseHistory ();
        browse_history.changed.connect (on_browse_history_changed);

        application.startup.connect_after ((app) => {
            var menu = new GLib.Menu ();
            menu.append (_("New"), "app.new");
            menu.append (_("About Music"), "app.about");
            menu.append (_("Quit"), "app.quit");

            application.set_app_menu (menu);
        });

        application.activate.connect_after ((app) => {
            window.present ();
            this.app_state_changed.connect (on_app_state_changed);
            this.app_state = Music.AppState.ARTISTS;
        });
    }

    public int run () {
        return application.run ();
    }

    private void setup_menu () {
        var action = new GLib.SimpleAction ("quit", null);
        action.activate.connect (() => { quit (); });
        application.add_action (action);

        action = new GLib.SimpleAction ("about", null);
        action.activate.connect (() => {
            string[] authors = {
                "César García Tapia <tapia@openshine.com>"
            };
            string[] artists = {
            };

            Gtk.show_about_dialog (window,
                                   "artists", artists,
                                   "authors", authors,
                                   "translator-credits", _("translator-credits"),
                                   "comments", _("A GNOME 3 application to listen and manage music playlists"),
                                   "copyright", "Copyright 2012 OpenShine SL.",
                                   "license-type", Gtk.License.LGPL_2_1,
                                   "logo-icon-name", "gnome-music",
                                   "version", Config.PACKAGE_VERSION,
                                   "website", "http://www.gnome.org",
                                   "wrap-license", true);
        });
        application.add_action (action);
    }

    private void setup_ui () {
        window = new Gtk.ApplicationWindow (application);
        window.show_menubar = false;
        window.hide_titlebar_when_maximized = true;

        // restore window geometry/position
        var size = settings.get_value ("window-size");
        if (size.n_children () == 2) {
            var width = (int) size.get_child_value (0);
            var height = (int) size.get_child_value (1);

            window.set_default_size (width, height);
        }

        if (settings.get_boolean ("window-maximized"))
            window.maximize ();

        var position = settings.get_value ("window-position");
        if (position.n_children () == 2) {
            var x = (int) position.get_child_value (0);
            var y = (int) position.get_child_value (1);

            window.move (x, y);
        }

        window.configure_event.connect (() => {
            if (configure_id != 0)
                GLib.Source.remove (configure_id);
            configure_id = Timeout.add (configure_id_timeout, () => {
                configure_id = 0;
                save_window_geometry ();

                return false;
            });

            return false;
        });
        window.window_state_event.connect (() => {
            settings.set_boolean ("window-maximized", maximized);
            return false;
        });

        layout = new Gtk.Box (Orientation.VERTICAL, 0);

        topbar = new Music.Topbar ();
        topbar.collection_back_btn_clicked.connect (on_collection_back_btn_clicked);
        layout.pack_start (topbar.actor, false, false);

        notebook = new Gtk.Notebook ();
        notebook.show_border = false;
        notebook.show_tabs = false;
        notebook.show ();
        layout.pack_start (notebook);

        collectionView = new Music.CollectionView ();
        collectionView.item_selected.connect (on_collectionview_selected_item);
        notebook.append_page (collectionView.actor, null);

        playlistView = new Music.PlaylistView ();
        notebook.append_page (playlistView.actor, null);

        player = new Music.Player ();
        layout.pack_start (player.actor, false, false);

        layout.show ();
        window.add (layout);
    }

    private void on_app_state_changed (Music.AppState old_state, Music.AppState new_state) {
    }

    private void on_collectionview_selected_item (string item_id, Music.ItemType? item_type, Grl.Media? media) {
        browse_history.push (item_id, item_type);

        if (item_type != null && item_type == Music.ItemType.ALBUM) {
            playlistView.load (media);
            notebook.set_current_page (AppPage.PLAYLIST);
        }
    }

    private void on_browse_history_changed () {
        if (browse_history.get_length () > 1) {
            topbar.set_collection_back_button_visible (true);
        }
        else {
            topbar.set_collection_back_button_visible (false);
        }
    }

    private void on_collection_back_btn_clicked () {
        var last_item_id = browse_history.get_last_item_id ();
        Music.ItemType? last_item_type = browse_history.get_last_item_type ();
        browse_history.delete_last_item ();

        browse_back (last_item_id, last_item_type);
    }

    private bool _selection_mode;
    public bool selection_mode {
        get {
            return _selection_mode;
        }
        set {
            _selection_mode = value;
        }
    }

    private void save_window_geometry () {
        int width, height, x, y;

        if (maximized)
            return;

        window.get_size (out width, out height);
        settings.set_value ("window-size", new int[] { width, height });

        window.get_position (out x, out y);
        settings.set_value ("window-position", new int[] { x, y });
    }



    public bool quit () {
        save_window_geometry ();
        window.destroy ();

        return false;
    }
}
