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

public class Music.App : Gtk.Application {
    public GLib.Settings settings;
    public static App app;
    private Gtk.Overlay overlay;

    private Music.Window window;
    //private Music.Embed embed;

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

    private void create_window () {
        window = new Music.Window (this);
        window.set_application (this);
        window.set_title (_("Music"));
        window.hide_titlebar_when_maximized = true;
        window.delete_event.connect (window_delete_event);
        window.key_press_event.connect_after (window_key_press_event);
        set_window_size_and_position ();

        //embed = new Music.Embed ();
        //window.add (embed);
    }

    private bool window_delete_event (Gdk.EventAny event) {
        save_window_geometry ();
        return false;
    }

    private bool window_key_press_event (Gdk.EventKey event) {
        if ((event.keyval == Gdk.keyval_from_name ("q")) &&
                ((event.state & Gdk.ModifierType.CONTROL_MASK) != 0)) {
            save_window_geometry ();
            window.destroy ();
        }

        return false;
    }

    private void save_window_geometry () {
        var state = window.get_window ().get_state ();
        if (WindowState.MAXIMIZED in state) {
            settings.set_boolean ("window-maximized", true);
            return;
        }

        int width, height;
        int x, y;

        window.get_size(out width, out height);
        GLib.Variant[] size = {new GLib.Variant.int32 (width), new GLib.Variant.int32 (height) };
        var variant = new GLib.Variant.array (GLib.VariantType.INT32, size);
        settings.set_value("window-size", variant);

        window.get_position(out x, out y);
        GLib.Variant[] position = {new GLib.Variant.int32 (x), new GLib.Variant.int32 (y) };
        variant = new GLib.Variant.array (GLib.VariantType.INT32, position);
        settings.set_value("window-position", variant);

        settings.set_boolean ("window-maximized", false);
    }

    private void set_window_size_and_position () {
        if (settings.get_boolean ("window-maximized")) {
            window.maximize ();
        }
        else {
            var variant = settings.get_value ("window-size");
            if (variant.n_children() == 2) {
                int width = variant.get_child_value(0).get_int32();
                int height = variant.get_child_value(1).get_int32();
                window.set_default_size (width, height);
            }

            variant = settings.get_value ("window-position");
            if (variant.n_children() == 2) {
                int x = variant.get_child_value(0).get_int32();
                int y = variant.get_child_value(1).get_int32();
                window.move (x, y);
            }
        }
    }

    public override void activate () {
        if (window == null) {
            create_window();
            app.window.show();
        }
        else {
            window.present ();
        }
    }

    public App () {
        Object (application_id: "org.gnome.Music");
        this.app = this;
        settings = new GLib.Settings ("org.gnome.Music");
    }
}
