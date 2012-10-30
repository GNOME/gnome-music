/*
 * Copyright (C) 2012 Cesar Garcia Tapia <tapia@openshine.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

using Gtk;


internal class Music.PlayPauseButton : ToggleButton {
    public Image play_image;
    public Image pause_image;

    public PlayPauseButton () {
        Object ();
        
        play_image = new Gtk.Image.from_icon_name ("media-playback-start-symbolic", IconSize.BUTTON);
        pause_image = new Gtk.Image.from_icon_name ("media-playback-pause-symbolic", IconSize.BUTTON);
        this.set_image (play_image);
    }

    public override void toggled () {
        if (this.get_active ()) {
            this.set_image (pause_image);
        } else {
            this.set_image (play_image);
        }
    }
}

private class Music.Player: GLib.Object {
    public Gtk.Widget actor { get { return eventbox; } }

    public signal void need_next ();
    public signal void need_previous ();

    private Gtk.EventBox eventbox;

    private PlayPauseButton play_btn;
    private Gtk.Button prev_btn;
    private Gtk.Button next_btn;
    private Gtk.Button rate_btn;

    private Gtk.Image cover_img;
    private Gtk.Label title_lbl;
    private Gtk.Label artist_lbl;
    private Gtk.Scale progress_scale;
    private Gtk.Label song_playback_time_lbl;
    private Gtk.Label song_total_time_lbl;

    private Gtk.ToggleButton shuffle_btn;

    private GLib.Settings settings;
    private dynamic Gst.Element playbin;

    private bool shuffle;

    private Music.AlbumArtCache cache;
    private int ART_SIZE = 42;

    private uint position_update_timeout;

    public Player () {
        Object ();

        cache = AlbumArtCache.get_default ();

        settings = new GLib.Settings ("org.gnome.Music");
        /*
        settings.bind ("shuffle",
                       this,
                       "shuffle",
                       SettingsBindFlags.DEFAULT);
        */

        playbin = Gst.ElementFactory.make ("playbin2", null);
        var bus = playbin.get_bus ();
        bus.add_watch ( (bus, message) => {
            switch (message.type) {
                case Gst.MessageType.EOS:
                    need_next ();
                    break;
                case Gst.MessageType.STATE_CHANGED:
                    if (message.src == playbin) {
                        Gst.State old_state, new_state;
                        message.parse_state_changed (out old_state, out new_state, null);
                        if (old_state == Gst.State.PAUSED && new_state == Gst.State.PLAYING) {
                            update_position (true);
                        }
                        else if (old_state == Gst.State.PLAYING && new_state == Gst.State.PAUSED) {
                            update_position (false);
                        }
                    }
                    break;
                default:
                    break;
            }
            
            return true;
        });

        set_ui ();
    }

    private void set_ui () {
        eventbox = new Gtk.EventBox ();
        eventbox.get_style_context ().add_class ("music-player");

        var box = new Gtk.Box (Orientation.HORIZONTAL, 0);
        var alignment = new Gtk.Alignment (0, (float)0.5, 1, 1);
        alignment.set_padding (15, 15, 15, 15);
        alignment.add (box);
        eventbox.add (alignment);

        var toolbar_start = new Gtk.Box (Orientation.HORIZONTAL, 0);
        toolbar_start.get_style_context ().add_class (Gtk.STYLE_CLASS_LINKED);
        var algmnt = new Gtk.Alignment (0, (float)0.5, 0, 0);
        algmnt.add (toolbar_start);
        box.pack_start (algmnt, false, false, 0);

        prev_btn = new Gtk.Button ();
        prev_btn.set_image (new Gtk.Image.from_icon_name ("media-skip-backward-symbolic", IconSize.BUTTON));
        prev_btn.clicked.connect (on_prev_btn_clicked);
        toolbar_start.pack_start (prev_btn, false, false, 0);

        play_btn = new PlayPauseButton ();
        play_btn.toggled.connect (on_play_btn_toggled);
        toolbar_start.pack_start (play_btn, false, false, 0);

        next_btn = new Gtk.Button ();
        next_btn.set_image (new Gtk.Image.from_icon_name ("media-skip-forward-symbolic", IconSize.BUTTON));
        next_btn.clicked.connect (on_next_btn_clicked);
        toolbar_start.pack_start (next_btn, false, false, 0);

        var toolbar_song_info = new Gtk.Box (Orientation.HORIZONTAL, 0);
        algmnt = new Gtk.Alignment (0, (float)0.5, 0, 0);
        algmnt.add (toolbar_song_info);
        box.pack_start (algmnt, false, false, 10);

        cover_img = new Gtk.Image();
        toolbar_song_info.pack_start (cover_img, false, false, 0);

        var databox = new Gtk.Box (Orientation.VERTICAL, 0);
        toolbar_song_info.pack_start (databox, false, false, 0);

        title_lbl = new Gtk.Label (null);
        databox.pack_start (title_lbl, false, false, 0);

        artist_lbl = new Gtk.Label (null);
        artist_lbl.get_style_context ().add_class ("dim-label");
        databox.pack_start (artist_lbl, false, false, 0);

        var toolbar_center = new Gtk.Box (Orientation.HORIZONTAL, 0);
        box.pack_start (toolbar_center, true, true, 10);

        progress_scale = new Gtk.Scale (Orientation.HORIZONTAL, null);
        progress_scale.set_draw_value (false);
        set_duration (1);
        progress_scale.sensitive = false;
        progress_scale.change_value.connect (on_progress_scale_change_value);
        toolbar_center.pack_start (progress_scale);

        song_playback_time_lbl = new Gtk.Label ("00:00");
        toolbar_center.pack_start (song_playback_time_lbl, false, false, 0);
        var label = new Gtk.Label ("/");
        toolbar_center.pack_start (label, false, false, 0);
        song_total_time_lbl = new Gtk.Label ("00:00");
        toolbar_center.pack_start (song_total_time_lbl, false, false, 0);

        var toolbar_end = new Gtk.Box (Orientation.HORIZONTAL, 5);
        alignment = new Gtk.Alignment (1, (float)0.5, 0, 0);
        alignment.add (toolbar_end);
        box.pack_start (alignment, false, false, 10);

        rate_btn = new Gtk.Button ();
        rate_btn.set_image (new Gtk.Image.from_icon_name ("bookmark-new-symbolic", IconSize.BUTTON));
        rate_btn.clicked.connect ((button) => {
        });
        toolbar_end.pack_start (rate_btn, false, false, 0);

        shuffle_btn = new Gtk.ToggleButton ();
        shuffle_btn.set_image (new Gtk.Image.from_icon_name ("media-playlist-shuffle-symbolic", IconSize.BUTTON));
        shuffle_btn.clicked.connect ((button) => {
        });
        toolbar_end.pack_start (shuffle_btn, false, false, 0);

        eventbox.show_all ();
    }

    public void load (Grl.Media media) {
        set_duration (media.get_duration());
        song_total_time_lbl.set_label (seconds_to_string (media.get_duration()));
        progress_scale.sensitive = true;

        // FIXME: site contains the album's name. It's obviously a hack to remove
        var pixbuf = cache.lookup (ART_SIZE, media.get_author (), media.get_site ());
        cover_img.set_from_pixbuf (pixbuf);

        if (media.get_title () != null) {
            title_lbl.set_label (media.get_title ());
        }
        else {
            var url = media.get_url();
            var file = GLib.File.new_for_path (url);
            var basename = file.get_basename ();
            var to_show = GLib.Uri.unescape_string (basename, null);
            title_lbl.set_label (to_show);
        }

        artist_lbl.set_label (media.get_author());

        uri = media.get_url();
    }

    public string uri {
        set {
            var resume = false;
            if (playbin.current_state == Gst.State.PLAYING |
                playbin.current_state == Gst.State.PAUSED) {
                playbin.set_state (Gst.State.READY);
                resume = true;
            }
            playbin.uri = value;
            play_btn.set_active (true);
            if (resume) {
                playbin.set_state (Gst.State.PLAYING);
            }
        }

        get {
            return playbin.uri;
        }
    }

    private void on_play_btn_toggled (Gtk.ToggleButton button) {
        if (button.get_active()) {
            playbin.set_state (Gst.State.PLAYING);
        }
        else {
            playbin.set_state (Gst.State.PAUSED);
        }
    }

    private void on_next_btn_clicked (Gtk.Button button) {
        need_next ();
    }

    private void on_prev_btn_clicked (Gtk.Button button) {
        need_previous ();
    }

    private void set_duration (uint duration) {
        progress_scale.set_range (0.0, (double) (duration * Gst.SECOND));
        progress_scale.set_value (0.0);
    }

    private void update_position (bool update) {
        if (update) {
            if (position_update_timeout == 0) {
                Timeout.add_seconds (1, update_position_cb);
            }
        } else {
            if (position_update_timeout != 0) {
                Source.remove (position_update_timeout);
                position_update_timeout = 0;
            }
        }
    }

    private bool update_position_cb () {
        var format = Gst.Format.TIME;
        int64 duration = 0;

        playbin.query_position (ref format, out duration);
        progress_scale.set_value ((double) duration);
        var seconds = duration / Gst.SECOND;
        song_playback_time_lbl.set_label (seconds_to_string ((int)seconds));

        return true;
    }

    private bool on_progress_scale_change_value (Gtk.ScrollType scroll, double new_value) {
        playbin.seek_simple (Gst.Format.TIME, Gst.SeekFlags.FLUSH|Gst.SeekFlags.KEY_UNIT, (int64)new_value);
        return false;
    }
}
