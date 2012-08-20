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
using Gee;

private class Music.PlaylistView {
    public Gtk.Widget actor { get { return scrolled_window; } }

    private Gtk.ScrolledWindow scrolled_window;
    private Music.AlbumInfoBox album_info_box;

    public PlaylistView () {
        setup_view ();
    }

    private void setup_view () {
        var layout = new Gtk.Box (Orientation.HORIZONTAL, 0);
        layout.set_homogeneous (false);

        /* Album Info Box */
        album_info_box = new Music.AlbumInfoBox ();
        layout.pack_start (album_info_box.actor, false, false);

        layout.show();

        scrolled_window = new Gtk.ScrolledWindow (null, null);
        scrolled_window.hscrollbar_policy = Gtk.PolicyType.NEVER;
        scrolled_window.vscrollbar_policy = Gtk.PolicyType.AUTOMATIC;
        scrolled_window.add_with_viewport (layout);

        scrolled_window.show ();
    }

    public void load (Grl.Media media) {
        album_info_box.load (media);
    }
}
