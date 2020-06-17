# Copyright 2019 The GNOME Music developers
#
# GNOME Music is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# GNOME Music is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with GNOME Music; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# The GNOME Music authors hereby grant permission for non-GPL compatible
# GStreamer plugins to be used and distributed together with GStreamer
# and GNOME Music.  This permission is above and beyond the permissions
# granted by the GPL license by which GNOME Music is covered.  If you
# modify this code, you may extend this exception to your version of the
# code, but you are not obligated to do so.  If you do not wish to do so,
# delete this exception statement from your version.

from gi.repository import Gio, GObject, Gtk

import gnomemusic.utils as utils


class SongListStore(Gtk.ListStore):

    def __init__(self, model):
        """Initialize SongListStore.

        :param Gio.ListStore model: The songs model to use
        """
        super().__init__()

        self._model = Gtk.SortListModel.new(model)
        sorter = Gtk.CustomSorter()
        sorter.set_sort_func(
            utils.wrap_list_store_sort_func(self._songs_sort))
        self._model.set_sorter(sorter)

        self.set_column_types([
            GObject.TYPE_STRING,    # play or invalid icon
            GObject.TYPE_BOOLEAN,   # selected
            GObject.TYPE_STRING,    # title
            GObject.TYPE_STRING,    # artist
            GObject.TYPE_STRING,    # album
            GObject.TYPE_STRING,    # duration
            GObject.TYPE_INT,       # favorite
            GObject.TYPE_OBJECT,    # coresong
            GObject.TYPE_INT,       # validation
            GObject.TYPE_BOOLEAN,   # iter_to_clean
        ])

        self._model.connect("items-changed", self._on_items_changed)

    def _songs_sort(self, song_a, song_b):
        title_a = song_a.props.title
        title_b = song_b.props.title
        song_cmp = (utils.normalize_caseless(title_a)
                    == utils.normalize_caseless(title_b))
        if not song_cmp:
            return utils.natural_sort_names(title_a, title_b)

        artist_a = song_a.props.artist
        artist_b = song_b.props.artist
        artist_cmp = (utils.normalize_caseless(artist_a)
                      == utils.normalize_caseless(artist_b))
        if not artist_cmp:
            return utils.natural_sort_names(artist_a, artist_b)

        return utils.natural_sort_names(song_a.props.album, song_b.props.album)

    def _on_items_changed(self, model, position, removed, added):
        if removed > 0:
            for i in list(range(removed)):
                path = Gtk.TreePath.new_from_string("{}".format(position))
                iter_ = self.get_iter(path)
                self.remove(iter_)

        if added > 0:
            for i in list(range(added)):
                coresong = model[position + i]
                time = utils.seconds_to_string(coresong.props.duration)
                self.insert_with_valuesv(
                    position + i, [2, 3, 4, 5, 6, 7],
                    [coresong.props.title, coresong.props.artist,
                     coresong.props.album, time,
                     int(coresong.props.favorite), coresong])
                coresong.connect(
                    "notify::favorite", self._on_favorite_changed)
                coresong.connect(
                    "notify::validation", self._on_validation_state_changed)

    def _on_favorite_changed(self, coresong, value):
        for row in self:
            if coresong == row[7]:
                row[6] = coresong.props.favorite
                break

    def _on_validation_state_changed(self, coresong, value):
        for row in self:
            if coresong == row[7]:
                row[8] = coresong.props.validation
                break

    @GObject.Property(
        type=Gio.ListStore, default=None, flags=GObject.ParamFlags.READABLE)
    def model(self):
        """Gets the model of songs sorted.

        :returns: a list model of sorted songs
        :rtype: Gtk.SortListModel
        """
        return self._model
