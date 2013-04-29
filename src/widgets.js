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

const folderPixbuf_small = GdkPixbuf.Pixbuf.new_from_file_at_scale(
        "/usr/share/icons/gnome/scalable/places/folder-music-symbolic.svg",
        -1, 128, true);
const folderPixbuf_big = GdkPixbuf.Pixbuf.new_from_file_at_scale(
        "/usr/share/icons/gnome/scalable/places/folder-music-symbolic.svg",
        -1, 128, true);
const nowPlayingPixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
        "/usr/share/icons/gnome/scalable/actions/media-playback-start-symbolic.svg",
        -1, 16, true);

const AlbumWidget = new Lang.Class({
    Name: "AlbumWidget",
    Extends: Gtk.EventBox,

    _init: function (player) {
        this.player = player;
        this.hbox = new Gtk.HBox ();
        this.iterToClean = null;
        this.scrolledWindow = new Gtk.ScrolledWindow();

        this.ui = new Gtk.Builder();
        this.ui.add_from_resource('/org/gnome/music/AlbumWidget.ui');
        this.model = this.ui.get_object("AlbumWidget_model");

        this.view = new Gd.MainView({
            shadow_type:    Gtk.ShadowType.NONE
        });
        this.view.set_view_type(Gd.MainViewType.LIST);
        this.album=null;
        this.view.connect('item-activated', Lang.bind(this,
            function(widget, id, path) {
                if (this.iterToClean && this.player.playlist_id == this.album){
                    let item = this.model.get_value(this.iterToClean, 5);
                    this.model.set_value(this.iterToClean, 0, item.get_title());
                    // Hide now playing icon
                    this.model.set_value(this.iterToClean, 3, false);
                }
                this.player.setPlaylist("Album", this.album, this.model, this.model.get_iter(path)[1], 5);
                this.player.play();
            })
        );

        this.parent();

        let view_box = this.ui.get_object("view");
        let child_view = this.view.get_children()[0];
        this.view.remove(child_view)
        view_box.add(child_view)

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
        nowPlayingSymbolRenderer.pixbuf = nowPlayingPixbuf;

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
        // This function is not needed, just add the renderer!
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
                if (!item)
                    return;
                durationRenderer.text = this.player.seconds_to_string(duration);
            }));
    },
    update: function (artist, album, item) {
        let released_date = item.get_publication_date();
        if (released_date != null) {
            this.ui.get_object("released_label_info").set_text(
                released_date.get_year().toString());
        }
        let duration = 0;
        this.album = album;
        // if the active queue has been set by this album,
        // use it as model, otherwise build the liststore
        let cachedPlaylist = this.player.runningPlaylist("Album", album);
        if (cachedPlaylist){
            this.model = cachedPlaylist;
            this.updateModel(this.player, cachedPlaylist, this.player.currentTrack);
        } else {
            this.model = Gtk.ListStore.new([
                GObject.TYPE_STRING, /*title*/
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
                GObject.TYPE_BOOLEAN,/*icon shown*/
                GdkPixbuf.Pixbuf,    /*icon*/
                GObject.TYPE_OBJECT, /*song object*/
                GObject.TYPE_BOOLEAN
            ]);
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
                    [ track.get_title(), "", "", false, nowPlayingPixbuf, track ]);
                this.ui.get_object("running_length_label_info").set_text(
                    (parseInt(duration/60) + 1) + " min");
            }
        }));
    }
    this.view.set_model(this.model);
        let pixbuf = albumArtCache.lookup (256, artist, item.get_string(Grl.METADATA_KEY_ALBUM));
        if (pixbuf == null)
            pixbuf = folderPixbuf_big;
        this.ui.get_object("cover").set_from_pixbuf (pixbuf);

        this.ui.get_object("artist_label").set_markup(artist);
        this.ui.get_object("title_label").set_markup(album);
        if (item.get_creation_date())
            this.ui.get_object("released_label_info").set_text(item.get_creation_date().get_year().toString());
        else
            this.ui.get_object("released_label_info").set_text("----");
        this.player.connect('playlist-item-changed', Lang.bind(this, this.updateModel));
    },

    updateModel: function(player, playlist, iter){
        //this is not our playlist, return
        if (playlist != this.model){
            return true;}
        if (this.iterToClean){
            let next_iter = iter.copy();
            do {
                let item = playlist.get_value(next_iter, 5);
                playlist.set_value(next_iter, 0, item.get_title());
                // Hide now playing icon
                playlist.set_value(next_iter, 3, false);
            } while (!playlist.iter_next(next_iter))
        }
        this.iterToClean = iter.copy();

        // Highlight currently played song as bold
        let item = playlist.get_value(iter, 5);
        playlist.set_value(iter, 0, "<b>" + item.get_title() + "</b>");
        // Display now playing icon
        playlist.set_value(iter, 3, true);

        // grey out previous items
        let prev_iter = iter.copy();
        while(playlist.iter_previous(prev_iter)){
            let item = playlist.get_value(prev_iter, 5);
            let title = "<span color='grey'>" + item.get_title() + "</span>";
            playlist.set_value(prev_iter, 0, title);
            playlist.set_value(prev_iter, 3, false);
        }
        return true;
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
        var widgets = [];

        this.model = Gtk.ListStore.new([
                GObject.TYPE_STRING, /*title*/
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
                GObject.TYPE_BOOLEAN,/*icon shown*/
                GdkPixbuf.Pixbuf,    /*icon*/
                GObject.TYPE_OBJECT, /*song object*/
                GObject.TYPE_BOOLEAN
                ]);


        this.pack_start(this.ui.get_object("ArtistAlbumsWidget"), false, false, 0);
        for (var i=0; i < albums.length; i++) {
            let widget = new ArtistAlbumWidget(artist, albums[i], this.player, this.model)
            this.pack_start(widget, false, false, 32);
            widgets.push(widget);
        }
        this.show_all();
        this.player.connect('playlist-item-changed', Lang.bind(this, this.updateModel));
    },

    updateModel: function(player, playlist, currentIter){
        //this is not our playlist, return
        if (playlist != this.model){
            return true;}
        let currentSong = playlist.get_value(currentIter, 5);
        let [res, iter] = playlist.get_iter_first();
        if (!res)
            return true;
        let songPassed = false;
        let i = 0;
        do{
            i++;
            let song = playlist.get_value(iter, 5);
            let songWidget = song.songWidget;

            if (song == currentSong){
                songWidget.nowPlayingSign.show();
                songWidget.title.set_markup("<b>" + song.get_title() + "</b>");
                songPassed = true;
            } else if (songPassed) {
                songWidget.nowPlayingSign.hide();
                songWidget.title.set_markup("<span>"+song.get_title()+"</span>");
            } else {
                songWidget.nowPlayingSign.hide();
                songWidget.title.set_markup("<span color='grey'>" + song.get_title() + "</span>");
            }
        } while(playlist.iter_next(iter));
        return true;

    },
});

const ArtistAlbumWidget = new Lang.Class({
    Name: "ArtistAlbumWidget",
    Extends: Gtk.HBox,

    _init: function (artist, album, player, model) {
        this.parent();
        this.player = player;
        this.album = album;
        this.artist = artist;
        this.model = model;
        this.songs = [];

        var track_count = album.get_childcount();

        this.ui = new Gtk.Builder();
        this.ui.add_from_resource('/org/gnome/music/ArtistAlbumWidget.ui');

        var pixbuf = albumArtCache.lookup (128, artist, album.get_title());
        if (pixbuf == null)
            pixbuf = folderPixbuf_small;

        this.ui.get_object("cover").set_from_pixbuf(pixbuf);
        this.ui.get_object("title").set_label(album.get_title());
        if (album.get_creation_date()) {
            this.ui.get_object("year").set_markup(
                "<span color='grey'>(" + album.get_creation_date().get_year() + ")</span>");
        }
        this.tracks = [];
        grilo.getAlbumSongs(album.get_id(), Lang.bind(this, function (source, prefs, track) {
            if (track != null) {
                this.tracks.push(track);
            }
            else {
                for (var i=0; i<this.tracks.length; i++) {
                    let track = this.tracks[i];
                    var ui = new Gtk.Builder();
                    ui.add_from_resource('/org/gnome/music/TrackWidget.ui');
                    var songWidget = ui.get_object("eventbox1");
                    this.songs.push(songWidget);
                    ui.get_object("num").set_text(this.songs.length.toString());
                    if (track.get_title() != null)
                        ui.get_object("title").set_text(track.get_title());
                    //var songWidget = ui.get_object("duration").set_text(track.get_title());
                    ui.get_object("title").set_alignment(0.0, 0.5);
                    this.ui.get_object("grid1").attach(songWidget,
                        parseInt(i/(this.tracks.length/2)),
                        parseInt((i)%(this.tracks.length/2)), 1, 1);
                    track.songWidget = songWidget;
                    let iter = model.append();
                    model.set(iter,
                            [0, 1, 2, 3, 4, 5],
                            [ track.get_title(), "", "", false, folderPixbuf_small, track]);

                    songWidget.iter = iter;
                    songWidget.model = model;
                    songWidget.connect('button-release-event', Lang.bind(
                                                            this, this.trackSelected));
                    songWidget.title = ui.get_object("title");
                    songWidget.nowPlayingSign = ui.get_object("image1");
                    songWidget.nowPlayingSign.set_from_pixbuf(nowPlayingPixbuf);
                    songWidget.nowPlayingSign.set_no_show_all("true");
                }
                this.ui.get_object("grid1").show_all();
            }
        }));

        this.pack_start(this.ui.get_object("ArtistAlbumWidget"), true, true, 0);
        this.show_all();
    },
    trackSelected: function(widget, iter) {
        this.player.setPlaylist("Artist", this.album, widget.model, widget.iter, 5);
        this.player.stop();
        this.player.play();
    },

});
