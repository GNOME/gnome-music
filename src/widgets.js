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
const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const GObject = imports.gi.GObject;
const Lang = imports.lang;
const Grl = imports.gi.Grl;
const Query = imports.query;
const Grilo = imports.grilo;
const Signals = imports.signals;
const GdkPixbuf = imports.gi.GdkPixbuf;

const grilo = Grilo.grilo;
const AlbumArtCache = imports.albumArtCache;
const albumArtCache = AlbumArtCache.AlbumArtCache.getDefault();

const nowPlayingIconName = 'media-playback-start-symbolic';
const errorIconName = 'dialog-error-symbolic';

const AlbumWidget = new Lang.Class({
    Name: "AlbumWidget",
    Extends: Gtk.EventBox,

    _init: function (player) {
        this.player = player;
        this.hbox = new Gtk.HBox ();
        this.iterToClean = null;

        this.ui = new Gtk.Builder();
        this.ui.add_from_resource('/org/gnome/music/AlbumWidget.ui');
        this.model = Gtk.ListStore.new([
                GObject.TYPE_STRING, /*title*/
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
                GdkPixbuf.Pixbuf,    /*icon*/
                GObject.TYPE_OBJECT, /*song object*/
                GObject.TYPE_BOOLEAN,/*icon shown*/
                GObject.TYPE_STRING,
       ]);

        this.view = new Gd.MainView({
            shadow_type:    Gtk.ShadowType.NONE
        });
        this.view.set_view_type(Gd.MainViewType.LIST);
        this.album=null;
        this.view.connect('item-activated', Lang.bind(this,
            function(widget, id, path) {
                let iter = this.model.get_iter(path)[1];
                if (this.model.get_value(iter, 7) != errorIconName) {
                    this.player.stop();
                    if (this.iterToClean && this.player.playlistId == this.album){
                        let item = this.model.get_value(this.iterToClean, 5);
                        this.model.set_value(this.iterToClean, 0, item.get_title());
                        // Hide now playing icon
                        this.model.set_value(this.iterToClean, 6, false);
                    }
                    this.player.setPlaylist("Album", this.album, this.model, iter, 5);
                    this.player.setPlaying(true);
                }
            })
        );

        this.parent();

        let view_box = this.ui.get_object("view");
        let child_view = this.view.get_children()[0];
        child_view.set_margin_top(64);
        child_view.set_margin_bottom(64);
        child_view.set_margin_right(32);
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
        cols[0].set_min_width(310)
        cols[0].set_max_width(470)
        var cells = cols[0].get_cells()
        cells[2].visible = false
        cells[1].visible = false

        let nowPlayingSymbolRenderer = new Gtk.CellRendererPixbuf({ xpad: 0 });

        var columnNowPlaying = new Gtk.TreeViewColumn();
        nowPlayingSymbolRenderer.set_property("xalign", 1.0);
        nowPlayingSymbolRenderer.set_property("yalign", 0.6);
        columnNowPlaying.pack_start(nowPlayingSymbolRenderer, false);
        columnNowPlaying.set_property('fixed-width', 24);
        columnNowPlaying.add_attribute(nowPlayingSymbolRenderer, "visible", 6);
        columnNowPlaying.add_attribute(nowPlayingSymbolRenderer, "icon_name", 7);
        listWidget.insert_column(columnNowPlaying, 0);

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

        let durationRenderer = new Gd.StyledTextRenderer({ xpad: 16 });
        durationRenderer.add_class('dim-label');
        durationRenderer.set_property("ellipsize", 3);
        durationRenderer.set_property("xalign", 1.0);
        listWidget.add_renderer(durationRenderer, Lang.bind(this,
            function(col, cell, model, iter) {
                let item = model.get_value(iter, 5);
                let duration = item.get_duration ();
                if (!item)
                    return;
                durationRenderer.text = this.player.secondsToString(duration);
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
        let pixbuf = albumArtCache.lookup (256, artist, item.get_string(Grl.METADATA_KEY_ALBUM));
        if (pixbuf == null)
            pixbuf = albumArtCache.makeDefaultIcon(256, 256);
        this.ui.get_object("cover").set_from_pixbuf (pixbuf);

        // if the active queue has been set by this album,
        // use it as model, otherwise build the liststore
        let cachedPlaylist = this.player.runningPlaylist("Album", album);
        if (cachedPlaylist){
            this.model = cachedPlaylist;
            this.updateModel(this.player, cachedPlaylist, this.player.currentTrack);
        } else {
            this.model.clear();
            var tracks = [];
            grilo.getAlbumSongs(item.get_id(), Lang.bind(this, function (source, prefs, track) {
                if (track != null) {
                    tracks.push(track);
                    duration = duration + track.get_duration();
                    let iter = this.model.append();
                    let escapedTitle = GLib.markup_escape_text(track.get_title(), track.get_title().length);
                    try{
                        this.player.discoverer.discover_uri(track.get_url());
                        this.model.set(iter,
                            [0, 1, 2, 3, 4, 5, 6, 7],
                            [ escapedTitle, "", "", "", pixbuf, track, false, nowPlayingIconName ]);
                    } catch(err) {
                        log("failed to discover url " + track.get_url());
                        this.model.set(iter,
                            [0, 1, 2, 3, 4, 5, 6, 7],
                            [ escapedTitle, "", "", "", pixbuf, track, true, errorIconName ]);
                    }

                    this.ui.get_object("running_length_label_info").set_text(
                        (parseInt(duration/60) + 1) + " min");

                    this.emit("track-added")
                }
            }));
        }
        this.view.set_model(this.model);
        let escapedArtist = GLib.markup_escape_text(artist, -1);
        let escapedAlbum = GLib.markup_escape_text(album, -1);
        this.ui.get_object("artist_label").set_markup(escapedArtist);
        this.ui.get_object("title_label").set_markup(escapedAlbum);
        if (item.get_creation_date())
            this.ui.get_object("released_label_info").set_text(item.get_creation_date().get_year().toString());
        else
            this.ui.get_object("released_label_info").set_text("----");
        this.player.connect('playlist-item-changed', Lang.bind(this, this.updateModel));
        this.emit('loaded')

    },

    updateModel: function(player, playlist, currentIter){
        //this is not our playlist, return
        if (playlist != this.model){
            return false;}
        let currentSong = playlist.get_value(currentIter, 5);
        let [res, iter] = playlist.get_iter_first();
        if (!res)
            return false;
        let songPassed = false;
        let iconVisible, title;
        do{
            let song = playlist.get_value(iter, 5);

            let escapedTitle = GLib.markup_escape_text(song.get_title(), -1);
            if (song == currentSong){
                title = "<b>" + escapedTitle + "</b>";
                iconVisible = true;
                songPassed = true;
            } else if (songPassed) {
                title = "<span>"+escapedTitle+"</span>";
                iconVisible = false;
            } else {
                title = "<span color='grey'>" + escapedTitle + "</span>";
                iconVisible = false;
            }
            playlist.set_value(iter, 0, title);
            playlist.set_value(iter, 6, iconVisible);
        } while(playlist.iter_next(iter));
        return false;
    },
});
Signals.addSignalMethods(AlbumWidget.prototype);

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
        this.widgets = [];

        this.model = Gtk.ListStore.new([
                GObject.TYPE_STRING, /*title*/
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
                GObject.TYPE_BOOLEAN,/*icon shown*/
                GObject.TYPE_STRING, /*icon*/
                GObject.TYPE_OBJECT, /*song object*/
                GObject.TYPE_BOOLEAN
                ]);


        this.pack_start(this.ui.get_object("ArtistAlbumsWidget"), false, false, 0);
        var hbox = new Gtk.Box({orientation: Gtk.Orientation.VERTICAL});
        hbox.set_spacing(48);
        this.pack_start(hbox, false, false, 16);
        for (var i=0; i < albums.length; i++) {
            let widget = new ArtistAlbumWidget(artist, albums[i], this.player, this.model)
            hbox.pack_start(widget, false, false, 0);
            this.widgets.push(widget);
        }
        this.show_all();
        this.player.connect('playlist-item-changed', Lang.bind(this, this.updateModel));
        this.emit("albums-loaded");
    },

    updateModel: function(player, playlist, currentIter){
        //this is not our playlist, return
        if (playlist != this.model){
            //TODO, only clean once, but that can wait util we have clean
            //the code a bit, and until the playlist refactoring.
            //the overhead is acceptable for now
            this.cleanModel();
            return false;}
        let currentSong = playlist.get_value(currentIter, 5);
        let [res, iter] = playlist.get_iter_first();
        if (!res)
            return false;
        let songPassed = false;
        do{
            let song = playlist.get_value(iter, 5);
            let songWidget = song.songWidget;

            if (!songWidget.can_be_played)
                continue;

            let escapedTitle = GLib.markup_escape_text(song.get_title(), -1);
            if (song == currentSong){
                songWidget.nowPlayingSign.show();
                songWidget.title.set_markup("<b>" + escapedTitle + "</b>");
                songPassed = true;
            } else if (songPassed) {
                songWidget.nowPlayingSign.hide();
                songWidget.title.set_markup("<span>" + escapedTitle + "</span>");
            } else {
                songWidget.nowPlayingSign.hide();
                songWidget.title.set_markup("<span color='grey'>" + escapedTitle + "</span>");
            }
        } while(playlist.iter_next(iter));
        return false;

    },
    cleanModel: function(){
        let [res, iter] = this.model.get_iter_first();
        if (!res)
            return false;
        do{
            let song = this.model.get_value(iter, 5);
            let songWidget = song.songWidget;
            let escapedTitle = GLib.markup_escape_text(song.get_title(), -1);
            if (songWidget.can_be_played)
                songWidget.nowPlayingSign.hide();
            songWidget.title.set_markup("<span>" + escapedTitle + "</span>");
        } while(this.model.iter_next(iter));
        return false;

    }
});
Signals.addSignalMethods(ArtistAlbums.prototype);

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

        let pixbuf = albumArtCache.makeDefaultIcon(128, 128);
        GLib.idle_add(300, Lang.bind(this, this._updateAlbumArt));

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
                    ui.get_object("num").set_markup("<span color='grey'>"+this.songs.length.toString()+"</span>");
                    if (track.get_title() != null)
                        ui.get_object("title").set_text(track.get_title());
                    //var songWidget = ui.get_object("duration").set_text(track.get_title());
                    ui.get_object("title").set_alignment(0.0, 0.5);
                    this.ui.get_object("grid1").attach(songWidget,
                        parseInt(i/(this.tracks.length/2)),
                        parseInt((i)%(this.tracks.length/2)), 1, 1);
                    track.songWidget = songWidget;
                    let iter = model.append();
                    songWidget.iter = iter;
                    songWidget.model = model;
                    songWidget.title = ui.get_object("title");

                    try{
                        this.player.discoverer.discover_uri(track.get_url());
                        model.set(iter,
                            [0, 1, 2, 3, 4, 5],
                            [ track.get_title(), "", "", false, nowPlayingIconName, track]);
                        songWidget.nowPlayingSign = ui.get_object("image1");
                        songWidget.nowPlayingSign.set_from_icon_name(nowPlayingIconName, Gtk.IconSize.SMALL_TOOLBAR);
                        songWidget.nowPlayingSign.set_no_show_all("true");
                        songWidget.nowPlayingSign.set_alignment(0.0,0.6);
                        songWidget.can_be_played = true;
                        songWidget.connect('button-release-event', Lang.bind(
                                                                this, this.trackSelected));
                    } catch(err) {
                        log("failed to discover url " + track.get_url());
                        this.model.set(iter,
                            [0, 1, 2, 3, 4, 5],
                            [ track.get_title(), "", "", true, errorIconName, track ]);
                        songWidget.nowPlayingSign = ui.get_object("image1");
                        songWidget.nowPlayingSign.set_from_icon_name(errorIconName, Gtk.IconSize.SMALL_TOOLBAR);
                        songWidget.nowPlayingSign.set_alignment(0.0,0.6);
                        songWidget.can_be_played = false;
                    }
                }
                this.ui.get_object("grid1").show_all();
                this.emit("tracks-loaded");
            }
        }));

        this.pack_start(this.ui.get_object("ArtistAlbumWidget"), true, true, 0);
        this.show_all();
        this.emit("artist-album-loaded");
    },

    _updateAlbumArt: function() {
        let pixbuf = albumArtCache.lookup (128, this.artist, this.album.get_title());
        if (pixbuf != null)
            this.ui.get_object("cover").set_from_pixbuf(pixbuf);
        else {
            var options = Grl.OperationOptions.new(null);
            options.set_flags (Grl.ResolutionFlags.FULL | Grl.ResolutionFlags.IDLE_RELAY);
            grilo.tracker.resolve(
                this.album,
                [Grl.METADATA_KEY_THUMBNAIL],
                options,
                Lang.bind(this,
                function(source, param, item) {
                    var uri = this.album.get_thumbnail();
                    albumArtCache.getFromUri(uri,
                        this.artist,
                        this.album.get_title(),
                        128,
                        128,
                        Lang.bind(this,
                            function (pixbuf) {
                                pixbuf = albumArtCache.makeIconFrame(pixbuf);
                                this.ui.get_object("cover").set_from_pixbuf(pixbuf);
                            }))
                }));
        }
    },

    trackSelected: function(widget, iter) {
        this.player.stop();
        this.player.setPlaylist ("Artist", this.album, widget.model, widget.iter, 5);
        this.player.setPlaying(true);
    },

});
Signals.addSignalMethods(ArtistAlbumWidget.prototype);
