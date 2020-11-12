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

import typing

import gi
gi.require_versions({"Gfm": "0.1", "Grl": "0.3"})
from gi.repository import Gfm, Gio, Grl, GObject

import gnomemusic.utils as utils

from gnomemusic.albumart import AlbumArt
from gnomemusic.coresong import CoreSong
if typing.TYPE_CHECKING:
    from gnomemusic.coredisc import CoreDisc


class CoreAlbum(GObject.GObject):
    """Exposes a Grl.Media with relevant data as properties
    """

    artist = GObject.Property(type=str)
    composer = GObject.Property(type=str, default=None)
    duration = GObject.Property(type=int, default=0)
    media = GObject.Property(type=Grl.Media)
    title = GObject.Property(type=str)
    url = GObject.Property(type=str)
    year = GObject.Property(type=str, default="----")

    def __init__(self, application, media):
        """Initiate the CoreAlbum object

        :param Application application: The application object
        :param Grl.Media media: A media object
        """
        super().__init__()

        self._application = application
        self._coregrilo = application.props.coregrilo
        self._model = None
        self._selected = False
        self._thumbnail = None

        self._disc_model_proxy = Gio.ListStore.new(Gio.ListModel)
        self._disc_model = Gio.ListStore()
        self._disc_model_sort = Gfm.SortListModel.new(
            self._disc_model,
            utils.wrap_list_store_sort_func(self._disc_order_sort))
        self._disc_model_sort.connect(
            "items-changed", self._on_core_items_changed)

        self.update(media)

    def update(self, media):
        """Update the CoreAlbum object with new info

        :param Grl.Media media: A media object
        """
        self.props.media = media
        self.props.artist = utils.get_artist_name(media)
        self.props.composer = media.get_composer()
        self.props.title = utils.get_media_title(media)
        self.props.url = media.get_url()
        self.props.year = utils.get_media_year(media)

    @staticmethod
    def _disc_order_sort(disc_a: CoreDisc, disc_b: CoreDisc) -> int:
        return disc_a.props.disc_nr - disc_b.props.disc_nr

    def _load_album_model(self):
        self._coregrilo.get_album_discs(self.props.media, self._disc_model)
        self._model = Gfm.FlattenListModel.new(
            CoreSong, self._disc_model_proxy)

    @GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READABLE)
    def model_loaded(self) -> bool:
        """Check if the model has already been loaded

        :returns: True if the model is loaded
        :rtype: bool
        """
        return self._model is not None

    @GObject.Property(
        type=Gfm.FlattenListModel, default=None,
        flags=GObject.ParamFlags.READABLE)
    def model(self):
        """Model which contains all the songs of an album.

        :returns: songs model
        :rtype: Gfm.FlattenListModel
        """
        if not self.props.model_loaded:
            self._load_album_model()

        return self._model

    @GObject.Property(
        type=Gfm.SortListModel, flags=GObject.ParamFlags.READABLE)
    def disc_model(self) -> Gfm.SortListModel:
        """Model which contains all the discs of an album.

        :returns: discs model
        :rtype: Gfm.SortListModel
        """
        if not self.props.model_loaded:
            self._load_album_model()

        return self._disc_model_sort

    def _on_core_items_changed(self, model, position, removed, added):
        with self.freeze_notify():
            for coredisc in model:
                coredisc.props.selected = self.props.selected

            if added > 0:
                for i in range(added):
                    coredisc = model[position + i]
                    self._disc_model_proxy.append(coredisc.props.model)
                    coredisc.connect(
                        "notify::duration", self._on_duration_changed)

    def _on_duration_changed(self, coredisc, duration):
        duration = 0

        for coredisc in self._disc_model:
            duration += coredisc.props.duration

        self.props.duration = duration

    @GObject.Property(type=bool, default=False)
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

    @GObject.Property(type=str, default=None)
    def thumbnail(self):
        """Album art thumbnail retrieval

        :return: The album art uri or "generic" or "loading"
        :rtype: string
        """
        if self._thumbnail is None:
            self._thumbnail = "loading"
            AlbumArt(self._application, self)

        return self._thumbnail

    @thumbnail.setter  # type: ignore
    def thumbnail(self, value):
        """Album art thumbnail setter

        :param string value: uri, "generic" or "loading"
        """
        self._thumbnail = value
