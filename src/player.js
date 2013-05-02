/*
 * Copyright (c) 2013 Eslam Mostafa.
 * Copyright (c) 2013 Vadim Rutkovsky.
 * Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
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
const GdkPixbug = imports.gi.GdkPixbuf;
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
        this.bus = this.player.get_bus();
        this.bus.add_signal_watch();
        this.bus.connect("message::error", Lang.bind(this, function(bus, message) {
            let uri;
            if (this.playlist[this.currentTrack])
                uri = this.playlist[this.currentTrack].get_url();
            else
                uri = "none"
            log("URI:" + uri);
            log("Error:" + message.parse_error());
            this.stop();
            return true;
        }));


        // Set URI earlier - this will enable gapless playback
        this.player.connect("about-to-finish", Lang.bind(this, function(player) {
            if(player.next_url != null) {
                player.set_property('uri', player.next_url);
                GLib.idle_add(GLib.PRIORITY_HIGH, Lang.bind(this, this.load_next_track));
            }
            return true;
        }));
        this._setupView();
    },

    setPlaying: function(bool) {
        if (bool) {
            this.play()
            this.play_btn.set_image(this._pause_image);
        }
        else {
            this.pause()
            this.play_btn.set_image(this._play_image);
        }
    },

    load_next_track: function(){
        if (this.timeout) {
            GLib.source_remove(this.timeout);
        }
        if (!this.playlist || !this.currentTrack || !this.playlist.iter_next(this.currentTrack))
            this.currentTrack=null;
        else {
            this.load( this.playlist.get_value( this.currentTrack, this.playlist_field));
            this.timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, Lang.bind(this, this._updatePositionCallback));
        }
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

        if (!this.player.next_url || media.get_url() != this.player.next_url) {
            this.player.set_property("uri", media.get_url());
        }

        // Store next available url
        let next_track = this.currentTrack.copy();
        if (this.playlist.iter_next(next_track)) {
            let next_media = this.playlist.get_value(next_track, this.playlist_field);
            this.player.next_url = next_media.get_url();
        } else {
            this.player.next_url = null;
        }
        this.emit("playlist-item-changed", this.playlist, this.currentTrack);
    },

    play: function() {
        if (this.timeout) {
            GLib.source_remove(this.timeout);
        }
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
    },

    stop: function() {
        this.player.set_state(Gst.State.NULL);
    },

    playNext: function () {
        this.stop();
        this.load_next_track();
        this.setPlaying(true);
    },

    playPrevious: function () {
        if (!this.playlist || !this.currentTrack)
               return;
        let savedTrack;
        if (RepeatType.SONG == this.repeat){
            this.stop();
            this.setPlaying(true);
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
        this.setPlaying(true);
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

    _setupView: function() {
        this._ui = new Gtk.Builder();
        this._ui.add_from_resource('/org/gnome/music/PlayerToolbar.ui');
        this.eventbox = this._ui.get_object('eventBox');
        this.prev_btn = this._ui.get_object('previous_button');
        this.play_btn = this._ui.get_object('play_button');
        this.play_btn.set_active(true)
        this.next_btn = this._ui.get_object('next_button');
        this._play_image = this._ui.get_object('play_image');
        this._pause_image = this._ui.get_object('pause_image');
        this.progress_scale = this._ui.get_object('progress_scale');
        this.song_playback_time_lbl = this._ui.get_object('playback');
        this.song_total_time_lbl = this._ui.get_object('duration');
        this.title_lbl = this._ui.get_object('title');
        this.artist_lbl = this._ui.get_object('artist');
        this.cover_img = this._ui.get_object('cover');
        this.duration = this._ui.get_object('duration');
        this.replay_model = this._ui.get_object('replay_button_model');
        this.replay_btn = this._ui.get_object('replay_button');

        let replay_icon = Gtk.Image.new_from_icon_name("media-playlist-repeat-symbolic", Gtk.IconSize.MENU);
        this.replay_model.append([replay_icon.get_pixbuf(), 'replay']);    
        this.replay_btn.show_all();

        this.prev_btn.connect("clicked", Lang.bind(this, this._onPrevBtnClicked));
        this.play_btn.connect("toggled", Lang.bind(this, this._onPlayBtnToggled));
        this.next_btn.connect("clicked", Lang.bind(this, this._onNextBtnClicked));
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
    },

    seconds_to_string: function(duration){
        var minutes = parseInt( duration / 60 ) % 60;
        var seconds = duration % 60;

        return (minutes < 10 ? "0" + minutes : minutes) + ":" + (seconds  < 10 ? "0" + seconds : seconds);
    },

    _onPlayBtnToggled: function(btn) {
       this.setPlaying(btn.get_active())
    },

    _onNextBtnClicked: function(btn) {
        this.playNext();
    },

    _onPrevBtnClicked: function(btn) {
        this.playPrevious();
    },

    _setDuration: function(duration) {
        this.duration = duration;
        this.progress_scale.set_range(0.0, duration*60);
    },

    _updatePositionCallback: function() {
        var position = this.player.query_position(Gst.Format.TIME, null)[1]/1000000000;
        if (position >= 0) {
            this.progress_scale.set_value(position * 60);
        }
        return true;
    },

    onProgressScaleChangeValue: function(scroll) {
        var seconds = scroll.get_value() / 60;
        if(seconds != this.duration) {
            this.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, seconds * 1000000000);
        } else {
            let duration = this.player.query_duration(Gst.Format.TIME, null);
            if (duration) {
                // Rewind a second back before the track end
                this.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, duration[1]-1000000000);
            }
        }
        return true;
     },
});
Signals.addSignalMethods(Player.prototype);
