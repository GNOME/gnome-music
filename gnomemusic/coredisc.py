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

from gi.repository import GObject, Gio, Grl, Gtk


class CoreDisc(GObject.GObject):

    __gtype_name__ = "CoreDisc"

    disc_nr = GObject.Property(type=int, default=0)
    duration = GObject.Property(type=int, default=None)
    media = GObject.Property(type=Grl.Media, default=None)

    def __init__(self, application, media, nr, album_model=None):
        """Initialize a CoreDisc object

        :param Application application: The application object
        :param Grl.Media media: A media object
        :param int nr: The disc number to create an object for
        """
        super().__init__()

        self._album_model = album_model
        self._coregrilo = application.props.coregrilo
        self._coremodel = application.props.coremodel
        self._filter_model = None
        self._log = application.props.log
        self._model = None
        self._selected = False

        self.update(media)
        self.props.disc_nr = nr

    def update(self, media):
        self.props.media = media

    @GObject.Property(type=Gio.ListModel, default=None)
    def model(self):
        def _disc_sort(song_a, song_b, data=None):
            order = song_a.props.track_number - song_b.props.track_number
            if order < 0:
                return Gtk.Ordering.SMALLER
            elif order > 0:
                return Gtk.Ordering.LARGER
            else:
                return Gtk.Ordering.EQUAL

        def _disc_nr_filter(coresong):
            cs_dn = coresong.props.media.get_album_disc_number()
            return cs_dn == self.props.disc_nr

        if self._model is None:
            self._filter_model = Gtk.FilterListModel.new(
                self._album_model)
            filter = Gtk.CustomFilter()
            filter.set_filter_func(_disc_nr_filter)
            self._filter_model.set_filter(filter)

            self._model = Gtk.SortListModel.new(self._filter_model)
            song_sorter = Gtk.CustomSorter()
            song_sorter.set_sort_func(_disc_sort)
            self._model.set_sorter(song_sorter)

        return self._model

    @GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READWRITE)
    def selected(self):
        return self._selected

    @selected.setter  # type: ignore
    def selected(self, value):
        if value == self._selected:
            return

        self._selected = value

        # The model is loaded on-demand, so the first time the model is
        # returned it can still be empty. This is problem for returning
        # a selection. Trigger loading of the model here if a selection
        # is requested, it will trigger the filled model update as
        # well.
        self.props.model.items_changed(0, 0, 0)
