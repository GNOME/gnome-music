/*
 * Copyright (c) 2013 Eslam Mostafa <cseslam@gmail.com>.
 * Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>.
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
const GdkPixbuf = imports.gi.GdkPixbuf;
const Gio = imports.gi.Gio;
const Lang = imports.lang;
const Grl = imports.gi.Grl;
const Query = imports.query;
const Grilo = imports.grilo;

const grilo = Grilo.grilo;
const AlbumArtCache = imports.albumArtCache;
const albumArtCache = AlbumArtCache.AlbumArtCache.getDefault();

const ClickableLabel = new Lang.Class({
    Name: "ClickableLabel",
    Extends: Gtk.Button,
    
    _init: function (track) {
        this.track = track
        var text = track.get_title()
        var duration = track.get_duration()
        let box = new Gtk.HBox();
        let label = new Gtk.Label({ label : text });
        label.set_alignment(0.0, 0.5)

        var minutes = parseInt(duration / 60);
        var seconds = duration % 60;
        var time = null
        if (seconds < 10)
            time =  minutes + ":0" + seconds;
        else
            time = minutes + ":" + seconds;
        let length_label = new Gtk.Label({ label : time });
        length_label.set_alignment(0.0, 0.5)
        
        this.parent();
        this.set_relief(Gtk.ReliefStyle.NONE);
        this.set_can_focus(false);
        box.homogeneous = true;
        box.pack_start(label, true, true, 0);
        box.pack_end(length_label, true, true, 0);
        this.add(box);
        this.show_all();
            
        this.connect("clicked", Lang.bind(this, this._on_btn_clicked));
    },
    
    _on_btn_clicked: function(btn) {
    },
    
});


const AlbumWidget = new Lang.Class({
    Name: "AlbumWidget",
    Extends: Gtk.EventBox,
    
    _init: function (album) {
        this.hbox = new Gtk.HBox ();
        this.box = new Gtk.VBox();
        this.scrolledWindow = new Gtk.ScrolledWindow();
        this.songsList = new Gtk.VBox();
        this.cover = new Gtk.Image();
        this.vbox = new Gtk.VBox();
        this.title_label = new Gtk.Label({label : ""});
        this.artist_label = new Gtk.Label({label : ""});
        this.tracks_labels = {};
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
        this.box.set_homogeneous (false);
        this.songsList.pack_start(new Gtk.Label(), false, false, 24)
        this.songsList.pack_end(new Gtk.Label(), true, true, 24)
        this.vbox.set_homogeneous(false);
        this.scrolledWindow.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC);
        this.scrolledWindow.add(this.songsList);


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
        this.vbox.pack_start (this.title_label, false, false, 9);
        this.vbox.pack_start (this.artist_label, false, false, 0);
        this.vbox.pack_start (new Gtk.Label({label:""}), false, false, 6);
        this.vbox.pack_start(this.infobox, false, false, 0)
        this.box.pack_end (this.scrolledWindow, true, true, 0);

        let hbox = new Gtk.Box()
        hbox.pack_start (new Gtk.Label({label: ""}), true, true, 0)
        hbox.pack_start (this.vbox, false, false, 0)
        this.hbox.pack_start (hbox, true, true, 64);
        this.hbox.pack_start (this.box, true, true, 6);

        this.get_style_context ().add_class ("view");
        this.get_style_context ().add_class ("content-view");
        this.add(this.hbox)
        this.show_all ()
    },

    update: function (artist, album, item) {
        var pixbuf = albumArtCache.lookup (256, artist, item.get_string(Grl.METADATA_KEY_ALBUM));
        let duration = 0;
        for (let t in this.tracks_labels) {
            this.songsList.remove(this.tracks_labels[t]);
        }
        this.tracks_labels = {};
        grilo.getAlbumSongs(artist, album, Lang.bind(this, function (source, prefs, track) {
            if (track != null) {
                duration = duration + track.get_duration()
                this.tracks_labels[track.get_title()] = new ClickableLabel (track);
                this.songsList.pack_start(this.tracks_labels[track.get_title()], false, false, 0);
                this.running_length_label_info.set_text(parseInt(duration/60) + " min")
            }
        }));

        //update labels view
        var i = 0 ;
        for (let t in this.tracks_labels) {
            let length = new Gtk.Label ({label : tracks[t]});
            this.songsList.pack_start(this.tracks_labels[t], false, false, 0);
            this.running_length = this.running_length+ parseInt(tracks[t], 10);
            i++;
        }

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
