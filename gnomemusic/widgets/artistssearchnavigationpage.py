# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from typing import Any
import typing

from gi.repository import Adw, Gtk

from gnomemusic.widgets.artistnavigationpage import ArtistNavigationPage
from gnomemusic.widgets.artistsearchtile import ArtistSearchTile
if typing.TYPE_CHECKING:
    from gnomemusic.coreartist import CoreArtist
    from gnomemusic.application import Application


@Gtk.Template(
    resource_path="/org/gnome/Music/ui/ArtistsSearchNavigationPage.ui")
class ArtistsSearchNavigationPage(Adw.NavigationPage):
    """ArtistsSearchNavigationPage
    """

    __gtype_name__ = "ArtistsSearchNavigationPage"

    _all_artists_flowbox = Gtk.Template.Child()

    def __init__(
            self, application: Application,
            model: Gtk.FlattenListModel) -> None:
        """Initialize the ArtistsSearchNavigationPage.

        :param Application application: The application object
        :param Gtk.FlattenListModel model: The model to show
        """
        super().__init__()

        self._application = application
        window = self._application.props.window
        self._navigation_view = window.props.navigation_view

        self._all_artists_flowbox.bind_model(
            model, self._create_artist_widget)

    def _create_artist_widget(
            self, coreartist: CoreArtist) -> ArtistSearchTile:
        artist_tile = ArtistSearchTile(coreartist)

        return artist_tile

    @Gtk.Template.Callback()
    def _on_artist_activated(
            self, flowbox: Gtk.FlowBox, tile: ArtistSearchTile,
            user_data: Any = None) -> None:
        coreartist = tile.props.coreartist

        artist_page = ArtistNavigationPage(self._application, coreartist)
        self._navigation_view.push(artist_page)
