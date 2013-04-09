/*
 * Copyright (c) 2013 Eslam Mostafa <cseslam@gmail.com>.
 * Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>.
 * Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>.
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
 */

const Gtk = imports.gi.Gtk;
const Gdk = imports.gi.Gdk;
const Gd = imports.gi.Gd;
const GdkPixbuf = imports.gi.GdkPixbuf;
const Gio = imports.gi.Gio;
const GObject = imports.gi.GObject;
const Lang = imports.lang;
const Grl = imports.gi.Grl;
const Query = imports.query;
const Grilo = imports.grilo;

const grilo = Grilo.grilo;
const AlbumArtCache = imports.albumArtCache;
const albumArtCache = AlbumArtCache.AlbumArtCache.getDefault();

const AlbumWidget = new Lang.Class({
    Name: "AlbumWidget",
    Extends: Gtk.EventBox,

    _init: function (player) {
        this.player = player;
        this.hbox = new Gtk.HBox ();
        this.scrolledWindow = new Gtk.ScrolledWindow();

        this.model = Gtk.ListStore.new([
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GdkPixbuf.Pixbuf,
            GObject.TYPE_OBJECT,
            GObject.TYPE_BOOLEAN
        ]);

        this.view = new Gd.MainView({
            shadow_type:    Gtk.ShadowType.NONE
        });
        this.view.set_view_type(Gd.MainViewType.LIST);
        this.view.set_model(this.model);
        this.view.connect('item-activated', Lang.bind(this,
            function(widget, id, path) {
                let iter = this.model.get_iter (path)[1];
                let item = this.model.get_value(iter, 5);
                this.player.setCurrentTrack(item);
                this.player.play();
            })
        );

        this.cover = new Gtk.Image();
        this.vbox = new Gtk.VBox();
        this.title_label = new Gtk.Label({label : ""});
        this.artist_label = new Gtk.Label({label : ""});
        this.running_length = 0;
        this.released_label = new Gtk.Label()
        this.released_label.set_markup ("<span color='grey'>Released</span>");
        this.running_length_label = new Gtk.Label({});
        this.running_length_label.set_markup ("<span color='grey'>Running Length</span>");
        this.released_label_info = new Gtk.Label({label: "----"});
        this.running_length_label_info = new Gtk.Label({label: "--:--"});
        this.released_label.set_alignment(1.0, 0.5)
        this.running_length_label.set_alignment(1.0, 0.5)
        this.released_label_info.set_alignment(0.0, 0.5)
        this.running_length_label_info.set_alignment(0.0, 0.5)

        this.parent();
        this.hbox.set_homogeneous(true);
        this.vbox.set_homogeneous(false);
        this.scrolledWindow.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC);

        var vbox = new Gtk.VBox()
        var hbox = new Gtk.Box()
        hbox.homogeneous = true
        var child_view = this.view.get_children()[0];
        this.view.remove(child_view)
        hbox.pack_start(child_view, true, true, 0)
        hbox.pack_start(new Gtk.Label(), true, true, 0)

        vbox.pack_start(new Gtk.Label(), false, false, 24)
        vbox.pack_start(hbox, true, true, 0)
        this.scrolledWindow.add(vbox);

        this.infobox = new Gtk.Box()
        this.infobox.homogeneous = true;
        this.infobox.spacing = 36
        var box = new Gtk.VBox();
        box.pack_start (this.released_label, false, false, 0)
        box.pack_start (this.running_length_label, false, false, 0)
        this.infobox.pack_start(box, true, true, 0)
        box = new Gtk.VBox();
        box.pack_start (this.released_label_info, false, false, 0)
        box.pack_start (this.running_length_label_info, false, false, 0)
        this.infobox.pack_start(box, true, true, 0)

        this.vbox.pack_start (new Gtk.Label({label:""}), false, false, 24);
        this.vbox.pack_start (this.cover, false, false, 0);

        let artistBox = new Gtk.VBox();
        artistBox.set_spacing(6);
        artistBox.pack_start (this.title_label, false, false, 0);
        artistBox.pack_start (this.artist_label, false, false, 0);

        this.vbox.pack_start (artistBox, false, false, 24);
        this.vbox.pack_start(this.infobox, false, false, 0);

        let hbox = new Gtk.Box();
        hbox.pack_start(new Gtk.Label(), true, true, 0);
        hbox.pack_end(this.vbox, false, false, 0);
        this.hbox.pack_start (hbox, true, true, 32);
        this.hbox.pack_start (this.scrolledWindow, true, true, 0);

        this.get_style_context ().add_class ("view");
        this.get_style_context ().add_class ("content-view");
        this.add(this.hbox);
        this._addListRenderers();
        this.show_all ();
    },

    _addListRenderers: function() {
        let listWidget = this.view.get_generic_view();

        var cols = listWidget.get_columns()
        var cells = cols[0].get_cells()
        cells[2].visible = false

        let typeRenderer =
            new Gd.StyledTextRenderer({ xpad: 0 });
        typeRenderer.set_property("ellipsize", 3);
        typeRenderer.set_property("xalign", 0.0);
        typeRenderer.set_property("expand", true);
        listWidget.add_renderer(typeRenderer, Lang.bind(this,
            function(col, cell, model, iter) {
                let item = model.get_value(iter, 5);
                typeRenderer.text = item.get_title();
            }));

        let durationRenderer =
            new Gd.StyledTextRenderer({ xpad: 16 });
        durationRenderer.add_class('dim-label');
        durationRenderer.set_property("ellipsize", 3);
        durationRenderer.set_property("xalign", 1.0);
        durationRenderer.set_property("expand", true);
        listWidget.add_renderer(durationRenderer, Lang.bind(this,
            function(col, cell, model, iter) {
                let item = model.get_value(iter, 5);
                let duration = item.get_duration ();
                var minutes = parseInt(duration / 60);
                var seconds = duration % 60;
                var time = null
                if (seconds < 10)
                    time =  minutes + ":0" + seconds;
                else
                    time = minutes + ":" + seconds;
                durationRenderer.text = time;
            }));

    },

    update: function (artist, album, item) {
        var pixbuf = albumArtCache.lookup (256, artist, item.get_string(Grl.METADATA_KEY_ALBUM));
        let duration = 0;
        this.model.clear()
        var tracks = [];
        grilo.getAlbumSongs(item.get_id(), Lang.bind(this, function (source, prefs, track) {
            if (track != null) {
                tracks.push(track);
                duration = duration + track.get_duration();
                let iter = this.model.append();
                this.model.set(iter,
                    [0, 1, 2, 3, 4, 5],
                    [ "", "", "", "", null, track]);
                this.running_length_label_info.set_text((parseInt(duration/60) + 1) + " min");
            }
        }));

        this.player.setPlaylist(tracks);
        this.player.setCurrentTrack(tracks[0]);

        if (pixbuf == null) {
            let path = "/usr/share/icons/gnome/scalable/places/folder-music-symbolic.svg";
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, -1, 256, true);
        }
        this.cover.set_from_pixbuf (pixbuf);

        this.setArtistLabel(artist);
        this.setTitleLabel(album);
    },

    setArtistLabel: function(artist) {
        this.artist_label.set_markup("<b><span size='large' color='grey'>" + artist + "</span></b>");
    },

    setTitleLabel: function(title) {
        this.title_label.set_markup("<b><span size='large'>" + title + "</span></b>");
    },

});
