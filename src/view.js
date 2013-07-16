/*
 * Copyright (c) 2013 Next Tuesday GmbH.
 *               Authored by: Seif Lotfy
 * Copyright (c) 2013 Eslam Mostafa<cseslam@gmail.com>.
 * Copyright (c) 2013 Seif Lotfy<seif@lotfy.com>.
 * Copyright (c) 2013 Vadim Rutkovsky<vrutkovs@redhat.com>.
 * Copyright (c) 2013 Giovanni Campagna
 * Copyright (c) 2013 Sai Suman Prayaga
 * Copyright (c) 2013 Ignacio Casal Quinteiro
 * Copyright (c) 2013 Guillaume Quintard
 * Copyright (c) 2013 Fabiano Fidêncio
 * Copyright (c) 2013 Shivani Poddar
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
 */

const Lang = imports.lang;
const Gtk = imports.gi.Gtk;
const Gdk = imports.gi.Gdk;
const GdkPixbuf = imports.gi.GdkPixbuf;
const GObject = imports.gi.GObject;
const Gd = imports.gi.Gd;
const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const Grl = imports.gi.Grl;
const Pango = imports.gi.Pango;
const Tracker = imports.gi.Tracker;
const Signals = imports.signals;
const Application = imports.application;
const Query = imports.query;
const Widgets = imports.widgets;
const Toolbar = imports.toolbar;

const tracker = Tracker.SparqlConnection.get (null);
const AlbumArtCache = imports.albumArtCache;
const Grilo = imports.grilo;

const nowPlayingIconName = 'media-playback-start-symbolic';
const errorIconName = 'dialog-error-symbolic';
const starIconName = 'starred-symbolic';

const albumArtCache = AlbumArtCache.AlbumArtCache.getDefault();
const grilo = Grilo.grilo;

const ViewContainer = new Lang.Class({
    Name: "ViewContainer",
    Extends: Gtk.Stack,

    _init: function(title, header_bar, selection_toolbar, use_stack) {
        this.parent({transition_type: Gtk.StackTransitionType.CROSSFADE});
        this._grid = new Gtk.Grid({orientation: Gtk.Orientation.VERTICAL})
        this._iconWidth = -1
        this._iconHeight = 128
        this._offset = 0;
        this._adjustmentValueId = 0;
        this._adjustmentChangedId = 0;
        this._scrollbarVisibleId = 0;
        this._model = Gtk.ListStore.new([
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GdkPixbuf.Pixbuf,
            GObject.TYPE_OBJECT,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT,
            GObject.TYPE_STRING,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_BOOLEAN
        ]);
        this.view = new Gd.MainView({
            shadow_type:    Gtk.ShadowType.NONE
        });
        this.view.set_view_type(Gd.MainViewType.ICON);
        this.view.set_model(this._model);
        this.selection_toolbar = selection_toolbar;
        let _box = new Gtk.Box({orientation: Gtk.Orientation.VERTICAL});
        _box.pack_start(this.view, true, true, 0);
        if (use_stack){
            this.stack = new Gd.Stack({
                transition_type: Gd.StackTransitionType.SLIDE_RIGHT,
            })
            var dummy = new Gtk.Frame({visible: false});
            this.stack.add_named(dummy, "dummy");
            this.stack.add_named(_box, "artists");
            this.stack.set_visible_child_name("dummy");
            this._grid.add(this.stack);
        } else {
            this._grid.add(_box);
        }

        this._loadMore = new Widgets.LoadMoreButton(this._getRemainingItemCount);
        _box.pack_end(this._loadMore.widget, false, false, 0);
        this._loadMore.widget.connect("clicked", Lang.bind(this, this.populate))
        this.view.connect('item-activated',
                            Lang.bind(this, this._onItemActivated));
        this._cursor = null;
        this.header_bar = header_bar;
        this.header_bar._selectButton.connect('toggled',Lang.bind(this,function (button) {
            if (button.get_active()) {
                this.view.set_selection_mode(true);
                this.header_bar.setSelectionMode(true);
                this.selection_toolbar.eventbox.set_visible(true);
                this.selection_toolbar._add_to_playlist_button.sensitive = false;
            } else {
                this.view.set_selection_mode(false);
                this.header_bar.setSelectionMode(false);
                this.selection_toolbar.eventbox.set_visible(false);
            }
        }));
        header_bar._cancelButton.connect('clicked',Lang.bind(this,function(button){
            this.view.set_selection_mode(false);
            header_bar.setSelectionMode(false);
        }));
        this.title = title;
        this.add(this._grid)

        this.show_all();
        this._items = [];
        this._loadMore.widget.hide();
        this._connectView();
        this._symbolicIcon = albumArtCache.makeDefaultIcon(this._iconHeight, this._iconWidth);

        this._init = false;
        grilo.connect('ready', Lang.bind(this, function() {
            if (this.header_bar.get_stack().get_visible_child() == this && this._init == false)
                this._populate();
            this.header_bar.get_stack().connect('notify::visible-child',
                Lang.bind(this, function(widget, param) { 
                    if (this == widget.get_visible_child() && !this._init)
                        this._populate();
                }));
        }));
        this.header_bar.connect('state-changed', Lang.bind(this, this._onStateChanged))
        this.view.connect('view-selection-changed',Lang.bind(this,function(){
            let items = this.view.get_selection();
            this.selection_toolbar._add_to_playlist_button.sensitive = items.length > 0
        }));
    },

    _populate: function() {
        this._init = true;
        this.populate();
    },

    _onStateChanged: function() {
    },

    _connectView: function() {
        this._adjustmentValueId = this.view.vadjustment.connect(
            'value-changed',
            Lang.bind(this, this._onScrolledWinChange)
        );
        this._adjustmentChangedId = this.view.vadjustment.connect(
            'changed',
            Lang.bind(this, this._onScrolledWinChange)
        );
        this._scrollbarVisibleId = this.view.get_vscrollbar().connect(
            'notify::visible',
            Lang.bind(this, this._onScrolledWinChange)
        );
        this._onScrolledWinChange();
    },

    _onScrolledWinChange: function() {
        let vScrollbar = this.view.get_vscrollbar();
        let adjustment = this.view.vadjustment;
        let revealAreaHeight = 32;

        // if there's no vscrollbar, or if it's not visible, hide the button
        if (!vScrollbar ||
            !vScrollbar.get_visible()) {
            this._loadMore.setBlock(true);
            return;
        }

        let value = adjustment.value;
        let upper = adjustment.upper;
        let page_size = adjustment.page_size;

        let end = false;
        // special case this values which happen at construction
        if ((value == 0) && (upper == 1) && (page_size == 1))
            end = false;
        else
            end = !(value < (upper - page_size - revealAreaHeight));
        if (this._getRemainingItemCount() <= 0)
            end = false;
        this._loadMore.setBlock(!end);
    },

    populate: function() {
    },

    _addItem: function(source, param, item) {
        if (item != null) {
            this._offset += 1;
            var iter = this._model.append();
            var artist = "Unknown"
            if (item.get_author() != null)
                artist = item.get_author();
            if (item.get_string(Grl.METADATA_KEY_ARTIST) != null)
                artist = item.get_string(Grl.METADATA_KEY_ARTIST)
            try{
                if (item.get_url())
                    this.player.discoverer.discover_uri(item.get_url());
                this._model.set(
                        iter,
                        [0, 1, 2, 3, 4, 5, 7, 8, 9, 10],
                        [toString(item.get_id()), "", item.get_title(), artist, this._symbolicIcon, item, -1, nowPlayingIconName, false, false]
                    );
            } catch(err) {
                log(err.message);
                log("failed to discover url " + item.get_url());
                this._model.set(
                        iter,
                        [0, 1, 2, 3, 4, 5, 7, 8, 9, 10],
                        [toString(item.get_id()), "", item.get_title(), artist, this._symbolicIcon, item, -1, errorIconName, false, true]
                    );
            }
            GLib.idle_add(300, Lang.bind(this, this._updateAlbumArt, item, iter));
        }
    },

    _getRemainingItemCount: function () {
        let count = -1;
        if (this.countQuery != null) {
            let cursor = tracker.query(this.countQuery, null)
            if (cursor != null && cursor.next(null))
                count = cursor.get_integer(0);
        }
        return ( count - this._offset);
    },

    _updateAlbumArt: function(item, iter) {
        albumArtCache.lookupOrResolve(item, this._iconWidth, this._iconHeight, Lang.bind(this, function(icon) {
            if (icon)
                this._model.set_value(iter, 4, albumArtCache.makeIconFrame(icon));
            else
                this._model.set_value(iter, 4, null);
            this.emit("album-art-updated");
        }));

        return false;
    },

    _addListRenderers: function () {
    },

    _onItemActivated: function (widget, id, path) {
    }
});
Signals.addSignalMethods(ViewContainer.prototype);

//Class for the Empty View
const Empty = new Lang.Class({
    Name: "Empty",
    Extends: Gtk.Stack,

    _init: function(header_bar,player){
        this.parent({transition_type: Gtk.StackTransitionType.CROSSFADE});
        let builder = new Gtk.Builder();
        builder.add_from_resource('/org/gnome/music/NoMusic.ui');
        let widget = builder.get_object('container');
        print(widget);
        this.add(widget);
        this.show_all();
    }
});


const Albums = new Lang.Class({
    Name: "AlbumsView",
    Extends: ViewContainer,

    _init: function(header_bar, selection_toolbar, player){
        this.parent("Albums", header_bar,selection_toolbar);
        this.view.set_view_type(Gd.MainViewType.ICON);
        this.countQuery = Query.album_count;
        this._albumWidget = new Widgets.AlbumWidget (player);
        this.add(this._albumWidget)
        this.header_bar.setState (1);
    },

    _onStateChanged: function (widget) {
        if (this.header_bar.get_stack() != null &&
            this == this.header_bar.get_stack().get_visible_child())
            this.visible_child = this._grid;
    },

    _onItemActivated: function (widget, id, path) {
        let button = Gtk.get_current_event().get_button()[1];
        if (button != 1)
            return;

        let iter = this._model.get_iter (path)[1];
        let title = this._model.get_value (iter, 2);
        let artist = this._model.get_value (iter, 3);
        let item = this._model.get_value (iter, 5);
        this._albumWidget.update (artist, title, item, this.header_bar,this.selection_toolbar);
        this.header_bar.setState (0);
        this.header_bar.header_bar.title = title;
        this.header_bar.header_bar.sub_title = artist;
        this.visible_child = this._albumWidget;
    },

    populate: function() {
        if (grilo.tracker != null)
            grilo.populateAlbums (this._offset, Lang.bind(this, this._addItem, null));
    },

});

const Songs = new Lang.Class({
    Name: "SongsView",
    Extends: ViewContainer,

    _init: function(header_bar, selection_toolbar, player) {
        this.parent("Songs", header_bar, selection_toolbar);
        this.countQuery = Query.songs_count;
        this._items = {};
        this.isStarred = null;
        this.view.set_view_type(Gd.MainViewType.LIST);
        this.view.get_generic_view().get_style_context().add_class("songs-list")
        this._iconHeight = 32;
        this._iconWidth = 32;
        this._symbolicIcon = albumArtCache.makeDefaultIcon(this._iconHeight, this._iconWidth)
        this._addListRenderers();
        this.player = player;
        this.player.connect('playlist-item-changed', Lang.bind(this, this.updateModel));
    },

    _onItemActivated: function (widget, id, path) {
        let button = Gtk.get_current_event().get_button()[1];
        if (button != 1)
            return;

        var iter = this._model.get_iter(path)[1]
        if (this._model.get_value(iter, 8) != errorIconName) {
            this.player.setPlaylist("Songs", null, this._model, iter, 5);
            this.player.setPlaying(true);
        }
    },

    updateModel: function(player, playlist, currentIter){
        if (playlist != this._model){
            return false;}
        if (this.iterToClean){
            this._model.set_value(this.iterToClean, 10, false);
        }
        this._model.set_value(currentIter, 10, true);
        this.iterToClean = currentIter.copy();
        return false;
    },

    _addItem: function(source, param, item) {
        if (item != null) {
            this._offset += 1;
            var iter = this._model.append();
            try{
                if (item.get_url())
                    this.player.discoverer.discover_uri(item.get_url());
                this._model.set(
                        iter,
                        [5, 8, 9, 10],
                        [item, nowPlayingIconName, false, false]
                    );
            } catch(err) {
                log(err.message);
                log("failed to discover url " + item.get_url());
                this._model.set(
                        iter,
                        [5, 8, 9, 10],
                        [item, errorIconName, false, true]
                    );
            }
        }
    },

    _addListRenderers: function() {
        let listWidget = this.view.get_generic_view();
        let cols = listWidget.get_columns();
        let cells = cols[0].get_cells();
        cells[2].visible = false;
        let nowPlayingSymbolRenderer = new Gtk.CellRendererPixbuf();
        var columnNowPlaying = new Gtk.TreeViewColumn();
        nowPlayingSymbolRenderer.xalign = 1.0;
        columnNowPlaying.pack_start(nowPlayingSymbolRenderer, false);
        columnNowPlaying.fixed_width = 24;
        columnNowPlaying.add_attribute(nowPlayingSymbolRenderer, "visible", 10);
        columnNowPlaying.add_attribute(nowPlayingSymbolRenderer, "icon_name", 8);
        listWidget.insert_column(columnNowPlaying, 0);

        let titleRenderer = new Gtk.CellRendererText({ xpad: 0 });
        listWidget.add_renderer(titleRenderer,Lang.bind(this,function (col,cell,model,iter) {
            let item = model.get_value(iter,5);
            titleRenderer.xalign = 0.0;
            titleRenderer.yalign = 0.5;
            titleRenderer.height = 48;
            titleRenderer.ellipsize = Pango.EllipsizeMode.END;
            titleRenderer.text = AlbumArtCache.getMediaTitle(item);
        }))
        let starRenderer = new Gtk.CellRendererPixbuf({xpad: 32});
        listWidget.add_renderer(starRenderer,Lang.bind(this,function (col,cell,model,iter) {
            let showstar = model.get_value(iter, 9);
            if(showstar){
            starRenderer.icon_name = starIconName;

            }
            else
            starRenderer.pixbuf = null;
        }))

        let durationRenderer =
            new Gd.StyledTextRenderer({ xpad: 32 });
        durationRenderer.add_class('dim-label');
        listWidget.add_renderer(durationRenderer, Lang.bind(this,
            function(col, cell, model, iter) {
                let item = model.get_value(iter, 5);
                if (item) {
                    let duration = item.get_duration ();
                    var minutes = parseInt(duration / 60);
                    var seconds = duration % 60;
                    var time = null
                    if (seconds < 10)
                        time =  minutes + ":0" + seconds;
                    else
                        time = minutes + ":" + seconds;
                    durationRenderer.xalign = 1.0;
                    durationRenderer.text = time;
                }
            }));

        let artistRenderer =
            new Gd.StyledTextRenderer({ xpad: 32});
        artistRenderer.add_class('dim-label');
        artistRenderer.ellipsize = Pango.EllipsizeMode.END;
        listWidget.add_renderer(artistRenderer, Lang.bind(this,
            function(col, cell, model, iter) {
                let item = model.get_value(iter, 5);
                if (item) {
                    artistRenderer.ellipsize = Pango.EllipsizeMode.END;
                    artistRenderer.text = item.get_string(Grl.METADATA_KEY_ARTIST);
                }
            }));
        let typeRenderer =
            new Gd.StyledTextRenderer({ xpad: 32});
        typeRenderer.add_class('dim-label');
        typeRenderer.ellipsize = Pango.EllipsizeMode.END;
        listWidget.add_renderer(typeRenderer, Lang.bind(this,
            function(col, cell, model, iter) {
                let item = model.get_value(iter, 5);
                if (item) {
                    typeRenderer.ellipsize = Pango.EllipsizeMode.END;
                    typeRenderer.text = item.get_string(Grl.METADATA_KEY_ALBUM);
                }
            }));

    },

    populate: function() {
        if (grilo.tracker != null)
            grilo.populateSongs (this._offset, Lang.bind(this, this._addItem, null));
    },

});

const Playlists = new Lang.Class({
    Name: "PlaylistsView",
    Extends: ViewContainer,

    _init: function(header_bar, selection_toolbar, player) {
        this.parent("Playlists", header_bar, selection_toolbar);
    },
});

const Artists = new Lang.Class({
    Name: "ArtistsView",
    Extends: ViewContainer,

    _init: function(header_bar, selection_toolbar ,player) {
        this.parent("Artists", header_bar, selection_toolbar, true);
        this.player = player;
        this._artists = {};
        this.countQuery = Query.artist_count;
        this._artistAlbumsWidget = new Gtk.Frame({
            shadow_type:    Gtk.ShadowType.NONE
        });
        this.view.set_view_type(Gd.MainViewType.LIST);
        this.view.set_hexpand(false);
        this._artistAlbumsWidget.set_hexpand(true);
        this.view.get_style_context().add_class("artist-panel");
        this.view.get_generic_view().get_selection().set_mode(Gtk.SelectionMode.SINGLE);
        this._grid.attach(new Gtk.Separator({orientation: Gtk.Orientation.VERTICAL}), 1, 0, 1, 1)
        this._grid.attach(this._artistAlbumsWidget, 2, 0, 2, 2);
        this._addListRenderers();
        if(Gtk.Settings.get_default().gtk_application_prefer_dark_theme)
            this.view.get_generic_view().get_style_context().add_class("artist-panel-dark");
        else
            this.view.get_generic_view().get_style_context().add_class("artist-panel-white");
        this.show_all();
    },

    _populate: function(widget, param) {
        let selection = this.view.get_generic_view().get_selection();
        if (!selection.get_selected()[0]) {
            this._allIter = this._model.append();
            this._artists["All Artists".toLowerCase()] = {"iter": this._allIter, "albums": []};
            this._model.set(
                this._allIter,
                [0, 1, 2, 3],
                ["All Artists", "All Artists", "All Artists", "All Artists"]
            );
            selection.select_path(this._model.get_path(this._allIter));
            this.view.emit('item-activated', "0", this._model.get_path(this._allIter));
        }
        this._init = true;
        this.populate();
    },

    _addListRenderers: function() {
        let listWidget = this.view.get_generic_view();

        var cols = listWidget.get_columns()
        var cells = cols[0].get_cells()
        cells[2].visible = false

        let typeRenderer =
            new Gd.StyledTextRenderer({ xpad: 0 });
        typeRenderer.ellipsize = 3;
        typeRenderer.xalign = 0.0;
        typeRenderer.yalign = 0.5;
        typeRenderer.height = 48;
        typeRenderer.width = 220;
        listWidget.add_renderer(typeRenderer, Lang.bind(this,
            function(col, cell, model, iter) {
                typeRenderer.text = model.get_value(iter, 0);
            }));
    },

    _onItemActivated: function (widget, id, path) {
        let button = Gtk.get_current_event().get_button()[1];
        if (button != 1)
            return;

        let children = this._artistAlbumsWidget.get_children();
        for (let i=0; i<children.length; i++)
            this._artistAlbumsWidget.remove(children[i]);
        let iter = this._model.get_iter (path)[1];
        let artist = this._model.get_value (iter, 0);
        let albums = this._artists[artist.toLowerCase()]["albums"];
        this.artistAlbums = null;
        if (this._model.get_string_from_iter(iter) == this._model.get_string_from_iter(this._allIter))
            this.artistAlbums = new Widgets.AllArtistsAlbums(this.player);
        else
            this.artistAlbums = new Widgets.ArtistAlbums(artist, albums, this.player);
        this._artistAlbumsWidget.add(this.artistAlbums);
    },

    _addItem: function (source, param, item) {
        this._offset += 1;
        if (item == null)
            return
        var artist = "Unknown"
        if (item.get_author() != null)
            artist = item.get_author();
        if (item.get_string(Grl.METADATA_KEY_ARTIST) != null)
            artist = item.get_string(Grl.METADATA_KEY_ARTIST)
        if (this._artists[artist.toLowerCase()] == undefined) {
            var iter = this._model.append();
            this._artists[artist.toLowerCase()] = {"iter": iter, "albums": []}
            this._model.set(
            iter,
            [0, 1, 2, 3],
            [artist, artist, artist, artist]
        );
        }
        this._artists[artist.toLowerCase()]["albums"].push(item)
        this.emit("artist-added");
    },

    populate: function () {
        if(grilo.tracker != null) {
            grilo.populateArtists(this._offset, Lang.bind(this, this._addItem, null));
            //FIXME: We're emitting this too early, need to wait for all artists to be filled in
        }
    },
});
