# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
import typing

from gi.repository import Adw, GObject, Gtk

from gnomemusic.corealbum import CoreAlbum
from gnomemusic.widgets.albumwidget import AlbumWidget
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


@Gtk.Template(resource_path='/org/gnome/Music/ui/AlbumNavigationPage.ui')
class AlbumNavigationPage(Adw.NavigationPage):
    """AlbumNavigationPage
    """

    __gtype_name__ = "AlbumNavigationPage"

    _album_scrolled_window = Gtk.Template.Child()
    _page_title = Gtk.Template.Child()

    show_artist_label = GObject.Property(type=bool, default=True)

    def __init__(self, application: Application, corealbum: CoreAlbum) -> None:
        """Initialize the AlbumNavigationPage.

        :param GtkApplication application: The application object
        :param CoreAlbum corealbum: The CoreAlbum to show
        """
        super().__init__()

        self._application = application
        self._corealbum = corealbum

        self._page_title.props.title = self._corealbum.props.title
        self._page_title.props.subtitle = self._corealbum.props.artist

        album_widget = AlbumWidget(self._application)
        album_widget.props.corealbum = self._corealbum

        self._album_scrolled_window.props.child = album_widget
