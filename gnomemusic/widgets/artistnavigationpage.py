# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
import typing

from gi.repository import Adw, GObject, Gtk

from gnomemusic.coreartist import CoreArtist
from gnomemusic.widgets.artistalbumswidget import ArtistAlbumsWidget
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


@Gtk.Template(resource_path='/org/gnome/Music/ui/ArtistNavigationPage.ui')
class ArtistNavigationPage(Adw.NavigationPage):
    """ArtistNavigationPage
    """

    __gtype_name__ = "ArtistNavigationPage"

    _artist_scrolled_window = Gtk.Template.Child()

    show_artist_label = GObject.Property(type=bool, default=True)

    def __init__(
            self, application: Application,
            coreartist: CoreArtist) -> None:
        """Initialize the AlbumNavigationPage.

        :param GtkApplication application: The application object
        :param CoreArtist coreartist: The artist albums to show
        """
        super().__init__()

        self._application = application
        self._coreartist = coreartist

        self.props.title = self._coreartist.props.artist

        artist_albums = ArtistAlbumsWidget(self._application)
        artist_albums.props.coreartist = self._coreartist

        self._artist_scrolled_window.props.child = artist_albums
