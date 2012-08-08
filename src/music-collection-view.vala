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

private class Music.CollectionView: Music.UI {
    public Gtk.Widget actor { get { return scrolled_window; } }

    private Music.FilteredList model;

    private Gtk.ScrolledWindow scrolled_window;
    private Gtk.IconView icon_view;

    public CollectionView () {
        setup_view ();
    }

    private void setup_view () {
        model = new Music.FilteredList (); 

        icon_view = new Gtk.IconView.with_model (model);
        icon_view.get_style_context ().add_class ("music-bg");
        icon_view.item_width = 185;
        icon_view.column_spacing = 20;
        icon_view.margin = 16;
//        icon_view_activate_on_single_click (icon_view, true);
        icon_view.set_selection_mode (Gtk.SelectionMode.NONE);
/*
        var pixbuf_renderer = new Gtk.CellRendererPixbuf ();
        pixbuf_renderer.xalign = 0.5f;
        pixbuf_renderer.yalign = 0.5f;
        icon_view.pack_start (pixbuf_renderer, false);
        icon_view.add_attribute (pixbuf_renderer, "pixbuf", MusicListStoreColumn.COVER);
*/

        var text_renderer = new Gtk.CellRendererText ();
        text_renderer.xalign = 0.5f;
        text_renderer.foreground = "white";
        icon_view.pack_start (text_renderer, false);
        icon_view.add_attribute(text_renderer, "text", MusicListStoreColumn.TITLE);

        scrolled_window = new Gtk.ScrolledWindow (null, null);
        // TODO: this should be set, but doesn't resize correctly the gtkactor..
        //        scrolled_window.hscrollbar_policy = Gtk.PolicyType.NEVER;
        scrolled_window.add (icon_view);
        scrolled_window.show_all ();
    }

    public override void ui_state_changed () {
        /*
        switch (ui_state) {
        */
    }
}
