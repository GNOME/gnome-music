/*
 * Copyright (c) 2013 Eslam Mostafa<cseslam@gmail.com>.
 * Copyright (c) 2013 Vadim Rutkovsky<vrutkovs@redhat.com>.
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
const Gio = imports.gi.Gio;
const Gst = imports.gi.Gst;
const GstPbutils = imports.gi.GstPbutils;
const GLib = imports.gi.GLib;
const GObject = imports.gi.GObject;
const Grl = imports.gi.Grl;
const Signals = imports.signals;
const Gdk = imports.gi.Gdk;

//pkg.initSubmodule('libgd');

const Mainloop = imports.mainloop;
const AlbumArtCache = imports.albumArtCache;

const ART_SIZE = 34;

const RepeatType = {
    NONE: 0,
    SONG: 1,
    ALL: 2,
    SHUFFLE: 3,
}

const Player = new Lang.Class({
    Name: "Player",

    _init: function() {
        this.playlist = null;
        this.playlistType = null;
        this.playlistId = null;
        this.playlistField = null;
        this.currentTrack = null;
        this._lastState = Gst.State.PAUSED;
        this.cache = AlbumArtCache.AlbumArtCache.getDefault();
        this._symbolicIcon = this.cache.makeDefaultIcon(ART_SIZE, ART_SIZE);

        Gst.init(null, 0);
        this.discoverer = new GstPbutils.Discoverer();
        this.player = Gst.ElementFactory.make("playbin", "player");
        this.bus = this.player.get_bus();
        this.bus.add_signal_watch();

        this._settings = new Gio.Settings({ schema: 'org.gnome.Music' });
        this._settings.connect('changed::repeat', Lang.bind(this, function(settings) {
            this.repeat = settings.get_enum('repeat');
            this._syncPrevNext();
            this._syncRepeatImage();
        }));
        this.repeat = this._settings.get_enum('repeat');

        this.bus.connect("message::state-changed", Lang.bind(this, function(bus, message) {
            // Note: not all state changes are signaled through here, in particular
            // transitions between Gst.State.READY and Gst.State.NULL are never async
            // and thus don't cause a message
            // In practice, this means only Gst.State.PLAYING and Gst.State.PAUSED are

            this._syncPlaying();
            this.emit('playing-changed');
        }));
        this.bus.connect("message::error", Lang.bind(this, function(bus, message) {
            let uri;
            let media =  this.playlist.get_value( this.currentTrack, this.playlistField);
            if (media != null)
                uri = media.get_url();
            else
                uri = "none"
            log("URI:" + uri);
            log("Error:" + message.parse_error());
            this.stop();
            return true;
        }));
        this.bus.connect("message::eos", Lang.bind(this, function(bus, message) {
            let nextTrack = this._getNextTrack();

            if (nextTrack) {
                GLib.idle_add(GLib.PRIORITY_HIGH, Lang.bind(this, function() {
                    this.currentTrack = nextTrack;
                    this.play();
                }));
            } else if (this.repeat == RepeatType.NONE) {
                this.stop();
                this.playBtn.set_image(this._playImage);
                this.progressScale.set_value(0);
                this.progressScale.sensitive = false;
                this.currentTrack = this.playlist.get_iter_first()[1];
                this.load(this.playlist.get_value(this.currentTrack, this.playlistField));
            } else {
                // Stop playback
                this.stop();
                this.playBtn.set_image(this._playImage);
                this.progressScale.set_value(0);
                this.progressScale.sensitive = false;
            }
        }));

        this._setupView();
    },

    _getNextTrack: function() {
        let currentTrack = this.currentTrack;
        let nextTrack;
        switch (this.repeat) {
        case RepeatType.SONG:
            nextTrack = currentTrack;
            break;

        case RepeatType.ALL:
            nextTrack = currentTrack.copy();
            if (!this.playlist.iter_next(nextTrack))
                nextTrack = this.playlist.get_iter_first()[1];
            break;

        case RepeatType.NONE:
            nextTrack = currentTrack.copy();
            nextTrack = this.playlist.iter_next(nextTrack) ? nextTrack : null;
            break;

        case RepeatType.SHUFFLE:
            /* FIXME */
            nextTrack = currentTrack;
        }

        return nextTrack;
    },

    _getIterLast: function() {
        let [ok, iter] = this.playlist.get_iter_first();
        let last;

        do {
            last = iter.copy();
            ok = this.playlist.iter_next(iter);
        } while (ok);

        return last;
    },

    _getPreviousTrack: function() {
        let currentTrack = this.currentTrack;
        let previousTrack;

        switch (this.repeat) {
        case RepeatType.SONG:
            previousTrack = currentTrack;
            break;

        case RepeatType.ALL:
            previousTrack = currentTrack.copy();
            if (!this.playlist.iter_previous(previousTrack))
                nextTrack = this._getIterLast();
            break;

        case RepeatType.NONE:
            previousTrack = currentTrack.copy();
            previousTrack = this.playlist.iter_previous(previousTrack) ? previousTrack : null;
            break;

        case RepeatType.SHUFFLE:
            /* FIXME */
            previousTrack = currentTrack;
        }

        return previousTrack;
    },

    _hasNext: function() {
        if (this.repeat == RepeatType.ALL ||
            this.repeat == RepeatType.SONG ||
            this.repeat == RepeatType.SHUFFLE) {
            return true;
        } else {
            let tmp = this.currentTrack.copy();
            return this.playlist.iter_next(tmp);
        }
    },

    _hasPrevious: function() {
        if (this.repeat == RepeatType.ALL ||
            this.repeat == RepeatType.SONG ||
            this.repeat == RepeatType.SHUFFLE) {
            return true;
        } else {
            let tmp = this.currentTrack.copy();
            return this.playlist.iter_previous(tmp);
        }
    },

    get playing() {
        let [ok, state, pending] = this.player.get_state(0);
        //log('get playing(), [ok, state, pending] = [%s, %s, %s]'.format(ok, state, pending));
        if (ok == Gst.StateChangeReturn.ASYNC)
            return pending == Gst.State.PLAYING;
        else if (ok == Gst.StateChangeReturn.SUCCESS)
            return state == Gst.State.PLAYING;
        else
            return false;
    },

    _syncPlaying: function() {
        this.playBtn.image = this.playing ? this._pauseImage : this._playImage;
    },

    _syncPrevNext: function() {
        this.nextBtn.sensitive = this._hasNext();
        this.prevBtn.sensitive = this._hasPrevious();
    },

    setPlaying: function(bool) {
        this.eventBox.show();

        if (bool)
            this.play();
        else
            this.pause();
    },

    load: function(media) {
        this._setDuration(media.get_duration());
        this.songTotalTimeLabel.label = this.secondsToString(media.get_duration());
        this.progressScale.sensitive = true;

        this.playBtn.sensitive = true;
        this._syncPrevNext();

        this.coverImg.set_from_pixbuf(this._symbolicIcon);
        this.cache.lookup(ART_SIZE, media.get_artist(), media.get_string(Grl.METADATA_KEY_ALBUM), Lang.bind(this,
            function(pixbuf) {
                if (pixbuf != null) {
                    this.coverImg.set_from_pixbuf(pixbuf);
                }
            }));

        if (media.get_title() != null) {
            this.titleLabel.set_label(media.get_title());
        } else {
            let url = media.get_url(),
                file = GLib.File.new_for_path(url),
                basename = file.get_basename(),
                toShow = GLib.Uri.unescape_string(basename, null);

            this.titleLabel.set_label(toShow);
        }

        if (media.get_artist() != null)
            this.artistLabel.set_label(media.get_artist());
        else
            this.artistLabel.set_label("Unknown artist");

        let url = media.get_url();
        if (url != this.player.current_uri)
            this.player.uri = url;

        // Store next available url
        // (not really useful because we can't connect to about-to-finish, but still)
        let nextTrack = this._getNextTrack();

        if (nextTrack) {
            let nextMedia = this.playlist.get_value(this.currentTrack, this.playlistField);
            this.player.nextUrl = nextMedia.get_url();
        } else {
            this.player.nextUrl = null;
        }

        this.emit("playlist-item-changed", this.playlist, this.currentTrack);
        this.emit('current-changed');
    },

    play: function() {
        if (this.player.get_state(1)[1] != Gst.State.PAUSED)
            this.stop();

        this.load(this.playlist.get_value(this.currentTrack, this.playlistField));

        this.player.set_state(Gst.State.PLAYING);
        this._updatePositionCallback();
        if (!this.timeout)
            this.timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, Lang.bind(this, this._updatePositionCallback));
    },

    pause: function () {
        if (this.timeout) {
            GLib.source_remove(this.timeout);
            this.timeout = 0;
        }

        this.player.set_state(Gst.State.PAUSED);
    },

    stop: function() {
        if (this.timeout) {
            GLib.source_remove(this.timeout);
            this.timeout = 0;
        }

        this.player.set_state(Gst.State.NULL);
        this.emit('playing-changed');
    },

    playNext: function() {
        this.currentTrack = this._getNextTrack();

        if (this.currentTrack)
            this.play();
        else
            this.stop();
    },

    playPrevious: function() {
        this.currentTrack = this._getPreviousTrack();

        if (this.currentTrack)
            this.play();
        else
            this.stop();
    },

    setPlaylist: function (type, id, model, iter, field) {
        this.stop();

        this.playlist = model;
        this.playlistType = type;
        this.playlistId = id;
        this.currentTrack = iter;
        this.playlistField = field;
        this.emit('current-changed');
    },

    runningPlaylist: function (type, id, force){
        if (type == this.playlistType && id == this.playlistId)
            return this.playlist;
        else
            return null;
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
        this.repeatBtnImage = this._ui.get_object('playlistRepeat');

        if (Gtk.Settings.get_default().gtk_application_prefer_dark_theme)
            var color = new Gdk.Color({red:65535,green:65535,blue:65535});
        else
            var color = new Gdk.Color({red:0,green:0,blue:0});
        this._playImage.modify_fg(Gtk.StateType.ACTIVE,color);
        this._pauseImage.modify_fg(Gtk.StateType.ACTIVE,color);

        this._syncRepeatImage();

        this.prevBtn.connect("clicked", Lang.bind(this, this._onPrevBtnClicked));
        this.playBtn.connect("clicked", Lang.bind(this, this._onPlayBtnClicked));
        this.nextBtn.connect("clicked", Lang.bind(this, this._onNextBtnClicked));
        this.progressScale.connect("button-press-event", Lang.bind(this,
            function() {
                this._lastState = this.player.get_state(1)[1];
                this.player.set_state(Gst.State.PAUSED);
                if (this.timeout) {
                    GLib.source_remove(this.timeout);
                    this.timeout = null;
                }
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
        if (this.playing)
            this.pause();
        else
            this.play();
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

    _syncRepeatImage: function() {
        let icon;

        switch (this.repeat) {
        case RepeatType.NONE:
            icon = 'media-playlist-consecutive-symbolic';
            break;

        case RepeatType.SHUFFLE:
            icon = 'media-playlist-shuffle-symbolic';
            break;

        case RepeatType.ALL:
            icon = 'media-playlist-repeat-symbolic';
            break;

        case RepeatType.SONG:
            icon = 'media-playlist-repeat-song-symbolic';
            break;
        }

        this.repeatBtnImage.icon_name = icon;
    },

    onProgressScaleChangeValue: function(scroll) {
        var seconds = scroll.get_value() / 60;
        if (seconds != this.duration) {
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
