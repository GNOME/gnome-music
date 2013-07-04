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
const GstAudio = imports.gi.GstAudio;
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

const PropertiesIface = <interface name="org.freedesktop.DBus.Properties">
<signal name="PropertiesChanged">
  <arg type="s" direction="out" />
  <arg type="a{sv}" direction="out" />
  <arg type="as" direction="out" />
</signal>
</interface>;
const PropertiesProxy = Gio.DBusProxy.makeProxyWrapper(PropertiesIface);

const MediaPlayer2PlayerIface = <interface name="org.mpris.MediaPlayer2.Player">
  <method name="Next"/>
  <method name="Previous"/>
  <method name="Pause"/>
  <method name="PlayPause"/>
  <method name="Stop"/>
  <method name="Play"/>
  <method name="Seek">
    <arg direction="in" name="Offset" type="x"/>
  </method>
  <method name="SetPosition">
    <arg direction="in" name="TrackId" type="o"/>
    <arg direction="in" name="Position" type="x"/>
  </method>
  <method name="OpenUri">
    <arg direction="in" name="Uri" type="s"/>
  </method>
  <signal name="Seeked">
    <arg name="Position" type="x"/>
  </signal>
  <property name="PlaybackStatus" type="s" access="read"/>
  <property name="LoopStatus" type="s" access="readwrite"/>
  <property name="Rate" type="d" access="readwrite"/>
  <property name="Shuffle" type="b" access="readwrite"/>
  <property name="Metadata" type="a{sv}" access="read"/>
  <property name="Volume" type="d" access="readwrite"/>
  <property name="Position" type="x" access="read"/>
  <property name="MinimumRate" type="d" access="read"/>
  <property name="MaximumRate" type="d" access="read"/>
  <property name="CanGoNext" type="b" access="read"/>
  <property name="CanGoPrevious" type="b" access="read"/>
  <property name="CanPlay" type="b" access="read"/>
  <property name="CanPause" type="b" access="read"/>
  <property name="CanSeek" type="b" access="read"/>
  <property name="CanControl" type="b" access="read"/>
</interface>;

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

        this._dbusImpl = Gio.DBusExportedObject.wrapJSObject(MediaPlayer2PlayerIface, this);
        this._dbusImpl.export(Gio.DBus.session, '/org/mpris/MediaPlayer2');

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
            nextTrack = this.playlist.get_iter_first()[1];
            let rows = this.playlist.iter_n_children(null);
            let random = Math.floor(Math.random() * rows);
            for(let i=0; i<random; i++){
                this.playlist.iter_next(nextTrack);
            }
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
                previousTrack = this._getIterLast();
            break;

        case RepeatType.NONE:
            previousTrack = currentTrack.copy();
            previousTrack = this.playlist.iter_previous(previousTrack) ? previousTrack : null;
            break;

        case RepeatType.SHUFFLE:
            previousTrack = this.playlist.get_iter_first()[1];
            let rows = this.playlist.iter_n_children(null);
            let random = Math.floor(Math.random() * rows);
            for(let i=0; i<random; i++){
                this.playlist.iter_next(previousTrack);
            }
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
        let hasNext = this._hasNext()
        let hasPrevious = this._hasPrevious()

        this.nextBtn.sensitive = hasNext;
        this.prevBtn.sensitive = hasPrevious;

        this._dbusImpl.emit_property_changed('CanGoNext', GLib.Variant.new('b', hasNext));
        this._dbusImpl.emit_property_changed('CanGoPrevious', GLib.Variant.new('b', hasPrevious));
    },

    setPlaying: function(bool) {
        this.eventBox.show();

        if (bool)
            this.play();
        else
            this.pause();

        let media = this.playlist.get_value(this.currentTrack, this.playlistField);
        this.playBtn.set_image(this._pauseImage);
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

        this.titleLabel.set_label(AlbumArtCache.getMediaTitle(media));

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

        this._dbusImpl.emit_property_changed('Metadata', GLib.Variant.new('a{sv}', this.Metadata));
        this._dbusImpl.emit_property_changed('CanPlay', GLib.Variant.new('b', true));
        this._dbusImpl.emit_property_changed('CanPause', GLib.Variant.new('b', true));

        this.emit("playlist-item-changed", this.playlist, this.currentTrack);
        this.emit('current-changed');
    },

    play: function() {
        if (this.playlist == null)
            return;

        if (this.player.get_state(1)[1] != Gst.State.PAUSED)
            this.stop();

        this.load(this.playlist.get_value(this.currentTrack, this.playlistField));

        this.player.set_state(Gst.State.PLAYING);
        this._updatePositionCallback();
        if (!this.timeout)
            this.timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, Lang.bind(this, this._updatePositionCallback));

        this._dbusImpl.emit_property_changed('PlaybackStatus', GLib.Variant.new('s', 'Playing'));
    },

    pause: function () {
        if (this.timeout) {
            GLib.source_remove(this.timeout);
            this.timeout = 0;
        }

        this.player.set_state(Gst.State.PAUSED);
        this._dbusImpl.emit_property_changed('PlaybackStatus', GLib.Variant.new('s', 'Paused'));
    },

    stop: function() {
        if (this.timeout) {
            GLib.source_remove(this.timeout);
            this.timeout = 0;
        }

        this.player.set_state(Gst.State.NULL);
        this._dbusImpl.emit_property_changed('PlaybackStatus', GLib.Variant.new('s', 'Stopped'));
        this.emit('playing-changed');
    },

    playNext: function() {
        if (this.playlist == null)
            return;

        if (!this.nextBtn.sensitive)
            return;

        this.stop();
        this.currentTrack = this._getNextTrack();

        if (this.currentTrack)
            this.play();
    },

    playPrevious: function() {
        if (this.playlist == null)
            return;

        if (!this.prevBtn.sensitive)
            return;

        this.stop();
        this.currentTrack = this._getPreviousTrack();

        if (this.currentTrack)
            this.play();
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
        this._dbusImpl.emit_property_changed('LoopStatus', GLib.Variant.new('s', this.LoopStatus));
        this._dbusImpl.emit_property_changed('Shuffle', GLib.Variant.new('b', this.Shuffle));
    },

    onProgressScaleChangeValue: function(scroll) {
        var seconds = scroll.get_value() / 60;
        if (seconds != this.duration) {
            this.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, seconds * 1000000000);
            this._dbusImpl.emit_signal('Seeked', GLib.Variant.new('(x)', [seconds * 1000000]));
        } else {
            let duration = this.player.query_duration(Gst.Format.TIME, null);
            if (duration) {
                // Rewind a second back before the track end
                this.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, duration[1]-1000000000);
                this._dbusImpl.emit_signal('Seeked', GLib.Variant.new('(x)', [(duration[1]-1000000000)/1000]));
            }
        }
        return true;
     },

    /* MPRIS */

    Next: function() {
        this.playNext();
    },

    Previous: function() {
        this.playPrevious();
    },

    Pause: function() {
        this.setPlaying(false);
    },

    PlayPause: function() {
        if (this.player.get_state(1)[1] == Gst.State.PLAYING){
            this.setPlaying(false);
        } else {
            this.setPlaying(true);
        }
    },

    Play: function() {
        this.setPlaying(true);
    },

    Stop: function() {
        this.progressScale.set_value(0);
        this.progressScale.sensitive = false;
        this.playBtn.set_image(this._playImage);
        this.stop();
    },

    SeekAsync: function(params, invocation) {
        let [offset] = params;

        let duration = this.player.query_duration(Gst.Format.TIME, null);
        if (!duration)
            return;

        if (offset < 0) {
            offset = 0;
        }

        if (duration[1] >= offset * 1000) {
            this.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, offset * 1000);
            this._dbusImpl.emit_signal('Seeked', GLib.Variant.new('(x)', [offset]));
        } else {
            this.playNext();
        }
    },

    SetPositionAsync: function(params, invocation) {
        let [trackId, position] = params;

        if (this.currentTrack == null)
            return;

        let media = this.playlist.get_value(this.currentTrack, this.playlistField);
        if (trackId != '/org/mpris/MediaPlayer2/Track/' + media.get_id())
            return;

        let duration = this.player.query_duration(Gst.Format.TIME, null);
        if (duration && position >= 0 && duration[1] >= position * 1000) {
            this.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, position * 1000);
            this._dbusImpl.emit_signal('Seeked', GLib.Variant.new('(x)', [position]));
        }
    },

    OpenUriAsync: function(params, invocation) {
        let [uri] = params;
    },

    get PlaybackStatus() {
        let [ok, state, pending] = this.player.get_state(0);
        if (ok == Gst.StateChangeReturn.ASYNC)
            state = pending;
        else if (ok != Gst.StateChangeReturn.SUCCESS)
            return 'Stopped';

        if (state == Gst.State.PLAYING) {
            return 'Playing';
        } else if (state == Gst.State.PAUSED) {
            return 'Paused';
        } else {
            return 'Stopped';
        }
    },

    get LoopStatus() {
        if (this.repeat == RepeatType.NONE) {
            return 'None';
        } else if (this.repeat == RepeatType.SONG) {
            return 'Track';
        } else {
            return 'Playlist';
        }
    },

    set LoopStatus(mode) {
        if (mode == 'None') {
            this.repeat = RepeatType.NONE;
        } else if (mode == 'Track') {
            this.repeat = RepeatType.SONG;
        } else if (mode == 'Playlist') {
            this.repeat = RepeatType.ALL;
        }
        this._syncRepeatImage();
    },

    get Rate() {
        return 1.0;
    },

    set Rate(rate) {
    },

    get Shuffle() {
        return this.repeat == RepeatType.SHUFFLE;
    },

    set Shuffle(enable) {
        if (enable && this.repeat != RepeatType.SHUFFLE) {
            this.repeat = RepeatType.SHUFFLE;
        } else if (!enable && this.repeat == RepeatType.SHUFFLE) {
            this.repeat = RepeatType.NONE;
        }
        this._syncRepeatImage();
    },

    get Metadata() {
        if (this.currentTrack == null)
            return {};

        let media = this.playlist.get_value(this.currentTrack, this.playlistField);
        let metadata = {
            'mpris:trackid': GLib.Variant.new('s', '/org/mpris/MediaPlayer2/Track/' + media.get_id()),
            'xesam:url': GLib.Variant.new('s', media.get_url()),
            'mpris:length': GLib.Variant.new('x', media.get_duration()*1000000),
            'xesam:trackNumber': GLib.Variant.new('i', media.get_track_number()),
            'xesam:useCount': GLib.Variant.new('i', media.get_play_count()),
            'xesam:userRating': GLib.Variant.new('d', media.get_rating()),
        };

        let title = media.get_title();
        if (title) {
            metadata['xesam:title'] = GLib.Variant.new('s', title);
        }

        let album = media.get_album();
        if (album) {
            metadata['xesam:album'] = GLib.Variant.new('s', album);
        }

        let artist = media.get_artist();
        if (artist) {
            metadata['xesam:artist'] = GLib.Variant.new('as', [artist]);
            metadata['xesam:albumArtist'] = GLib.Variant.new('as', [artist]);
        }

        let genre = media.get_genre();
        if (genre) {
            metadata['xesam:genre'] = GLib.Variant.new('as', [genre]);
        }

        let last_played = media.get_last_played();
        if (last_played) {
            metadata['xesam:lastUsed'] = GLib.Variant.new('s', last_played);
        }

        let thumbnail = media.get_thumbnail();
        if (thumbnail) {
            metadata['mpris:artUrl'] = GLib.Variant.new('s', thumbnail);
        }

        return metadata;
    },

    get Volume() {
        return this.player.get_volume(GstAudio.StreamVolumeFormat.LINEAR);
    },

    set Volume(rate) {
        this.player.set_volume(GstAudio.StreamVolumeFormat.LINEAR, rate);
        this._dbusImpl.emit_property_changed('Volume', GLib.Variant.new('d', rate));
    },

    get Position() {
        return this.player.query_position(Gst.Format.TIME, null)[1]/1000;
    },

    get MinimumRate() {
        return 1.0;
    },

    get MaximumRate() {
        return 1.0;
    },

    get CanGoNext() {
        return this._hasNext();
    },

    get CanGoPrevious() {
        return this._hasPrevious();
    },

    get CanPlay() {
        return this.currentTrack != null;
    },

    get CanPause() {
        return this.currentTrack != null;
    },

    get CanSeek() {
        return true;
    },

    get CanControl() {
        return true;
    },

});
Signals.addSignalMethods(Player.prototype);

const SelectionToolbar = new Lang.Class({
        Name: 'SelectionToolbar',
        _init: function() {
            this._ui = new Gtk.Builder();
            this._ui.add_from_resource('/org/gnome/music/SelectionToolbar.ui');
            this.eventbox = this._ui.get_object("eventbox1");
            this._add_to_playlist_button = this._ui.get_object("button1");
            this.eventbox.set_visible(false);
        }
});
Signals.addSignalMethods(SelectionToolbar.prototype);
