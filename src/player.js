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
const Gdk = imports.gi.Gdk;

//pkg.initSubmodule('libgd');

const Mainloop = imports.mainloop;
const AlbumArtCache = imports.albumArtCache;

const ART_SIZE = 34;

const RepeatType = {
    NONE: 0,
    SONG: 1,
    ALL:  2
}

const Player = new Lang.Class({
    Name: "Player",

    _init: function() {
        this.playlist = null;
        this.playlistType = null;
        this.playlistId = null;
        this.playlistField = null;
        this.currentTrack = null;
        this._lastState = Gst.State.NULL;
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
            if(player.nextUrl != null) {
                player.set_property('uri', player.nextUrl);
                GLib.idle_add(GLib.PRIORITY_HIGH, Lang.bind(this, this.loadNextTrack));
            }
            return true;
        }));
        this._setupView();
    },

    setPlaying: function(bool) {
        this.eventBox.set_visible(true);
        if (bool) {
            this.play();
            this.playBtn.set_image(this._pauseImage);
        }
        else {
            this.pause();
            this.playBtn.set_image(this._playImage);
        }
    },

    loadNextTrack: function(){
        if (this.timeout) {
            GLib.source_remove(this.timeout);
        }
        if (!this.playlist || !this.currentTrack || !this.playlist.iter_next(this.currentTrack))
            this.currentTrack=null;
        else {
            this.load( this.playlist.get_value( this.currentTrack, this.playlistField));
            this.timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, Lang.bind(this, this._updatePositionCallback));
        }
    },

    load: function(media) {
        var pixbuf;
        this._setDuration(media.get_duration());
        this.songTotalTimeLabel.set_label(this.secondsToString (media.get_duration()));
        this.progressScale.sensitive = true;
        this.playBtn.set_sensitive(true);
        // FIXME: site contains the album's name. It's obviously a hack to remove
        let tmp = this.currentTrack.copy();
        if(this.playlist.iter_next(tmp))
            this.nextBtn.set_sensitive(true);
        else
            this.nextBtn.set_sensitive(false);

        tmp = this.currentTrack.copy();
        if(this.playlist.iter_previous(tmp))
            this.prevBtn.set_sensitive(true);
        else
            this.prevBtn.set_sensitive(false);
        pixbuf = this.cache.lookup (ART_SIZE, media.get_artist (), media.get_string(Grl.METADATA_KEY_ALBUM));
        this.coverImg.set_from_pixbuf (pixbuf);

        if (media.get_title() != null) {
            this.titleLabel.set_label(media.get_title());
        }

        else {
            let url = media.get_url(),
                file = GLib.File.new_for_path(url),
                basename = file.get_basename(),
                toShow = GLib.Uri.unescape_string(basename, null);

            this.titleLabel.set_label(toShow);
        }

        if (media.get_artist() != null) {
            this.artistLabel.set_label(media.get_artist());
        }

        else {
            this.artistLabel.set_label("Unknown artist");
        }

        this.player.set_property("uri", media.get_url());

        // Store next available url
        let nextTrack = this.currentTrack.copy();
        if (this.playlist.iter_next(nextTrack)) {
            let nextMedia = this.playlist.get_value(nextTrack, this.playlistField);
            this.player.nextUrl = nextMedia.get_url();
        } else {
            this.player.nextUrl = null;
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
        this.load( this.playlist.get_value( this.currentTrack, this.playlistField));

        this.player.set_state(Gst.State.PLAYING);
        this._updatePositionCallback();
        this.timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, Lang.bind(this, this._updatePositionCallback));
    },

    pause: function () {
        if (this.timeout) {
            GLib.source_remove(this.timeout);
            this.timout = null;
        }
        this.player.set_state(Gst.State.PAUSED);
    },

    stop: function() {
        this.player.set_state(Gst.State.NULL);
    },

    playNext: function () {
        this.stop();
        this.loadNextTrack();
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
        this.playlistType = type;
        this.playlistId = id;
        this.currentTrack = iter;
        this.playlistField = field;
    },

    runningPlaylist: function (type, id, force){
        if (type == this.playlistType && id == this.playlistId)
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
        this.eventBox = this._ui.get_object('eventBox');
        this.prevBtn = this._ui.get_object('previous_button');
        this.playBtn = this._ui.get_object('play_button');
        this.nextBtn = this._ui.get_object('next_button');
        this._playImage = this._ui.get_object('play_image');
        this._pauseImage = this._ui.get_object('pause_image');
        this.progressScale = this._ui.get_object('progress_scale');
        this.songPlaybackTimeLabel = this._ui.get_object('playback');
        this.songTotalTimeLabel = this._ui.get_object('duration');
        this.titleLabel = this._ui.get_object('title');
        this.artistLabel = this._ui.get_object('artist');
        this.coverImg = this._ui.get_object('cover');
        this.duration = this._ui.get_object('duration');
        this.replayBtn = this._ui.get_object('menuButton');
        let replayMenu = this._ui.get_object('replayMenu');
        if(Gtk.Settings.get_default().gtk_application_prefer_dark_theme)
            var color = new Gdk.Color({red:65535,green:65535,blue:65535});
        else
            var color = new Gdk.Color({red:0,green:0,blue:0});
        this._playImage.modify_fg(Gtk.StateType.ACTIVE,color);
        this._pauseImage.modify_fg(Gtk.StateType.ACTIVE,color);

        let replaySong = Gtk.MenuItem.new_with_label("replay song");
        let replayAll = Gtk.MenuItem.new_with_label("replay all");
        let shuffle = Gtk.MenuItem.new_with_label("shuffle");
        replayMenu.attach(replaySong, 0, 1, 0, 1);
        replayMenu.attach(replayAll, 0, 1, 1, 2);
        replayMenu.attach(shuffle, 0, 1, 2, 3);
        replayMenu.show_all();

        this.prevBtn.connect("clicked", Lang.bind(this, this._onPrevBtnClicked));
        this.playBtn.connect("clicked", Lang.bind(this, this._onPlayBtnClicked));
        this.nextBtn.connect("clicked", Lang.bind(this, this._onNextBtnClicked));
        this.progressScale.connect("button-press-event", Lang.bind(this,
            function() {
                this._lastState = this.player.get_state(1)[1];
                this.player.set_state(Gst.State.PAUSED);
                this._updatePositionCallback();
                GLib.source_remove(this.timeout);
                return false;
            }));
        this.progressScale.connect("value-changed", Lang.bind(this,
            function() {
                let seconds = Math.floor(this.progressScale.get_value() / 60);
                this.songPlaybackTimeLabel.set_label(this.secondsToString(seconds));
                return false;
            }));
        this.progressScale.connect("button-release-event", Lang.bind(this,
            function() {
                this.onProgressScaleChangeValue(this.progressScale);
                this.player.set_state(Gst.State.PLAYING);
                this._updatePositionCallback();
                this.player.set_state(this._lastState);
                this.timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, Lang.bind(this, this._updatePositionCallback));
                return false;
            }));
    },

    secondsToString: function(duration){
        var minutes = parseInt( duration / 60 ) % 60;
        var seconds = duration % 60;

        return minutes + ":" + (seconds  < 10 ? "0" + seconds : seconds);
    },

    _onPlayBtnClicked: function(btn) {
        if(this.player.get_state(1)[1] == Gst.State.PLAYING){
            this.setPlaying(false);
        }else{
            this.setPlaying(true);
        }
    },

    _onNextBtnClicked: function(btn) {
        this.playNext();
    },

    _onPrevBtnClicked: function(btn) {
        this.playPrevious();
    },

    _setDuration: function(duration) {
        this.duration = duration;
        this.progressScale.set_range(0.0, duration*60);
    },

    _updatePositionCallback: function() {
        var position = this.player.query_position(Gst.Format.TIME, null)[1]/1000000000;
        if (position >= 0) {
            this.progressScale.set_value(position * 60);
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
