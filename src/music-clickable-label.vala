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
using Gdk;

private class Music.ClickableLabel : Gtk.EventBox {
	public signal void clicked ();

	private Gtk.Label label;

 	public ClickableLabel (string text) {
 		Gtk.HBox hbox = new Gtk.HBox (false, 0);
 		this.add (hbox);

 		label = new Gtk.Label (text);
 		hbox.add (label);

 		this.enter_notify_event.connect (() => {
 			Gdk.Cursor cursor = new Gdk.Cursor (Gdk.CursorType.HAND2);
 			this.get_window().set_cursor (cursor);
 			return false;
 		});

 		this.leave_notify_event.connect (() => {
 			Gdk.Cursor cursor = new Gdk.Cursor (Gdk.CursorType.ARROW);
 			this.get_window().set_cursor (cursor);
 			return false;
 		});
 		this.button_release_event.connect (() => {
 			clicked ();
 			return false;
 		});
 	}

 	public void set_label (string text) {
 		label.set_label (text);
 	}

 	public string get_label () {
 		return label.get_label ();
 	}

 	public void show () {
 		this.show_all();
 	}

 	public void set_style (string style) {
 		label.get_style_context ().add_class (style);
 	}

 	public void set_alignment (float xalign, float yalign) {
 		label.set_alignment (xalign, yalign);
 	}
 }