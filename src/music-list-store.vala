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
using Tracker;

internal enum Music.MusicListStoreColumn {
    DISC = 0,
    TRACK,
    ALBUM,
    ALBUM_ART,
    TITLE,
    URL,
    ALBUM_ID,
    DURATION,
    ARTIST
}

internal class Music.MusicListStore : ListStore {
    private const string QUERY =
"""
SELECT
        nie:title(nmm:musicAlbum(?song))
        nmm:setNumber(nmm:musicAlbumDisc(?song))
        nmm:trackNumber(?song)
        nie:title(?song)
        nie:url(?song)
        tracker:id(nmm:musicAlbum(?song))
        nfo:duration(?song)
        nmm:artistName(nmm:performer(?song))
{
        ?song a nmm:MusicPiece
}

ORDER BY
        nie:title(nmm:musicAlbum(?song))
        nmm:setNumber(nmm:musicAlbumDisc(?song))
        nmm:trackNumber(?song)
        nie:title(?song)
""";

    public signal void finished ();

    public MusicListStore () {
        Object ();

        Type[] types = { typeof (uint),
                         typeof (uint),
                         typeof (string),
                         typeof (string),
                         typeof (string),
                         typeof (string),
                         typeof (uint),
                         typeof (string),
                         typeof (string)};
        this.set_column_types (types);
        this.fill_list_store.begin ();
    }

    private async void fill_list_store () {
        try {
            this.clear ();
            Sparql.Connection connection = yield Sparql.Connection.get_async ();
            Sparql.Cursor cursor = yield connection.query_async (QUERY);
            while (cursor.next ()) {
                stdout.printf ("-------------\n");
                stdout.printf (cursor.get_string (5) + "\n");
                stdout.printf ("-------------\n");
                /*
                TreeIter iter;
                this.append (out iter);
                this.set (iter,
                          MusicListStoreColumn.DISC,
                              (uint) cursor.get_integer (1),
                          MusicListStoreColumn.TRACK,
                              (uint) cursor.get_integer (2),
                          MusicListStoreColumn.ALBUM,
                              cursor.get_string (0),
                          MusicListStoreColumn.TITLE,
                              cursor.get_string (3),
                          MusicListStoreColumn.URL,
                              cursor.get_string (4),
                          MusicListStoreColumn.ALBUM_ID,
                              cursor.get_string (5),
                          MusicListStoreColumn.DURATION,
                              (uint) cursor.get_integer (6),
                          MusicListStoreColumn.ARTIST,
                              cursor.get_string (7));
                */
            }
        } catch (Error error) {
            critical ("Something failed: %s", error.message);
        }

        this.finished ();
    }
}
