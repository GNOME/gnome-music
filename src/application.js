/*
 * Copyright (c) 2013 Eslam Mostafa.
 * Copyright (c) 2013 Vadim Rutkovsky.
 *
 * Gnome Music is free software; you can Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 *
 * Gnome Music is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with Gnome Music; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
 *
 * Author: Eslam Mostafa <cseslam@gmail.com>
 *
 */

const Lang = imports.lang;
const Gtk = imports.gi.Gtk;
const Gdk = imports.gi.Gdk;
const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const Gd = imports.gi.Gd;

const Window = imports.window;

const Gettext = imports.gettext;
const _ = imports.gettext.gettext;

var AppState = {
    ARTISTS: 0,
    ALBUMS: 1,
    SONGS: 2,
    PLAYLISTS: 3,
    PLAYLIST: 4,
    PLAYLIST_NEW: 5
};

const Application = new Lang.Class({
    Name: 'Music',
    Extends: Gtk.Application,

    _init: function() {
        this.parent({
            application_id: 'org.gnome.Music',
            flags: Gio.ApplicationFlags.FLAGS_NONE,
            inactivity_timeout: 12000
        });

        GLib.set_application_name(_("Music"));
    },

    _buildAppMenu: function() {
        var builder,
            menu;

        builder = new Gtk.Builder();
        builder.add_from_resource('/org/gnome/music/app-menu.ui');

        menu = builder.get_object('app-menu');
        this.set_app_menu(menu);

        let newPlaylistAction = new Gio.SimpleAction ({ name: 'newPlaylist' });
        newPlaylistAction.connect('activate', Lang.bind(this,
            function() {
                log("newPlaylist action");
            }));
         this.add_action(newPlaylistAction);

        let nowPlayingAction = new Gio.SimpleAction ({ name: 'nowPlaying' });
        nowPlayingAction.connect('activate', Lang.bind(this,
            function() {
                log("nowPlaying action");
            }));
         this.add_action(nowPlayingAction);

        let aboutAction = new Gio.SimpleAction ({ name: 'about' });
        aboutAction.connect('activate', Lang.bind(this,
            function() {
                log("about action");
            }));
         this.add_action(aboutAction);

        let quitAction = new Gio.SimpleAction ({ name: 'quit' });
        quitAction.connect('activate', Lang.bind(this,
            function() {
                this.quit();
            }));
         this.add_action(quitAction);
    },

    vfunc_startup: function() {
        this.parent();

        let resource = Gio.Resource.load(pkg.pkgdatadir + '/gnome-music.gresource');
        resource._register();

        let cssFile = Gio.File.new_for_uri('resource:///org/gnome/music/application.css');
        let provider = new Gtk.CssProvider();
        provider.load_from_file(cssFile);
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),
                                                 provider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION);
    },

    vfunc_activate: function() {
        this._buildAppMenu();
        this._window = new Window.MainWindow(this);
        this._window.present();
        this._window.connect("destroy",Lang.bind(this,
        function () {
            this.quit();
        }));
    },
});
