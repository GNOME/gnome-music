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

private class Music.Searchbar {
    public Gtk.Widget actor { get { return eventbox; } }

    private Gtk.EventBox eventbox;
    private Gd.TaggedEntry search_entry;

    public Searchbar () {
        setup_ui ();
    }

    private void setup_ui () {
        eventbox = new Gtk.EventBox ();
        eventbox.margin_top = 5;
        eventbox.margin_bottom = 5;
        //eventbox.get_style_context ().add_class ("music-topbar");

        var container = new Gd.MarginContainer ();
        container.min_margin = 64;
        container.max_margin = 128;
        eventbox.add (container);

        var box = new Gtk.Box (Orientation.HORIZONTAL, 0);
        container.add (box);

        search_entry = new Gd.TaggedEntry();
        search_entry.hexpand = true;
        search_entry.key_press_event.connect (on_search_entry_key_pressed);
        search_entry.changed.connect (on_search_entry_changed);
        search_entry.tag_clicked.connect (on_search_entry_tag_clicked);
        box.add (search_entry);

        eventbox.show_all();
    }

    private bool on_search_entry_key_pressed (Gdk.EventKey e) {
        var keyval = e.keyval;

        if (keyval == Gdk.Key.Escape) {
            App.app.search_mode = false;
            return true;
        }

        return false;
    }

    private void on_search_entry_changed () {
        debug ("2");
    }

    private void on_search_entry_tag_clicked () {
        debug ("3");
    }

    public void show () {
        actor.show();
    }

    public void hide () {
        actor.hide();
    }

    public void grab_focus () {
        search_entry.grab_focus ();
    }
}