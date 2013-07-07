/*
 * Copyright (c) 2013 Eslam Mostafa<cseslam@gmail.com>.
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
const Gd = imports.gi.Gd;
const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const Tracker = imports.gi.Tracker;

const Gettext = imports.gettext;
const _ = imports.gettext.gettext;

const Toolbar = imports.toolbar;
const Views = imports.view;
const Player = imports.player;
const Query = imports.query;
const tracker = Tracker.SparqlConnection.get (null)

const MainWindow = new Lang.Class({
    Name: "MainWindow",
    Extends: Gtk.ApplicationWindow,

    _init: function (app) {
        this.parent({
            application: app,
            title: _('Music'),
            window_position: Gtk.WindowPosition.CENTER,
        });
        this.connect('focus-in-event', Lang.bind(this, this._windowsFocusCb));

        let settings = new Gio.Settings({ schema: 'org.gnome.Music' });
        this.add_action(settings.create_action('repeat'));

        this.set_size_request(887, 640);
        this._setupView();

        this.proxy = Gio.DBusProxy.new_sync(Gio.bus_get_sync(Gio.BusType.SESSION, null),
                                            Gio.DBusProxyFlags.NONE,
                                            null,
                                            'org.gnome.SettingsDaemon',
                                            '/org/gnome/SettingsDaemon/MediaKeys',
                                            'org.gnome.SettingsDaemon.MediaKeys',
                                            null);
        this.proxy.call_sync('GrabMediaPlayerKeys',
                             GLib.Variant.new('(su)', 'Music'),
                             Gio.DBusCallFlags.NONE,
                             -1,
                             null);
        this.proxy.connect('g-signal', Lang.bind(this, this._handleMediaKeys));
    },

    _windowsFocusCb: function(window, event) {
        this.proxy.call_sync('GrabMediaPlayerKeys',
                             GLib.Variant.new('(su)', 'Music'),
                             Gio.DBusCallFlags.NONE,
                             -1,
                             null);
    },

    _handleMediaKeys: function(proxy, sender, signal, parameters) {
        if (signal != 'MediaPlayerKeyPressed') {
            log ('Received an unexpected signal \'%s\' from media player'.format(signal));
            return;
        }

        let key = parameters.get_child_value(1).get_string()[0];
        if (key == 'Play')
            this.player.PlayPause();
        else if (key == 'Stop')
            this.player.Stop();
        else if (key == 'Next')
            this.player.Next();
        else if (key == 'Previous')
            this.player.Previous();
    },

    _setupView: function () {
        this._box = new Gtk.Box({
            orientation: Gtk.Orientation.VERTICAL,
            spacing: 0
        });
        this.views = [];
        this.player = new Player.Player();

        this.toolbar = new Toolbar.Toolbar();
        this.set_titlebar(this.toolbar);
        this._stack = new Gtk.Stack({
            transition_type: Gtk.StackTransitionType.CROSSFADE,
            transition_duration: 100,
            visible: true
        });
        this.toolbar.set_stack(this._stack);

        this._box.pack_start(this._stack, true, true, 0);
        this._box.pack_start(this.player.eventBox, false, false, 0);
        this.add(this._box);
        let count = -1;
        let cursor = tracker.query(Query.songs_count, null)
        if(cursor!= null && cursor.next(null))
            count = cursor.get_integer(0);
        if(count > 0)
        {
        this.views[0] = new Views.Albums(this.toolbar, this.player);
        this.views[1] = new Views.Artists(this.toolbar, this.player);
        this.views[2] = new Views.Songs(this.toolbar, this.player);
        this.views[3] = new Views.Playlists(this.toolbar, this.player);

        for (let i in this.views) {
            this._stack.add_titled(
                this.views[i],
                this.views[i].title,
                this.views[i].title
            );
        }

        this._onNotifyModelId = this._stack.connect("notify::visible-child", Lang.bind(this, this._onNotifyMode));
        this.connect("destroy",Lang.bind(this, function(){
            this._stack.disconnect(this._onNotifyModelId);
        }));
  
        this.views[0].populate();
        }
        //To revert to the No Music View when no songs are found
        else{
            this.views[0] = new Views.Empty(this.toolbar, this.player);
            this._stack.add_titled(this.views[0],"Empty","Empty");
        }

        this.toolbar.show();
        this.player.eventBox.show_all();
        this._box.show();
        this.show();
    },

    _onNotifyMode: function(stack, param) {
        // Slide out artist list on switching to artists view
        if(stack.get_visible_child() == this.views[1]){
            stack.get_visible_child().stack.set_visible_child_name("dummy")
            stack.get_visible_child().stack.set_visible_child_name("artists")
        }
    },

    _toggleView: function(btn, i) {
        this._stack.set_visible_child(this.views[i])
    },
});
