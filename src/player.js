/*
 * Copyright (c) 2013 Eslam Mostafa.
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
const AlbumArtCache = imports.album_art_cache;

const ART_SIZE = 240;

const PlayPauseButton = new Lang.Class({
    Name: "PlayPauseButton",
    Extends: Gtk.ToggleButton,

    _init: function() {
        this.play_image = Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON);
        this.pause_image = Gtk.Image.new_from_icon_name("media-playback-pause-symbolic", Gtk.IconSize.BUTTON);

        this.parent();
        this.set_image(this.play_image);
    },
});

const Player = new Lang.Class({
    Name: "Player",
    //Extends: GLib.Object,

    _init: function(playlist) {
        this.playlist = playlist;
        this.cache = AlbumArtCache.AlbumArtCache.getDefault();

        //Gst.init(null, 0);
        //this.source = new Gst.ElementFactory.make("audiotestrc", "source");
        //this.sink = new Gst.ElementFactory.make("autoaudiosink", "output");
        //this.playbin = new Gst.ElementFactory.make("playbin", "playbin");
        //this.bus = this.playbin.get_bus();

        this._setup_view();
    },

    _setup_view: function() {
        var alignment,
            artist_lbl,
            box,
            databox,
            label,
            next_btn,
            play_btn,
            prev_btn,
            rate_btn,
            toolbar_center,
            toolbar_end,
            toolbar_start,
            toolbar_song_info;

        this.eventbox = new Gtk.Box();
        this.eventbox.set_spacing(9)
        this.eventbox.set_border_width(9)
        toolbar_start = new Gtk.Box({
            orientation: Gtk.Orientation.HORIZONTAL,
            spacing: 0
        });
        toolbar_start.get_style_context().add_class(Gtk.STYLE_CLASS_LINKED);

        prev_btn = new Gtk.Button();
        prev_btn.set_image(Gtk.Image.new_from_icon_name("media-skip-backward-symbolic", Gtk.IconSize.BUTTON));
        prev_btn.connect("clicked", Lang.bind(this, this._onPrevBtnClicked));
        toolbar_start.pack_start(prev_btn, false, false, 0);

        play_btn = new PlayPauseButton();
        play_btn.connect("toggled", Lang.bind(this, this._onPlayBtnToggled));
        toolbar_start.pack_start(play_btn, false, false, 0);

        next_btn = new Gtk.Button();
        next_btn.set_image(Gtk.Image.new_from_icon_name("media-skip-forward-symbolic", Gtk.IconSize.BUTTON));
        next_btn.connect("clicked", Lang.bind(this, this._onNextBtnClicked));
        toolbar_start.pack_start(next_btn, false, false, 0);
        
        this.eventbox.pack_start(toolbar_start, false, false, 3)

        toolbar_song_info = new Gtk.Box({
            orientation: Gtk.Orientation.HORIZONTAL,
            spacing: 0
        });

        this.cover_img = new Gtk.Image();
        toolbar_song_info.pack_start(this.cover_img, false, false, 0);

        databox = new Gtk.Box({
            orientation: Gtk.Orientation.VERTICAL,
            spacing: 0
        });
        toolbar_song_info.pack_start(databox, false, false, 0);
        toolbar_start.pack_start(toolbar_song_info, false, false, 9)


        this.title_lbl = new Gtk.Label({
            label: ""
        });
        databox.pack_start(this.title_lbl, false, false, 0);

        artist_lbl = new Gtk.Label({
            label: ""
        });
        artist_lbl.get_style_context().add_class("dim-label");
        databox.pack_start(artist_lbl, false, false, 0);

        toolbar_center = new Gtk.Box({
            orientation: Gtk.Orientation.HORIZONTAL,
            spacing: 0
        });

        this.progress_scale = new Gtk.Scale({
            orientation: Gtk.Orientation.HORIZONTAL,
            sensitive: false
        });
        this.progress_scale.set_draw_value(false);
        this._setDuration(1);
        this.progress_scale.connect("change_value", Lang.bind(this, this.onProgressScaleChangeValue));
        toolbar_center.pack_start(this.progress_scale, true, true, 0);

        /*this.song_playback_time_lbl = new Gtk.Label({
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
        */
        this.eventbox.pack_start(toolbar_center, true, true, 0)

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
        this.eventbox.pack_end(toolbar_end, false, false, 3);

        rate_btn = new Gtk.Button ();
        rate_btn.set_image(Gtk.Image.new_from_icon_name("bookmark-new-symbolic", Gtk.IconSize.BUTTON));
        toolbar_end.pack_end(rate_btn, false, false, 0);

        this.shuffle_btn = new Gtk.ToggleButton ();
        this.shuffle_btn.set_image (Gtk.Image.new_from_icon_name("media-playlist-shuffle-symbolic", Gtk.IconSize.BUTTON));
        this.shuffle_btn.connect("clicked", Lang.bind(this, this._onShuffleBtnClicked));
        toolbar_end.pack_end(this.shuffle_btn, false, false, 0);

        this.eventbox.show_all();

    },

    load: function(media) {
        var pixbuf,
            uri;

        this._setDuration(media.get_duration());
        this.song_total_time_lbl.set_label(this.seconds_to_string (media.get_duration()));
        this.progress_scale.sensitive = true;

        // FIXME: site contains the album's name. It's obviously a hack to remove
        pixbuf = this.cache.lookup (ART_SIZE, media.get_author (), media.get_site ());
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

        artist_lbl.set_label(media.get_author());

        uri = media.get_url();
    },

    uri: function() {
    },

    _onPlayBtnToggled: function(btn) {
        if (btn.get_active()) {
            //this.beginPlayback();
        }

        else {
            //this.pausePlayback();
        }
    },

    _onNextBtnClicked: function(btn) {
        this._needNext();
    },

    _onPrevBtnClicked: function(btn) {
        this._needPrevious();
    },

    _needNext: function() {
    },

    _needPrevious: function() {
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

    _updatePosition: function(update) {
        if (update) {
            if (this.position_update_timeout == 0) {
                Timeout.add_seconds(1, Lang.bind(this, this.update_position_cb));
            }
        }

        else {
            if (this.position_update_timeout != 0) {
                this.source.remove(position_update_timeout);
                this.position_update_timeout = 0;
            }
        }
    },

    _updatePositionCallback: function() {
        var format = Gst.Format.TIME,
            duration = 0,
            seconds;

        this.playbin.query_position(format, duration);
        this.progress_scale.set_value(duration);

        seconds = duration / Gst.SECOND;

        this.song_playback_time_lbl.set_label(this.seconds_to_string(seconds));

        return true;
    },

    onProgressScaleChangeValue: function(scroll, newValue) {
        this.playbin.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, newValue);

        return false;
     }
});
