# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
import typing

from gettext import gettext as _
from gi.repository import Adw, GObject, Gtk

from gnomemusic.widgets.albumnavigationpage import AlbumNavigationPage
from gnomemusic.widgets.albumtile import AlbumTile
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


@Gtk.Template(resource_path="/org/gnome/Music/ui/AlbumsView.ui")
class AlbumsView(Adw.Bin):
    """Gridlike view of all albums

    Album activation switches to AlbumWidget.
    """

    __gtype_name__ = "AlbumsView"

    icon_name = GObject.Property(
        type=str, default="media-optical-cd-audio-symbolic",
        flags=GObject.ParamFlags.READABLE)
    title = GObject.Property(
        type=str, default=_("Albums"), flags=GObject.ParamFlags.READABLE)

    _gridview = Gtk.Template.Child()

    def __init__(self, application: Application) -> None:
        """Initialize AlbumsView

        :param application: The Application object
        """
        super().__init__()

        self.props.name = "albums"

        self._application = application
        self._window = application.props.window
        self._navigation_view = self._window.props.navigation_view

        list_item_factory = Gtk.SignalListItemFactory()
        list_item_factory.connect("setup", self._setup_list_item)
        list_item_factory.connect("bind", self._bind_list_item)

        self._gridview.props.factory = list_item_factory

        selection_model = Gtk.MultiSelection.new(
            self._application.props.coremodel.props.albums_sort)
        self._gridview.props.model = selection_model

        self._gridview.connect("activate", self._on_album_activated)

    def _on_album_activated(
            self, gridview: Gtk.GridView, position: int) -> None:
        corealbum = gridview.props.model[position]

        album_page = AlbumNavigationPage(self._application, corealbum)
        self._navigation_view.push(album_page)

    def _setup_list_item(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        list_item.props.child = AlbumTile()

    def _bind_list_item(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        corealbum = list_item.props.item
        album_tile = list_item.props.child
        album_tile.props.corealbum = corealbum
