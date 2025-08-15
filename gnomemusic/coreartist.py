# Copyright 2025 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from typing import Any, Dict
import typing

from gi.repository import Gtk, GObject

from gnomemusic.artistart import ArtistArt
from gnomemusic.corealbum import CoreAlbum
import gnomemusic.utils as utils
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


class CoreArtist(GObject.GObject):
    """Artist information object

    Contains all relevant information about an artist.
    """

    artist = GObject.Property(type=str)
    id = GObject.Property(type=str)

    def __init__(
            self, application: Application,
            cursor_dict: Dict[str, Any]) -> None:
        """Initiate the CoreArtist object

        :param Application application: The application object
        :param Dict[str, Any] cursor_dict: Dict with Tsparql keys
        """
        super().__init__()

        self._application = application
        self._coregrilo = application.props.coregrilo
        self._coremodel = application.props.coremodel
        self._model = None
        self._thumbnail = None

        self.update(cursor_dict)

    def update(self, cursor_dict: Dict[str, Any]) -> None:
        self.props.id = cursor_dict.get("id")
        self.props.artist = utils.get_artist_from_cursor_dict(cursor_dict)

    def _get_artist_album_model(self):
        albums_model_filter = Gtk.FilterListModel.new(
            self._coremodel.props.albums)
        albums_model_filter.set_filter(Gtk.AnyFilter())

        albums_sort_exp = Gtk.PropertyExpression.new(CoreAlbum, None, "year")
        albums_sorter = Gtk.StringSorter.new(albums_sort_exp)
        albums_model_sort = Gtk.SortListModel.new(
            albums_model_filter, albums_sorter)

        self._coregrilo.get_artist_albums(self, albums_model_filter)

        return albums_model_sort

    @GObject.Property(type=Gtk.SortListModel, default=None)
    def model(self):
        if self._model is None:
            self._model = self._get_artist_album_model()

        return self._model

    @GObject.Property(type=str, default=None)
    def thumbnail(self):
        """Artist art thumbnail retrieval

        :return: The artist art uri or "generic"
        :rtype: string
        """
        if self._thumbnail is None:
            self._thumbnail = "generic"
            ArtistArt(self._application, self)

        return self._thumbnail

    @thumbnail.setter  # type: ignore
    def thumbnail(self, value):
        """Artist art thumbnail setter

        :param string value: uri or "generic"
        """
        self._thumbnail = value
