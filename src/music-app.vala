/* -*- Mode: vala; indent-tabs-mode: t; c-basic-offset: 2; tab-width: 8 -*- */
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

public class Music.App : Gtk.Application {
  public GLib.Settings settings;
  public static App app;
  private Gtk.Overlay overlay;

  private bool window_delete_event (Gdk.EventAny event) {
    return false;
  }

  private bool window_key_press_event (Gdk.EventKey event) {
    if ((event.keyval == Gdk.keyval_from_name ("q")) &&
	((event.state & Gdk.ModifierType.CONTROL_MASK) != 0)) {
      window.destroy ();
    }

    return false;
  }

  public override void startup () {
    base.startup ();
  }

  public void show_message (string message) {
    var notification = new Gtk.Notification ();

    var g = new Grid ();
    g.set_column_spacing (8);
    var l = new Label (message);
    l.set_line_wrap (true);
    l.set_line_wrap_mode (Pango.WrapMode.WORD_CHAR);
    notification.add (l);

    notification.show_all ();
    overlay.add_overlay (notification);
  }

  public App () {
    Object (application_id: "org.gnome.Music", flags: ApplicationFlags.HANDLES_COMMAND_LINE);
    this.app = this;
    settings = new GLib.Settings ("org.gnome.Music");
  }
}
