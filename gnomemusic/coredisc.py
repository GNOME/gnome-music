# Copyright 2025 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
import typing

from gi.repository import GObject, Gtk

from gnomemusic.coresong import CoreSong
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.corealbum import CoreAlbum


class CoreDisc(GObject.GObject):

    __gtype_name__ = "CoreDisc"

    id = GObject.Property(type=str)
    disc_nr = GObject.Property(type=int, default=0)
    duration = GObject.Property(type=int, default=None)

    def __init__(
            self, application: Application, corealbum: CoreAlbum,
            nr: int) -> None:
        """Initialize a CoreDisc object

        :param Application application: The application object
        :param CoreAlbum corealbum: The album to create a disc from
        :param int nr: The disc number to create an object for
        """
        super().__init__()

        self._coregrilo = application.props.coregrilo
        self._coremodel = application.props.coremodel
        self._log = application.props.log
        self._model = None

        self.update(corealbum)
        self.props.disc_nr = nr

    def update(self, corealbum: CoreAlbum) -> None:
        self.props.id = corealbum.props.id

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
            if self._model:
                self._model.connect("items-changed", self._on_disc_changed)

            self._coregrilo.get_album_disc(self, filter_model)

        return self._model

    def _on_disc_changed(self, model, position, removed, added):
        with self.freeze_notify():
            duration = 0
            for coresong in model:
                duration += coresong.props.duration

            self.props.duration = duration

    def remove_song_from_disc(self, song_urn: str) -> None:
        """Update this disc

        :param str song_urn: Song identifier
        """
        # FIXME: For now we just retrieve the full disc again
        filter_model = self.props.model.get_model()
        self._coregrilo.get_album_disc(self, filter_model)
