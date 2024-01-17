# Copyright 2019 The GNOME Music Developers
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

from gettext import gettext as _
from gi.repository import Adw, GObject, Gtk
from typing import Dict, List

from gnomemusic.coverpaintable import CoverPaintable
from gnomemusic.utils import ArtSize, DefaultIconType
from gnomemusic.widgets.albumnavigationpage import AlbumNavigationPage
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

        self._list_item_bindings: Dict[
            Gtk.ListItem, List[GObject.Binding]] = {}
        self._list_item_star_controllers: Dict[
            Gtk.ListItem, List[GObject.Binding]] = {}

        list_item_factory = Gtk.SignalListItemFactory()
        list_item_factory.connect("setup", self._setup_list_item)
        list_item_factory.connect("bind", self._bind_list_item)
        list_item_factory.connect("unbind", self._unbind_list_item)

        self._gridview.props.factory = list_item_factory

        selection_model = Gtk.MultiSelection.new(
            self._application.props.coremodel.props.albums_sort)
        self._gridview.props.model = selection_model

        self._gridview.connect("activate", self._on_album_activated)

    def _on_album_activated(self, widget, position):
        corealbum = widget.props.model[position]

        album_page = AlbumNavigationPage(self._application, corealbum)
        self._navigation_view.push(album_page)

    def _setup_list_item(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        builder = Gtk.Builder.new_from_resource(
            "/org/gnome/Music/ui/AlbumCoverListItem.ui")
        list_item.props.child = builder.get_object("_album_cover")
        cover_image = list_item.props.child.get_first_child()
        cover_image.set_size_request(
            ArtSize.MEDIUM.width, ArtSize.MEDIUM.height)
        cover_image.props.paintable = CoverPaintable(
            self, ArtSize.MEDIUM, icon_type=DefaultIconType.ALBUM)

    def _bind_list_item(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        album_cover = list_item.props.child
        corealbum = list_item.props.item

        cover_image = album_cover.get_first_child()
        album_label = album_cover.get_first_child().get_next_sibling()
        artist_label = album_label.get_next_sibling()

        b1 = corealbum.bind_property(
            "corealbum", cover_image.props.paintable, "coreobject",
            GObject.BindingFlags.SYNC_CREATE)
        b2 = corealbum.bind_property(
            "title", album_label, "label", GObject.BindingFlags.SYNC_CREATE)
        b3 = corealbum.bind_property(
            "artist", artist_label, "label", GObject.BindingFlags.SYNC_CREATE)

        self._list_item_bindings[list_item] = [b1, b2, b3]

    def _unbind_list_item(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        bindings = self._list_item_bindings.pop(list_item)
        [binding.unbind() for binding in bindings]
