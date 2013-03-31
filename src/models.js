/*
 * Copyright (c) 2013 Eslam Mostafa.
 *
 * Gnome Music is free software; you can Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
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
 * Author: Eslam Mostafa <cseslam@gmail.com>
 *
 */

const Gtk = imports.gi.Gtk;
const Lang = imports.lang;

const Columns = {
    ID:             Gd.MainColumns.ID,
    URI:            Gd.MainColumns.URI,
    PRIMARY_TEXT:   Gd.MainColumns.PRIMARY_TEXT,
    SECONDARY_TEXT: Gd.MainColumns.SECONDARY_TEXT,
    ICON:           Gd.MainColumns.ICON,
    MTIME:          Gd.MainColumns.MTIME,
    SELECTED:       Gd.MainColumns.SELECTED,
    LOCATION:       7,
    INFO:           8
};

const BaseModel = new Lang.Class({
    Name: "BaseModel",
    Extends: Gtk.ListStore,

    _init: function() {
        this.parent();
    },

    push_item: function(tracker_id, uri, title, artists, icon, duration, data) {
        var iter = this.append();

        this.set(iter, [Columns.PRIMARY_TEXT, Columns.ICON], title, icon);
    }
});

const AlbumModel = new Lang.Class({
    Name: "AlbumModel",
    Extends: BaseModel,

    _init: function() {
        this.parent();

        this.set_columns([
            GObject.TYPE_STRING,        // Album id
            GObject.TYPE_STRING,        // Album uri
            GObject.TYPE_STRING,        // Album title
            GObject.TYPE_STRING,        // Album artists
            GObject.TYPE_STRING,        // Album data
            GdkPixbuf.Pixbuf,           // Album icon
            GObject.TYPE_INT,           // Album duration
            GObject.TYPE_BOOLEAN        // Album ??
        ]);
    }
});

const ArtistsModel = new Lang.Class({
    Name: "ArtistModel",
    Extends: BaseModel,

    _init: function() {
        this.parent();
    }
});

const SongModel = new Lang.Class({
    Name: "SongModel",
    Extends: BaseModel,

    _init: function() {
        this.parent();
    }
});

const PlaylistModel = new Lang.Class({
    Name: "PlaylistModel",
    Extends: BaseModel,

    _init: function() {
        this.parent();
    }
});