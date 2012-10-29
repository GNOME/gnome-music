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

private class Music.PlaylistSongs {
    public Gtk.Widget actor { get { return alignment; } }

    private Music.Playlist playlist;

    private Gtk.Alignment alignment;
    private Gtk.Grid grid;

    private int current_song = 0;

    public PlaylistSongs (Music.Playlist playlist) {
        this.playlist = playlist;
        this.playlist.changed.connect (on_playlist_changed);
        this.playlist.song_selected.connect (on_playlist_song_selected);

        alignment = new Gtk.Alignment ((float)0.5, (float)0.5, 0, 0);
        alignment.show_all ();
    }

    private void on_playlist_changed () {
        clear_grid ();

        foreach (Grl.Media media in playlist) {
            var image = new Gtk.Image.from_icon_name ("media-playback-start-symbolic", IconSize.BUTTON);
            image.hide();

            var title = new Music.ClickableLabel (media.get_title());
            title.set_alignment (0, (float)0.5);
            title.clicked.connect (() => {
                on_title_clicked (media);
            });

            var duration = media.get_duration ();
            var length = new Gtk.Label (Music.seconds_to_string (duration));
            length.set_alignment (1, (float)0.5);
            length.get_style_context ().add_class ("dim-label");

            grid.attach_next_to (image, null, Gtk.PositionType.BOTTOM, 1, 1);
            grid.attach_next_to (title, image, Gtk.PositionType.RIGHT, 1, 1);
            grid.attach_next_to (length, title, Gtk.PositionType.RIGHT, 1, 1);

            image.hide();
            title.show();
            length.show();
        }
    }
    public void clear_grid () {
        var child = alignment.get_child ();
        if (child != null) {
            alignment.remove (child);
        }
        
        grid = new Gtk.Grid ();
        grid.set_column_spacing (10);
        grid.set_row_spacing (10);
        alignment.add (grid);
        grid.show_all ();
    }

    private void on_title_clicked (Grl.Media media) {
        playlist.select (media);
    }

    private void on_playlist_song_selected (Grl.Media media, int index) {
        debug (current_song.to_string());
        var image = grid.get_child_at(0, current_song);
        if (image != null) {
            image.hide();
        }

        image = grid.get_child_at(0, index);
        image.show();

        current_song = index;
    }
}
