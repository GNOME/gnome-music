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
const Gd = imports.gi.Gd;
const Gst = imports.gi.Gst;
const GLib = imports.gi.GLib;
const GObject = imports.gi.GObject;
const Grl = imports.gi.Grl;
const Signals = imports.signals;

//pkg.initSubmodule('libgd');

const Mainloop = imports.mainloop;
const AlbumArtCache = imports.albumArtCache;

const ART_SIZE = 36;

const RepeatType = {
    NONE: 0,
    SONG: 1,
    ALL:  2
}

const PlayPauseButton = new Lang.Class({
    Name: "PlayPauseButton",
    Extends: Gtk.ToggleButton,

    _init: function() {
        this.play_image = Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.MENU);
        this.pause_image = Gtk.Image.new_from_icon_name("media-playback-pause-symbolic", Gtk.IconSize.MENU);

        this.parent();
        this.set_playing();
    },

    set_playing: function() {
        this.set_image(this.pause_image);
        this.show_all();
    },

    set_paused: function() {
        this.set_image(this.play_image);
        this.show_all();
    },

});

const MenuButton = new Lang.Class({
    Name: "MenuButton",
    Extends: Gtk.Button,

    _init: function () {
        this.parent();
        let box = new Gtk.HBox();
        let image = Gtk.Image.new_from_icon_name("media-playlist-repeat-symbolic", Gtk.IconSize.MENU);
        let arrow = Gtk.Image.new_from_icon_name("go-down-symbolic", Gtk.IconSize.MENU);
        box.pack_start(image, false, false, 3);
        box.pack_start(arrow, false, false, 3);
        this.add(box);
        this.show_all();
    },
});

const Player = new Lang.Class({
    Name: "Player",

    _init: function() {
        this.playlist = null;
        this.playlist_type = null;
        this.playlist_id = null;
        this.playlist_field = null;
        this.currentTrack = null;
        this.repeat = RepeatType.NONE;
        this.cache = AlbumArtCache.AlbumArtCache.getDefault();

        Gst.init(null, 0);
        this.player = Gst.ElementFactory.make("playbin", "player");
        this.player.connect("about-to-finish", Lang.bind(this,
            function() {
                if (!this.playlist || !this.currentTrack || !this.playlist.iter_next(this.currentTrack))
                    this.currentTrack=null;
                else {
                    this.load( this.playlist.get_value( this.currentTrack, this.playlist_field));
                    this.progress_scale.set_value(0.0);
                }
                return true;
            }));
        this.bus = this.player.get_bus();
        this.bus.add_signal_watch()
        this.bus.connect("message", Lang.bind(this,
            function(bus, message) {
            if (message.type == Gst.MessageType.ERROR) {
                let uri;
                if (this.playlist[this.currentTrack])
                    uri = this.playlist[this.currentTrack].get_url();
                else
                    uri = "none"
                log("URI:" + uri);
                log("Error:" + message.parse_error());
                this.stop();
            }
        }));

        this._setup_view();
    },

    load: function(media) {
        var pixbuf;

        this._setDuration(media.get_duration());
        this.song_total_time_lbl.set_label(this.seconds_to_string (media.get_duration()));
        this.progress_scale.sensitive = true;
        this.prev_btn.set_sensitive(true);
        this.play_btn.set_sensitive(true);
        this.next_btn.set_sensitive(true);

        // FIXME: site contains the album's name. It's obviously a hack to remove

        pixbuf = this.cache.lookup (ART_SIZE, media.get_artist (), media.get_string(Grl.METADATA_KEY_ALBUM));
        this.cover_img.set_from_pixbuf (pixbuf);

        if (media.get_title() != null) {
            this.title_lbl.set_label(media.get_title());
        }

        else {
            let url = media.get_url(),
                file = GLib.File.new_for_path(url),
                basename = file.get_basename(),
                to_show = GLib.Uri.unescape_string(basename, null);

            this.title_lbl.set_label(to_show);
        }

        if (media.get_artist() != null) {
            this.artist_lbl.set_label(media.get_artist());
        }

        else {
            this.artist_lbl.set_label("Unknown artist");
        }
        this.player.set_property("uri", media.get_url());

        this.emit("playlist-item-changed", this.playlist, this.currentTrack);
    },

    play: function() {
        this.play_btn.set_active(true);
        if(this.player.get_state(1)[1] != Gst.State.PAUSED) {
            this.stop();
        }
        this.load( this.playlist.get_value( this.currentTrack, this.playlist_field));

        this.player.set_state(Gst.State.PLAYING);
        this._updatePositionCallback();
        this.timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, Lang.bind(this, this._updatePositionCallback));
    },

    pause: function () {
        this.player.set_state(Gst.State.PAUSED);
        this.play_btn.set_active(false);
    },

    stop: function() {
        //this.play_btn.set_playing();
        this.player.set_state(Gst.State.NULL);
        if (this.timeout) {
            GLib.source_remove(this.timeout);
        }
    },

    playNext: function () {
        // don't do anything if we don't have the basics
        if (!this.playlist || !this.currentTrack)
               return;
        let savedTrack;
        // if we are in repeat dong mode, just play the song again
        // other, save the node
        if (RepeatType.SONG == this.repeat){
            this.stop();
            this.play();
            return;
        } else
            savedTrack = this.currentTrack.copy()

        // if we were able to just to the next iter, play it
        // otherwise...
        if (!this.playlist.iter_next(this.currentTrack)){
            // ... if all repeat mode is activated, loop around the listStore
            // if not, restore the saved node and don't play anything
            if (RepeatType.ALL== this.repeat)
                this.currentTrack = this.playlist.get_iter_first()[1];
            else {
                this.currentTrack = savedTrack;
                return;
            }
        }
        this.stop();
        this.play();
    },

    playPrevious: function () {
        if (!this.playlist || !this.currentTrack)
               return;
        let savedTrack;
        if (RepeatType.SONG == this.repeat){
            this.stop();
            this.play();
            return;
        } else
            savedTrack = this.currentTrack.copy()

        if (!this.playlist.iter_previous(this.currentTrack)){
            if (RepeatType.ALL== this.repeat){
                //FIXME there has to be a better way
                let index = 0;
                let iter = this.playlist.get_iter_first()[1];
                while (this.playlist.iter_next(iter))
                    index++;
                this.currentTrack = this.playlist.get_iter_from_string(index.toString())[1];
            }
            else {
                this.currentTrack = savedTrack;
                return;
            }
        }
        this.stop();
        this.play();
    },

    setPlaylist: function (type, id, model, iter, field) {
        this.playlist = model;
        this.playlist_type = type;
        this.playlist_id = id;
        this.currentTrack = iter;
        this.playlist_field = field;
    },

    runningPlaylist: function (type, id, force){
        if (type == this.playlist_type && id == this.playlist_id)
            return this.playlist;
        else
            return null;
    },

    setCurrentTrack: function (track) {
        for(let t in this.playlist) {
            if(this.playlist[t].get_url() == track.get_url()) {
                this.currentTrack = t;
            }
        }
    },

    _setup_view: function() {
        let alignment,
            artist_lbl,
            box,
            databox,
            label,
            toolbar_center,
            toolbar_end,
            toolbar_start,
            toolbar_song_info;

        this.box = new Gtk.Box();
        this.box.set_spacing(9)
        this.box.set_border_width(9)
        toolbar_start = new Gtk.Box({
            orientation: Gtk.Orientation.HORIZONTAL,
            spacing: 0
        });
        toolbar_start.get_style_context().add_class(Gtk.STYLE_CLASS_LINKED);

        this.prev_btn = new Gtk.Button();
        this.prev_btn.set_size_request(35, -1);
        this.prev_btn.set_image(Gtk.Image.new_from_icon_name("media-skip-backward-symbolic", Gtk.IconSize.MENU));
        this.prev_btn.connect("clicked", Lang.bind(this, this._onPrevBtnClicked));
        this.prev_btn.set_sensitive(false);
        toolbar_start.pack_start(this.prev_btn, false, false, 0);

        this.play_btn = new PlayPauseButton();
        this.play_btn.set_size_request(55, -1);
        this.play_btn.connect("toggled", Lang.bind(this, this._onPlayBtnToggled));
        this.play_btn.set_sensitive(false);
        toolbar_start.pack_start(this.play_btn, false, false, 0);

        this.next_btn = new Gtk.Button();
        this.next_btn.set_size_request(35, -1);
        this.next_btn.set_image(Gtk.Image.new_from_icon_name("media-skip-forward-symbolic", Gtk.IconSize.MENU));
        this.next_btn.connect("clicked", Lang.bind(this, this._onNextBtnClicked));
        this.next_btn.set_sensitive(false);
        toolbar_start.pack_start(this.next_btn, false, false, 0);
        this.box.pack_start(toolbar_start, false, false, 3)

        this.progress_scale = new Gtk.Scale({
            orientation: Gtk.Orientation.HORIZONTAL,
            sensitive: false
        });
        this.progress_scale.set_draw_value(false);
        this._setDuration(1);

        this.progress_scale.connect("button-press-event", Lang.bind(this,
            function() {
                this.player.set_state(Gst.State.PAUSED);
                this._updatePositionCallback();
                GLib.source_remove(this.timeout);
                return false;
            }));
        this.progress_scale.connect("value-changed", Lang.bind(this,
            function() {
                let seconds = Math.floor(this.progress_scale.get_value() / 60);
                this.song_playback_time_lbl.set_label(this.seconds_to_string(seconds));
                return false;
            }));
        this.progress_scale.connect("button-release-event", Lang.bind(this,
            function() {
                this.onProgressScaleChangeValue(this.progress_scale);
                this.player.set_state(Gst.State.PLAYING);
                this._updatePositionCallback();
                this.timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, Lang.bind(this, this._updatePositionCallback));
                return false;
            }));

        this.toolbar_song_info = new Gtk.Box({
            orientation: Gtk.Orientation.HORIZONTAL,
            spacing: 0
        });

        this.cover_img = new Gtk.Image();
        this.toolbar_song_info.pack_start(this.cover_img, false, false, 0);
        databox = new Gtk.Box({
            orientation: Gtk.Orientation.VERTICAL,
            spacing: 0
        });

        this.title_lbl = new Gtk.Label({
            label: ""
        });
        databox.pack_start(this.title_lbl, false, false, 0);

        this.artist_lbl = new Gtk.Label({
            label: ""
        });
        this.artist_lbl.get_style_context().add_class("dim-label");
        databox.pack_start(this.artist_lbl, false, false, 0);

        toolbar_center = new Gtk.Box({
            orientation: Gtk.Orientation.HORIZONTAL,
            spacing: 0
        });

        this.toolbar_song_info.pack_start(databox, false, false, 12);

        toolbar_center.pack_start(this.toolbar_song_info, false, false, 3);
        toolbar_center.pack_start(this.progress_scale, true, true, 0);
        toolbar_center.pack_start(new Gtk.Label({}), false, false, 3);

        this.song_playback_time_lbl = new Gtk.Label({
            label: "00:00"
        });
        toolbar_center.pack_start(this.song_playback_time_lbl, false, false, 0);
        label = new Gtk.Label({
            label: "/"
        });
        toolbar_center.pack_start(label, false, false, 0);
        this.song_total_time_lbl = new Gtk.Label({
            label: "00:00"
        });
        toolbar_center.pack_start(this.song_total_time_lbl, false, false, 0);
        this.box.pack_start(toolbar_center, true, true, 0)

        toolbar_end = new Gtk.Box({
            orientation: Gtk.Orientation.HORIZONTAL,
            spacing: 5
        });
        alignment = new Gtk.Alignment({
            xalign: 1,
            yalign: 0.5,
            xscale: 0,
            yscale: 0
        });
        this.box.pack_end(toolbar_end, false, false, 3);

        let menuBtn = new MenuButton();
        toolbar_end.pack_end(menuBtn, false, false, 0);

        this.eventbox = new Gtk.Frame();
        this.eventbox.get_style_context().add_class("play-bar")
        this.eventbox.add(this.box);
        this.eventbox.show_all();

    },

    seconds_to_string: function(duration){
        var minutes = parseInt( duration / 60 ) % 60;
        var seconds = duration % 60;

        return (minutes < 10 ? "0" + minutes : minutes) + ":" + (seconds  < 10 ? "0" + seconds : seconds);
    },

    uri: function() {
    },

    _onPlayBtnToggled: function(btn) {
        if (this.player.get_state(1)[1] != Gst.State.PAUSED) {
            this.pause();
            this.play_btn.set_paused();
        } else {
            this.play();
            this.play_btn.set_playing();
        }
    },

    _onNextBtnClicked: function(btn) {
        this.playNext();
    },

    _onPrevBtnClicked: function(btn) {
        this.playPrevious();
    },

    _onShuffleBtnClicked: function(order) {
    },

    _onPlaylistShuffleModeChanged: function(mode) {
        this.shuffle_btn.set_active(mode);
    },

    _setDuration: function(duration) {
        this.duration = duration;
        this.progress_scale.set_range(0.0, duration*60);
        this.progress_scale.set_value(0.0);
    },

    _updatePositionCallback: function() {
        let seconds = Math.floor(this.progress_scale.get_value() / 60);
        this.progress_scale.set_value((seconds+ 1) * 60);
        return true;
    },

    onProgressScaleChangeValue: function(scroll) {
        var seconds = scroll.get_value() / 60;
        if(seconds <= this.duration) {
            this.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, seconds * 1000000000);
        }

        return false;
     },
});
Signals.addSignalMethods(Player.prototype);
