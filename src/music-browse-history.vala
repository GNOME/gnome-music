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

using Gee;

private class Music.BrowseHistory {
    private ArrayList<string> history;
    private HashMap<string, Music.ItemType?> history_types;

    public signal void changed ();

    public BrowseHistory () {
        history = new ArrayList<string>(); 
        history_types = new HashMap<string, Music.ItemType?>();
    }

    public void push (string id, Music.ItemType? item_type)
    {
        history.add (id);
        history_types.set (id, item_type);

        changed ();
    }

    public string get_last_item_id () {
        if (history.size >= 2) {
            // (history.size - 1) is the actual item, so we want the previous one
            var last = history.size - 2;
            return history[last];
        }

        return "";
    }

    public Music.ItemType? get_last_item_type () {
        string id = get_last_item_id ();
        return history_types[id];
    }

    public void delete_last_item () {
        // We want to go back one position in the history, so we only need to
        // delete the actual item (history.size - 1).
        var last = history.size - 1;
        var id = get_last_item_id ();
        history.remove_at (last);
        history_types.unset (id);

        changed ();
    }

    public int get_length () {
        return history.size;
    }

    public void clear () {
        history.clear();
        history_types.clear();

        changed ();
    }
}
