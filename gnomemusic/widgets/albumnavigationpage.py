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
    from gnomemusic.player import Player


@Gtk.Template(resource_path='/org/gnome/Music/ui/AlbumNavigationPage.ui')
class AlbumNavigationPage(Adw.NavigationPage):
    """AlbumNavigationPage
    """

    __gtype_name__ = "AlbumNavigationPage"

    _page_title = Gtk.Template.Child()
    _viewport = Gtk.Template.Child()

    show_artist_label = GObject.Property(type=bool, default=True)

    def __init__(self, application: Application, corealbum: CoreAlbum) -> None:
        """Initialize the AlbumNavigationPage.

        :param GtkApplication application: The application object
        :param CoreAlbum corealbum: The CoreAlbum to show
        """
        super().__init__()

        self._application = application
        self._corealbum = corealbum
        self._player = application.props.player

        self._notify_id = 0

        self._page_title.props.title = self._corealbum.props.title
        self._page_title.props.subtitle = self._corealbum.props.artist

        self._album_widget = AlbumWidget(self._application)
        self._album_widget.props.corealbum = self._corealbum

        self._viewport.props.child = self._album_widget

        self.connect("hidden", self._on_hidden)
        self.connect("shown", self._on_shown)

    def _on_hidden(self, widget: Adw.NavigationPage) -> None:
        self._player.disconnect(self._notify_id)

    def _on_shown(self, widget: Adw.NavigationPage) -> None:
        self._notify_id = self._player.connect(
            "notify::position", self._on_player_position_changed)

    def _on_player_position_changed(
            self, player: Player, position: GObject.GParamInt) -> None:
        coresong = self._player.props.current_song
        scroll_to_widget = self._album_widget.get_active_songwidget(coresong)
        self._viewport.scroll_to(scroll_to_widget, None)
