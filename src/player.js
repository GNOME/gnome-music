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

//pkg.initSubmodule('libgd');

const Mainloop = imports.mainloop;
const AlbumArtCache = imports.albumArtCache;

const ART_SIZE = 64;

const PlayPauseButton = new Lang.Class({
    Name: "PlayPauseButton",
    Extends: Gtk.ToggleButton,

    _init: function() {
        this.play_image = Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.MENU);
        this.pause_image = Gtk.Image.new_from_icon_name("media-playback-pause-symbolic", Gtk.IconSize.MENU);

        this.parent();
        this.set_image(this.play_image);
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
        this.playlist = [];
        this.currentTrack = 0;
        this.cache = AlbumArtCache.AlbumArtCache.getDefault();

        Gst.init(null, 0);
        this.player = Gst.ElementFactory.make("playbin", "player");
        this.player.connect("about-to-finish", Lang.bind(this,
            function() {
                let newCurrentTrack = parseInt(this.currentTrack) + 1;
                if (newCurrentTrack < this.playlist.length) {
                    this.currentTrack = newCurrentTrack;
                    this.load(this.playlist[this.currentTrack]);
                }
                return true;
            }));
        this.bus = this.player.get_bus();
        this.bus.add_signal_watch()
        this.bus.connect("message", Lang.bind(this,
            function(bus, message) {
            if (message.type == Gst.MessageType.ERROR) {
                let uri = this.playlist[this.currentTrack].get_url();
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

        // FIXME: site contains the album's name. It's obviously a hack to remove
        pixbuf = this.cache.lookup (ART_SIZE, media.get_artist (), media.get_site ());
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
    },

    play: function() {
        this.stop();
        this.load(this.playlist[this.currentTrack]);
        this.player.set_state(Gst.State.PLAYING);
        this.timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 10, Lang.bind(this, this._updatePositionCallback));
    },

    pause: function () {
        this.player.set_state(Gst.State.PAUSED);
    },

    stop: function() {
        this.play_btn.set_active(false);
        this.player.set_state(Gst.State.NULL);
        if (this.timeout) {
            GLib.source_remove(this.timeout);
        }
    },

    appendToPlaylist: function (track) {
        this.playlist.push(track);
    },

    playNext: function () {
        let newCurrentTrack = parseInt(this.currentTrack) + 1;
        if (newCurrentTrack < this.playlist.length) {
            this.currentTrack = newCurrentTrack;
            this.play_btn.set_active(true);
        }
    },

    playPrevious: function () {
        let newCurrentTrack = parseInt(this.currentTrack) - 1;
        if (newCurrentTrack >= 0) {
            this.currentTrack = newCurrentTrack;
            this.play_btn.set_active(true);
        }
    },

    setPlaylist: function (playlist) {
        this.playlist = playlist;
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
            next_btn,
            prev_btn,
            rate_btn,
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

        prev_btn = new Gtk.Button();
        prev_btn.set_size_request(35, -1);
        prev_btn.set_image(Gtk.Image.new_from_icon_name("media-skip-backward-symbolic", Gtk.IconSize.MENU));
        prev_btn.connect("clicked", Lang.bind(this, this._onPrevBtnClicked));
        toolbar_start.pack_start(prev_btn, false, false, 0);

        this.play_btn = new PlayPauseButton();
        this.play_btn.set_size_request(55, -1);
        this.play_btn.connect("toggled", Lang.bind(this, this._onPlayBtnToggled));
        toolbar_start.pack_start(this.play_btn, false, false, 0);

        next_btn = new Gtk.Button();
        next_btn.set_size_request(35, -1);
        next_btn.set_image(Gtk.Image.new_from_icon_name("media-skip-forward-symbolic", Gtk.IconSize.MENU));
        next_btn.connect("clicked", Lang.bind(this, this._onNextBtnClicked));
        toolbar_start.pack_start(next_btn, false, false, 0);
        this.box.pack_start(toolbar_start, false, false, 3)

        this.progress_scale = new Gtk.Scale({
            orientation: Gtk.Orientation.HORIZONTAL,
            sensitive: false
        });
        this.progress_scale.set_draw_value(false);
        this._setDuration(1);
        this.progress_scale.connect("change_value", Lang.bind(this, this.onProgressScaleChangeValue));

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

        this.toolbar_song_info.pack_start(databox, false, false, 0);

        toolbar_center.pack_start(this.toolbar_song_info, false, false, 3);
        toolbar_center.pack_start(this.progress_scale, true, true, 0);
        toolbar_center.pack_start(new Gtk.Label({}), false, false, 3);

        this.song_playback_time_lbl = new Gtk.Label({
            label:              "00:00"
        });
        toolbar_center.pack_start(this.song_playback_time_lbl, false, false, 0);
        label = new Gtk.Label({
            label:              "/"
        });
        toolbar_center.pack_start(label, false, false, 0);
        this.song_total_time_lbl = new Gtk.Label({
            label:              "00:00"
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

        /*
        rate_btn = new Gtk.Button ();
        rate_btn.set_image(Gtk.Image.new_from_icon_name("bookmark-new-symbolic", Gtk.IconSize.BUTTON));
        toolbar_end.pack_end(rate_btn, false, false, 0);

        this.shuffle_btn = new Gtk.ToggleButton ();
        this.shuffle_btn.set_image (Gtk.Image.new_from_icon_name("media-playlist-shuffle-symbolic", Gtk.IconSize.BUTTON));
        this.shuffle_btn.connect("clicked", Lang.bind(this, this._onShuffleBtnClicked));
        toolbar_end.pack_end(this.shuffle_btn, false, false, 0);
        */

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
        if (btn.get_active()) {
            this.play();
        }

        else {
            this.pause();
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
        this.progress_scale.set_range(0.0, duration*60);
        this.progress_scale.set_value(0.0);
    },

    _updatePositionCallback: function() {
        var format = Gst.Format.TIME,
            position = 0,
            seconds;

        position = this.player.query_position(format, null);
        seconds = Math.floor(position[1] / Gst.SECOND);
        this.progress_scale.set_value(seconds*60);

        this.song_playback_time_lbl.set_label(this.seconds_to_string(seconds));

        return true;
    },

    onProgressScaleChangeValue: function(scroll, other, newValue) {
        var seconds = newValue / 60;
        log('onProgressScaleChangeValue ' + seconds)
        this.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, seconds * 1000000000);

        return false;
     }
});
