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

from gi.repository import GObject, Gio, Gfm, Grl

import gnomemusic.utils as utils


class CoreDisc(GObject.GObject):

    disc_nr = GObject.Property(type=int, default=0)
    duration = GObject.Property(type=int, default=None)
    media = GObject.Property(type=Grl.Media, default=None)

    def __init__(self, application, media, nr):
        """Initialize a CoreDisc object

        :param Application application: The application object
        :param Grl.Media media: A media object
        :param int nr: The disc number to create an object for
        """
        super().__init__()

        self._coregrilo = application.props.coregrilo
        self._coremodel = application.props.coremodel
        self._filter_model = None
        self._log = application.props.log
        self._model = None
        self._old_album_ids = []
        self._selected = False

        self.update(media)
        self.props.disc_nr = nr

    def update(self, media):
        self.props.media = media

    @GObject.Property(type=Gio.ListModel, default=None)
    def model(self):
        def _disc_sort(song_a, song_b):
            return song_a.props.track_number - song_b.props.track_number

        if self._model is None:
            self._filter_model = Gfm.FilterListModel.new(
                self._coremodel.props.songs)
            self._filter_model.set_filter_func(lambda a: False)
            self._model = Gfm.SortListModel.new(self._filter_model)
            self._model.set_sort_func(
                utils.wrap_list_store_sort_func(_disc_sort))

            self._model.connect("items-changed", self._on_disc_changed)

            self._get_album_disc(
                self.props.media, self.props.disc_nr, self._filter_model)

        return self._model

    def _on_disc_changed(self, model, position, removed, added):
        with self.freeze_notify():
            duration = 0
            for coresong in model:
                coresong.props.selected = self._selected
                duration += coresong.props.duration

            self.props.duration = duration

    def _get_album_disc(self, media, discnr, model):
        album_ids = []
        model_filter = model

        def _filter_func(core_song):
            return core_song.props.grlid in album_ids

        def _callback(source, op_id, media, remaining, error):
            if error:
                self._log.warning("Error: {}".format(error))
                return

            if media is None:
                if sorted(album_ids) == sorted(self._old_album_ids):
                    return
                model_filter.set_filter_func(_filter_func)
                self._old_album_ids = album_ids
                return

            album_ids.append(media.get_source() + media.get_id())

        self._coregrilo.populate_album_disc_songs(media, discnr, _callback)

    @GObject.Property(
        type=bool, default=False, flags=GObject.BindingFlags.SYNC_CREATE)
    def selected(self):
        return self._selected

    @selected.setter  # type: ignore
    def selected(self, value):
        self._selected = value

        # The model is loaded on-demand, so the first time the model is
        # returned it can still be empty. This is problem for returning
        # a selection. Trigger loading of the model here if a selection
        # is requested, it will trigger the filled model update as
        # well.
        self.props.model.items_changed(0, 0, 0)
