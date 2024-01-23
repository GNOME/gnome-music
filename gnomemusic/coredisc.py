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

from gi.repository import GObject, Grl, Gtk

from gnomemusic.coresong import CoreSong


class CoreDisc(GObject.GObject):

    __gtype_name__ = "CoreDisc"

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
        self._log = application.props.log
        self._model = None

        self.update(media)
        self.props.disc_nr = nr

    def update(self, media):
        self.props.media = media

    @GObject.Property(type=Gtk.SortListModel, default=None)
    def model(self) -> Gtk.SortListModel:
        if self._model is None:
            filter_model = Gtk.FilterListModel.new(
                self._coremodel.props.songs)
            filter_model.set_filter(Gtk.AnyFilter())

            song_exp = Gtk.PropertyExpression.new(
                CoreSong, None, "track-number")
            song_sorter = Gtk.NumericSorter.new(song_exp)
            self._model = Gtk.SortListModel.new(filter_model, song_sorter)
            self._model.connect("items-changed", self._on_disc_changed)

            self._coregrilo.get_album_disc(
                self.props.media, self.props.disc_nr, filter_model)

        return self._model

    def _on_disc_changed(self, model, position, removed, added):
        with self.freeze_notify():
            duration = 0
            for coresong in model:
                duration += coresong.props.duration

            self.props.duration = duration
