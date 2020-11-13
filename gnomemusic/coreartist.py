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

from __future__ import annotations

from typing import Optional
import typing

import gi
gi.require_versions({"Gfm": "0.1", "Grl": "0.3"})
from gi.repository import Gfm, Gio, Grl, GObject

from gnomemusic.artistart import ArtistArt
from gnomemusic.coresong import CoreSong
import gnomemusic.utils as utils
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.corealbum import CoreAlbum
    from gnomemusic.coregrilo import CoreGrilo
    from gnomemusic.coremodel import CoreModel


class CoreArtist(GObject.GObject):
    """Exposes a Grl.Media with relevant data as properties
    """

    artist = GObject.Property(type=str)
    media = GObject.Property(type=Grl.Media)

    def __init__(self, application: Application, media: Grl.Media) -> None:
        """Initiate the CoreArtist object

        :param Application application: The application object
        :param Grl.Media media: A media object
        """
        super().__init__()

        self._application: Application = application
        self._coregrilo: CoreGrilo = application.props.coregrilo
        self._coremodel: CoreModel = application.props.coremodel
        self._model: Optional[Gfm.FlattenListModel] = None
        self._selected: bool = False
        self._thumbnail: Optional[str] = None

        self._albums_model_proxy = Gio.ListStore.new(Gio.ListModel)
        self._albums_model_filter = Gfm.FilterListModel.new(
            self._coremodel.props.albums)
        self._albums_model_sort = Gfm.SortListModel.new(
            self._albums_model_filter,
            utils.wrap_list_store_sort_func(self._album_sort))

        self.update(media)

    def update(self, media: Grl.Media) -> None:
        self.props.media = media
        self.props.artist = utils.get_artist_name(media)

    @staticmethod
    def _album_sort(album_a: CoreAlbum, album_b: CoreAlbum) -> None:
        return album_a.props.year > album_b.props.year

    def _load_artist_album_model(self) -> None:
        self._model = Gfm.FlattenListModel.new(
            CoreSong, self._albums_model_proxy)

        self._albums_model_filter.set_filter_func(lambda a: False)
        self._coregrilo.get_artist_albums(
            self.props.media, self._albums_model_filter)

        self._albums_model_sort.connect(
            "items-changed", self._on_albums_changed)

    @GObject.Property(type=Gfm.FlattenListModel, default=None)
    def model(self) -> Gfm.FlattenListModel:
        """Model which contains all the songs of an artist.

        :returns: songs model
        :rtype: Gfm.FlattenListModel
        """
        if self._model is None:
            self._load_artist_album_model()

        return self._model

    @GObject.Property(type=Gio.ListModel, flags=GObject.ParamFlags.READABLE)
    def albums_model(self) -> Gio.ListModel:
        """Model which contains all the albums of an artists.

        :returns: albums model
        :rtype: Gfm.SortListModel
        """
        if self._model is None:
            self._load_artist_album_model()

        return self._albums_model_sort

    def _on_albums_changed(
            self, model: Gfm.SortListModel, pos: int, removed: int,
            added: int) -> None:
        with self.freeze_notify():
            for corealbum in model:
                corealbum.props.selected = self.props.selected

            if added > 0:
                for i in range(added):
                    corealbum = model[pos + i]
                    self._albums_model_proxy.append(
                        corealbum.props.model)

    @GObject.Property(type=bool, default=False)
    def selected(self) -> bool:
        return self._selected

    @selected.setter  # type: ignore
    def selected(self, value: bool) -> None:
        if value == self._selected:
            return

        self._selected = value

        # The model is loaded on-demand, so the first time the model is
        # returned it can still be empty. This is problem for returning
        # a selection. Trigger loading of the model here if a selection
        # is requested, it will trigger the filled model update as
        # well.
        self.props.model.items_changed(0, 0, 0)

    @GObject.Property(type=str, default=None)
    def thumbnail(self) -> str:
        """Artist art thumbnail retrieval

        :return: The artist art uri or "generic" or "loading"
        :rtype: string
        """
        if self._thumbnail is None:
            self._thumbnail = "loading"
            ArtistArt(self._application, self)

        return self._thumbnail

    @thumbnail.setter  # type: ignore
    def thumbnail(self, value: str) -> None:
        """Artist art thumbnail setter

        :param string value: uri, "generic" or "loading"
        """
        self._thumbnail = value
