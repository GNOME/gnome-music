/*
 * Copyright (c) 2013 Eslam Mostafa <cseslam@gmail.com>
 * Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
 * Copyright (c) 2013 Giovanni Campagna
 *
 * Gnome Music is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 *
 * The Gnome Music authors hereby grant permission for non-GPL compatible
 * GStreamer plugins to be used and distributed together with GStreamer and
 * Gnome Music. This permission is above and beyond the permissions granted by
 * the GPL license by which Gnome Music is covered. If you modify this code, you may 
 * extend this exception to your version of the code, but you are not obligated 
 * to do so. If you do not wish to do so, delete this exception statement from 
 * your version.
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
 */

pkg.initSubmodule('libgd');
pkg.initGettext();

const GIRepository = imports.gi.GIRepository;
const App = imports.application;

function main(argv) {
    let app = new App.Application();
    return app.run(argv);
}
