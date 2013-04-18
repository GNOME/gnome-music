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
            this.released_label_info.set_text(released_date.get_year().toString());
	} else {
            this.released_label_info.set_text("----");
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


const ArtistAlbums = new Lang.Class({
    Name: "ArtistAlbumsWidget",
    Extends: Gtk.VBox,

    _init: function (artist, albums) {
        this.artist = artist
        this.albums = albums
        this.parent();
        this.set_border_width(24)
        this.label = new Gtk.Label()
        this.label.set_markup("<b>" + this.artist + "</b>")
        this.label.set_alignment(0.0, 0.5)
        this.pack_start(this.label, false, false, 0)
        this.pack_start(new Gtk.HSeparator(), false, false, 12)
        for (var i=0; i < albums.length; i++)
            this.pack_start(new ArtistAlbumWidget(artist, albums[i]), false, false, 9);
        this.show_all();
    },
});

const ArtistAlbumWidget = new Lang.Class({
    Name: "ArtistAlbumWidget",
    Extends: Gtk.HBox,

    _init: function (artist, album) {
        this.parent();
        this.album = album;
        this.cover = new Gtk.Image();
        this.title = new Gtk.Label();
        this.title.set_ellipsize(2);
        var pixbuf = albumArtCache.lookup (128, artist, album.get_title());
        if (pixbuf == null) {
            let path = "/usr/share/icons/gnome/scalable/places/folder-music-symbolic.svg";
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, -1, 128, true);
        }
        this.cover.set_from_pixbuf (pixbuf);
        this.pack_start(this.cover, false, false, 0)
        var vbox = new Gtk.VBox()
        this.pack_start(vbox, true, true, 32)
        this.title.set_markup("<span color='grey'><b>" + album.get_title() + "</b></span>")
        var tracks = [];
        grilo.getAlbumSongs(album.get_id(), Lang.bind(this, function (source, prefs, track) {
            if (track != null) {
                tracks.push(track);
                let released_date = album.get_publication_date();
                if (released_date != null) {
                    this.title.set_markup("<span color='grey'><b>" + album.get_title() + "</b> (" + released_date.get_year().toString() + ")</span>")
                } else {
                    this.title.set_markup("<span color='grey'><b>" + album.get_title() + "</b></span>")
                }
            }
        }));
        this.title.set_alignment(0.0, 0.5)
        vbox.pack_start(this.title, false, false, 0)
        this.show_all()
    },
});
