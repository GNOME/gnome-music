# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from typing import Any
import typing

from gi.repository import Adw, Gtk

from gnomemusic.corealbum import CoreAlbum
from gnomemusic.widgets.albumcover import AlbumCover
from gnomemusic.widgets.albumnavigationpage import AlbumNavigationPage
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


@Gtk.Template(
    resource_path="/org/gnome/Music/ui/AlbumsSearchNavigationPage.ui")
class AlbumsSearchNavigationPage(Adw.NavigationPage):
    """ArtistsSearchNavigationPage
    """

    __gtype_name__ = "AlbumsSearchNavigationPage"

    _all_albums_flowbox = Gtk.Template.Child()

    def __init__(
            self, application: Application,
            model: Gtk.FlattenListModel) -> None:
        """Initialize the AlbumsSearchNavigationPage.

        :param Application application: The application object
        :param model Gtk.FlattenListModel: The model to show
        """
        super().__init__()

        self._application = application
        window = self._application.props.window
        self._navigation_view = window.props.navigation_view

        self._all_albums_flowbox.bind_model(
            model, self._create_album_cover)

    def _create_album_cover(self, corealbum: CoreAlbum) -> AlbumCover:
        album_cover = AlbumCover(corealbum)

        return album_cover

    @Gtk.Template.Callback()
    def _on_album_activated(
            self, flowbox: Gtk.FlowBox, album_cover: AlbumCover,
            user_data: Any = None) -> None:
        corealbum = album_cover.props.corealbum
        album_page = AlbumNavigationPage(self._application, corealbum)
        self._navigation_view.push(album_page)
