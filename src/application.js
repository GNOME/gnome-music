/*
 * Copyright (c) 2013 Eslam Mostafa <cseslam@gmail.com>.
 * Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>.
 * Copyright (c) 2013 Giovanni Campagna
 * Copyright (c) 2013 Sai Suman Prayaga
 * 
 * Gnome Music is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 *
 * The Gnome Music authors hereby grant permission for non-GPL compatible
 * GStreamer plugins to be used and distributed together with GStreamer and
 * Gnome Music. This permission is above and beyond the permissions granted by
 * the GPL license by which Gnome Music is covered. If you modify this code, you may 
 * extend this exception to your version of the code, but you are not obligated 
 * to do so. If you do not wish to do so, delete this exception statement from 
 * your version.
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

const MediaPlayer2Iface = <interface name="org.mpris.MediaPlayer2">
  <method name="Raise"/>
  <method name="Quit"/>
  <property name="CanQuit" type="b" access="read"/>
  <property name="CanRaise" type="b" access="read"/>
  <property name="HasTrackList" type="b" access="read"/>
  <property name="Identity" type="s" access="read"/>
  <property name="DesktopEntry" type="s" access="read"/>
  <property name="SupportedUriSchemes" type="as" access="read"/>
  <property name="SupportedMimeTypes" type="as" access="read"/>
</interface>;

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

        this._dbusImpl = Gio.DBusExportedObject.wrapJSObject(MediaPlayer2Iface, this);
        this._dbusImpl.export(Gio.DBus.session, '/org/mpris/MediaPlayer2');

        Gio.DBus.session.own_name('org.mpris.MediaPlayer2.gnome-music', Gio.BusNameOwnerFlags.REPLACE, null, null);
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

    /* MPRIS */

    Raise: function() {
        this._window.present();
    },

    Quit: function() {
        this.quit();
    },

    get CanQuit() {
        return true;
    },

    get CanRaise() {
        return true;
    },

    get HasTrackList() {
        return false;
    },

    get Identity() {
        return 'Music';
    },

    get DesktopEntry() {
        return 'gnome-music';
    },

    get SupportedUriSchemes() {
        return [
            'file'
        ];
    },

    get SupportedMimeTypes() {
        return [
            'application/ogg',
            'audio/x-vorbis+ogg',
            'audio/x-flac',
            'audio/mpeg'
        ];
    },
});
