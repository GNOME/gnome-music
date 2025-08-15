# Copyright 2025 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from typing import Any, Dict
import typing

from gi.repository import GObject, Gio, Gtk

from gnomemusic.albumart import AlbumArt
from gnomemusic.coredisc import CoreDisc
import gnomemusic.utils as utils
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


class CoreAlbum(GObject.GObject):
    """Album information object

    Contains all relevant information about an album.
    """

    __gtype_name__ = "CoreAlbum"

    artist = GObject.Property(type=str)
    composer = GObject.Property(type=str, default=None)
    duration = GObject.Property(type=int, default=0)
    id = GObject.Property(type=str)
    title = GObject.Property(type=str)
    url = GObject.Property(type=str)
    year = GObject.Property(type=str, default=None)

    def __init__(
            self, application: Application,
            cursor_dict: Dict[str, Any]) -> None:
        """Initiate the CoreAlbum object

        :param Application application: The application object
        :param Dict[str, Any] cursor_dict: Dict with Tsparql keys
        """
        super().__init__()

        self._application = application
        self._coregrilo = application.props.coregrilo
        self._model = None
        self._thumbnail = None

        self.update(cursor_dict)

    def update(self, cursor_dict):
        """Update the CoreAlbum object with new info

        :param Dict[str, Any] cursor_dict: Dict with Tsparql keys
        """
        self.props.artist = utils.get_artist_from_cursor_dict(cursor_dict)
        self.props.composer = cursor_dict.get("composer")
        self.props.id = cursor_dict.get("id")
        self.props.title = utils.get_title_from_cursor_dict(cursor_dict)
        self.props.url = cursor_dict.get("url")
        self.props.year = cursor_dict.get("publicationDate")

    def remove_song_from_album(self, disc_nr: int, song_id: str) -> None:
        """Removes given song on given album disc

        :param int disc_nr: Number of disc
        :param int song_id: Song identifier
        """
        for coredisc in self.props.model:
            if coredisc.props.disc_nr == disc_nr:
                coredisc.remove_song_from_disc(song_id)
                break

    def _get_album_model(self):
        disc_model = Gio.ListStore()
        disc_no_exp = Gtk.PropertyExpression.new(CoreDisc, None, "disc_nr")
        disc_sorter = Gtk.NumericSorter.new(disc_no_exp)
        disc_model_sort = Gtk.SortListModel.new(disc_model, disc_sorter)

        self._coregrilo.get_album_discs(self, disc_model)

        return disc_model_sort

    @GObject.Property(
        type=Gtk.SortListModel, default=None,
        flags=GObject.ParamFlags.READABLE)
    def model(self):
        if self._model is None:
            self._model = self._get_album_model()
            self._model.connect("items-changed", self._on_list_items_changed)
            self._model.items_changed(0, 0, self._model.get_n_items())

        return self._model

    def _on_list_items_changed(self, model, position, removed, added):
        with self.freeze_notify():
            if added > 0:
                for i in range(added):
                    coredisc = model[position + i]
                    coredisc.connect(
                        "notify::duration", self._on_duration_changed)

    def _on_duration_changed(self, coredisc, duration):
        duration = 0

        for coredisc in self.props.model:
            duration += coredisc.props.duration

        self.props.duration = duration

    @GObject.Property(type=str, default=None)
    def thumbnail(self):
        """Album art thumbnail retrieval

        :return: The album art uri or "generic"
        :rtype: string
        """
        if self._thumbnail is None:
            self._thumbnail = "generic"
            AlbumArt(self._application, self)

        return self._thumbnail

    @thumbnail.setter  # type: ignore
    def thumbnail(self, value):
        """Album art thumbnail setter

        :param string value: uri or "generic"
        """
        self._thumbnail = value

    @GObject.Property(type=object, flags=GObject.ParamFlags.READABLE)
    def corealbum(self) -> CoreAlbum:
        return self
