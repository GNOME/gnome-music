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
using Grl;
using Music;

public static int
main (string[] args) {
    Intl.bindtextdomain (Config.GETTEXT_PACKAGE, Config.LOCALEDIR);
    Intl.bind_textdomain_codeset (Config.GETTEXT_PACKAGE, "UTF-8");
    Intl.textdomain (Config.GETTEXT_PACKAGE);

    Grl.init (ref args);
    Gst.init (ref args);
    Gtk.init (ref args);

    var provider = new Gtk.CssProvider ();
    try {
        var sheet = Path.build_filename (Config.PKGDATADIR, "style", "gtk-style.css");
        provider.load_from_path (sheet);
        Gtk.StyleContext.add_provider_for_screen (Gdk.Screen.get_default (),
                provider,
                600);
    } catch (GLib.Error error) {
        warning (error.message);
    }

    var app = new App ();
    app.run ();
    app = null;

    return 0;
}
