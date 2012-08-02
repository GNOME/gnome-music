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

private enum Music.AppPage {
    MAIN,
    PLAYLIST 
}

private class Music.App: Music.UI {
    public static App app;
    public Gtk.ApplicationWindow window;
    private bool maximized { get { return WindowState.MAXIMIZED in window.get_window ().get_state (); } }
    public GLib.Settings settings;

    public Gtk.Box layout;
    public Music.Topbar topbar;
    public Music.Player player;
    public Gtk.Notebook notebook;

    private Gtk.Application application;

    private uint configure_id;
    public static const uint configure_id_timeout = 100;  // 100ms

    public App () {
        app = this;
        application = new Gtk.Application ("org.gnome.Music", 0);
        settings = new GLib.Settings ("org.gnome.Music");

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

        application.startup.connect_after ((app) => {
            var menu = new GLib.Menu ();
            menu.append (_("New"), "app.new");
            menu.append (_("About Music"), "app.about");
            menu.append (_("Quit"), "app.quit");

            application.set_app_menu (menu);

            setup_ui ();
        });

        application.activate.connect_after ((app) => {
            window.present ();
        });
    }

    public int run () {
        return application.run ();
    }

    public bool open (string name) {
        ui_state = UIState.COLLECTION;
        return false;
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
        window.add (layout);

        topbar = new Music.Topbar ();
        layout.pack_start (topbar.actor, false, false);

        notebook = new Gtk.Notebook ();
        notebook.show_border = false;
        notebook.show_tabs = false;
        layout.pack_start (notebook);

        player = new Music.Player ();
        layout.pack_start (player.actor, false, false);

        layout.show_all ();

        ui_state = UIState.COLLECTION;
    }

    private void set_main_ui_state () {
        notebook.page = Music.AppPage.MAIN;
    }

    public override void ui_state_changed () {
    }

    private bool _selection_mode;
    public bool selection_mode { get { return _selection_mode; }
        set {
            return_if_fail (ui_state == UIState.COLLECTION);

            _selection_mode = value;
        }
    }

    public bool quit () {
        save_window_geometry ();
        window.destroy ();

        return false;
    }
}
