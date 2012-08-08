/*
    This file is part of MusicMate.

    MusicMate is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    MusicMate is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with MusicMate.  If not, see <http://www.gnu.org/licenses/>.
*/

using Gee;
using Gtk;

internal class Music.FilteredList : TreeModelFilter {
    private HashSet<string> album_list;

    public string albums {
        owned get {
            return string.join (",", album_list.to_array ());
        }

        set {
            this.album_list.clear ();
            foreach (var album in value.split (",")) {
                this.album_list.add (album);
            }

            this.refilter ();
        }
    }

    public FilteredList () {
        var model = new MusicListStore ();
        Object (child_model : model,
                virtual_root : null );

        this.album_list = new HashSet<string> ();
        this.set_visible_func (this.filter_albums);
    }

    private bool filter_albums (TreeModel model, TreeIter iter) {
        string tracker_id = null;

        if (this.album_list.is_empty) {
            return true;
        }

        model.get (iter,
                   MusicListStoreColumn.ALBUM_ID,
                   ref tracker_id);

        if (tracker_id == null) {
            return false;
        }

        return album_list.contains (tracker_id);
    }
}
