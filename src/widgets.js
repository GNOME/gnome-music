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
            GObject.TYPE_BOOLEAN,
            GdkPixbuf.Pixbuf,
            GObject.TYPE_OBJECT,
            GObject.TYPE_BOOLEAN
        ]);
        this.ui = new Gtk.Builder();
        this.ui.add_from_resource('/org/gnome/music/AlbumWidget.ui');
        this.model = this.ui.get_object("AlbumWidget_model");

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

        this.parent();

        let hbox = this.ui.get_object("box3");
        let child_view = this.view.get_children()[0];
        this.view.remove(child_view)
        hbox.pack_start(child_view, true, true, 0)

        this.add(this.ui.get_object("AlbumWidget"));
        this._addListRenderers();
        this.get_style_context().add_class("view");
        this.get_style_context().add_class("content-view");
        this.show_all ();
    },

    _addListRenderers: function() {
        let listWidget = this.view.get_generic_view();

        var cols = listWidget.get_columns()
        var cells = cols[0].get_cells()
        cells[2].visible = false
        cells[1].visible = false

        let nowPlayingSymbolRenderer = new Gtk.CellRendererPixbuf({ xpad: 0 });
        let path = "/usr/share/icons/gnome/scalable/actions/media-playback-start-symbolic.svg";
        nowPlayingSymbolRenderer.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, -1, 16, true);

        var columnNowPlaying = new Gtk.TreeViewColumn();
        nowPlayingSymbolRenderer.set_property("xalign", 1.0);
        columnNowPlaying.pack_start(nowPlayingSymbolRenderer, false)
        columnNowPlaying.set_property('fixed-width', 24)
        columnNowPlaying.add_attribute(nowPlayingSymbolRenderer, "visible", 3);
        listWidget.insert_column(columnNowPlaying, 0)

        let typeRenderer =
            new Gd.StyledTextRenderer({ xpad: 16 });
        typeRenderer.set_property("ellipsize", 3);
        typeRenderer.set_property("xalign", 0.0);
        // This function is not neede, just add the renderer!
        listWidget.add_renderer(typeRenderer, Lang.bind(this,
            function(col, cell, model, iter) {}
        ));
        cols[0].clear_attributes(typeRenderer);
        cols[0].add_attribute(typeRenderer, "markup", 0);

        let durationRenderer =
            new Gd.StyledTextRenderer({ xpad: 16 });
        durationRenderer.add_class('dim-label');
        durationRenderer.set_property("ellipsize", 3);
        durationRenderer.set_property("xalign", 1.0);
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
        let released_date = item.get_publication_date();
        if (released_date != null) {
            this.ui.get_object("released_label_info").set_text(
                released_date.get_year().toString());
        } else {
            this.ui.get_object("released_label_info").set_text("----");
        }
        let duration = 0;
        this.model.clear()
        var tracks = [];
        grilo.getAlbumSongs(item.get_id(), Lang.bind(this, function (source, prefs, track) {
            if (track != null) {
                tracks.push(track);
                duration = duration + track.get_duration();
                let iter = this.model.append();
                let path = "/usr/share/icons/gnome/scalable/actions/media-playback-start-symbolic.svg";
                let pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, -1, 16, true);
                this.model.set(iter,
                    [0, 1, 2, 3, 4, 5],
                    [ track.get_title(), "", "", false, pixbuf, track ]);
                this.ui.get_object("running_length_label_info").set_text(
                    (parseInt(duration/60) + 1) + " min");
            }
        }));

        this.player.setPlaylist(tracks);
        this.player.setCurrentTrack(tracks[0]);

        if (pixbuf == null) {
            let path = "/usr/share/icons/gnome/scalable/places/folder-music-symbolic.svg";
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, -1, 256, true);
        }
        this.ui.get_object("cover").set_from_pixbuf (pixbuf);

        this.setArtistLabel(artist);
        this.setTitleLabel(album);
        this.setReleasedLabel(item.get_creation_date().get_year());

        this.player.connect('song-changed', Lang.bind(this,
            function(widget, id) {
                // Highlight currently played song as bold
                let iter = this.model.get_iter_from_string(id.toString())[1];
                let item = this.model.get_value(iter, 5);
                let title = "<b>" + item.get_title() + "</b>";
                this.model.set_value(iter, 0, title);
                // Display now playing icon
                this.model.set_value(iter, 3, true);

                // Make all previous songs shadowed
                for (let i = 0; i < id; i++){
                    let iter = this.model.get_iter_from_string(i.toString())[1];
                    let item = this.model.get_value(iter, 5);
                    let title = "<span color='grey'>" + item.get_title() + "</span>";
                    this.model.set_value(iter, 0, title);
                    this.model.set_value(iter, 3, false);
                }

                //Remove markup from the following songs
                let i = parseInt(id) + 1;
                while(this.model.get_iter_from_string(i.toString())[0]) {
                    let iter = this.model.get_iter_from_string(i.toString())[1];
                    let item = this.model.get_value(iter, 5);
                    this.model.set_value(iter, 0, item.get_title());
                    this.model.set_value(iter, 3, false);
                    i++;
                }
                return true;
            }
        ));
    },

    setArtistLabel: function(artist) {
        this.ui.get_object("artist_label").set_markup(
            "<b><span size='large' color='grey'>" + artist + "</span></b>");
    },

    setTitleLabel: function(title) {
        this.ui.get_object("title_label").set_markup(
            "<b><span size='large'>" + title + "</span></b>");
    },

    setReleasedLabel: function(year) {
        this.ui.get_object("released_label_info").set_markup(
            "<span>" + year + "</span>");
    },
});

const ArtistAlbums = new Lang.Class({
    Name: "ArtistAlbumsWidget",
    Extends: Gtk.VBox,

    _init: function (artist, albums, player) {
        this.player = player
        this.artist = artist
        this.albums = albums
        this.parent();
        this.ui = new Gtk.Builder();
        this.ui.add_from_resource('/org/gnome/music/ArtistAlbumsWidget.ui');
        this.set_border_width(0);
        this.ui.get_object("artist").set_label(this.artist); 
        var tracks = [];
        var widgets = [];

        this.pack_start(this.ui.get_object("ArtistAlbumsWidget"), false, false, 0);
        for (var i=0; i < albums.length; i++) {
            let widget = new ArtistAlbumWidget(artist, albums[i], this.player, tracks)
            this.pack_start(widget, false, false, 32);
            widgets.push(widget);
        }
        this.show_all();
        this.player.setPlaylist(tracks);
        this.player.setCurrentTrack(tracks[0]);

        this.player.connect('song-changed', Lang.bind(this,
            function(widget, id) {
                let origin = tracks[id].origin;
                let iter = tracks[id].iterator;
                origin.setPlayingSong(iter);

                //Remove markup from other albums
                for (let i in widgets) {
                    let albumwidget = widgets[i];
                    if (albumwidget != origin) {
                        albumwidget.setPlayingSong(-1);
                    }
                }
            }
        ));
    },
});

const ArtistAlbumWidget = new Lang.Class({
    Name: "ArtistAlbumWidget",
    Extends: Gtk.HBox,

    _init: function (artist, album, player, tracks) {
        this.parent();
        this.player = player;
        this.album = album;
        this.songs = [];

        this.ui = new Gtk.Builder();
        this.ui.add_from_resource('/org/gnome/music/ArtistAlbumWidget.ui');
        this.model = this.ui.get_object("liststore1");

        var pixbuf = albumArtCache.lookup (128, artist, album.get_title());
        if (pixbuf == null) {
            let path = "/usr/share/icons/gnome/scalable/places/folder-music-symbolic.svg";
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, -1, 128, true);
        }
        
        this.ui.get_object("cover").set_from_pixbuf(pixbuf);
        this.ui.get_object("title").set_label(album.get_title());
        if (album.get_creation_date()) {
            this.ui.get_object("year").set_markup(
                "<span color='grey'>(" + album.get_creation_date().get_year() + ")</span>");
        }

        grilo.getAlbumSongs(album.get_id(), Lang.bind(this, function (source, prefs, track) {
            if (track != null) {
                tracks.push(track);
                track.origin = this;
                //let path = "/usr/share/icons/gnome/scalable/actions/media-playback-start-symbolic.svg";
                //let pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, -1, 16, true);
                //this.model.set(iter,
                //    [0, 1, 2, 3, 4, 5],
                //    [ track.get_title(), track.get_track_number(), "", false, pixbuf, track ]);
                var ui = new Gtk.Builder();
                ui.add_from_resource('/org/gnome/music/TrackWidget.ui');
                var songWidget = ui.get_object("box1");
                this.songs.push(songWidget);
                ui.get_object("num").set_text(this.songs.length.toString());
                if (track.get_title() != null)
                    ui.get_object("title").set_text(track.get_title());
                //var songWidget = ui.get_object("duration").set_text(track.get_title());
                ui.get_object("title").set_alignment(0.0, 0.5);
                if (this.songs.length == 1) {
                    this.ui.get_object("grid1").add(songWidget);
                }
                else {
                    var i = this.songs.length - 1;
                    this.ui.get_object("grid1").attach(songWidget, i%2, parseInt(i/2), 1, 1)
                }
                this.ui.get_object("grid1").show_all();
                //ui.get_object("image1").hide();
            }
        }));

        this.pack_start(this.ui.get_object("ArtistAlbumWidget"), true, true, 0);
        this.show_all();

        /*this.ui.get_object("iconview1").connect('item-activated', Lang.bind(
            this, function(widget, path) {
                var iter = this.model.get_iter (path)[1];
                var item = this.model.get_value (iter, 5);
                this.setPlayingSong(item.iterator);
        }));
        */
    },

    setPlayingSong: function(iter) {
        /*
        if (iter == -1) {
            // Remove markup completely
            let new_iter = this.model.get_iter_first()[1];
            let item = this.model.get_value(new_iter, 5);
            this.model.set_value(new_iter, 0, item.get_title());
            this.model.set_value(new_iter, 3, false);
            while(this.model.iter_next(new_iter)){
                let item = this.model.get_value(new_iter, 5);
                this.model.set_value(new_iter, 0, item.get_title());
                this.model.set_value(new_iter, 3, false);
            }
        } else {
            // Highlight currently played song as bold
            if (!iter)
                return
            let item = this.model.get_value(iter, 5);
            let title = "<b>" + item.get_title() + "</b>";
            this.model.set_value(iter, 0, title);
            // Display now playing icon
            this.model.set_value(iter, 3, true);

            // Make all previous songs shadowed
            let prev_iter = iter;
            while(this.model.iter_previous(prev_iter)){
                let item = this.model.get_value(prev_iter, 5);
                let title = "<span color='grey'>" + item.get_title() + "</span>";
                this.model.set_value(prev_iter, 0, title);
                this.model.set_value(prev_iter, 3, false);
            }

            //Remove markup from the following songs
            let next_iter = iter;
            while(this.model.iter_next(next_iter)){
                let item = this.model.get_value(next_iter, 5);
                this.model.set_value(next_iter, 0, item.get_title());
                this.model.set_value(next_iter, 3, false);
            }
        }
        */
    },
});
