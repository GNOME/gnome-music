# Copyright (c) 2016 The GNOME Music Developers
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

from gnomemusic.widgets.artistalbumswidget import ArtistAlbumsWidget
from gnomemusic.widgets.artisttile import ArtistTile
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


@Gtk.Template(resource_path="/org/gnome/Music/ui/ArtistsView.ui")
class ArtistsView(Adw.Bin):
    """Main view of all available artists

    Consists of a list of artists on the left side and an overview of
    all albums by this artist on the right side.
    """

    __gtype_name__ = "ArtistsView"

    icon_name = GObject.Property(
        type=str, default="music-artist-symbolic",
        flags=GObject.ParamFlags.READABLE)
    title = GObject.Property(
        type=str, default=_("Artists"), flags=GObject.ParamFlags.READABLE)

    _artist_view = Gtk.Template.Child()
    _sidebar = Gtk.Template.Child()

    def __init__(self, application: Application) -> None:
        """Initialize

        :param GtkApplication application: The application object
        """
        super().__init__()

        self.props.name = "artists"

        # This indicates if the current list has been empty and has
        # had no user interaction since.
        self._untouched_list = True

        self._window = application.props.window
        self._coremodel = application.props.coremodel
        self._model = self._coremodel.props.artists_sort

        self._selection_model = Gtk.SingleSelection.new(self._model)
        self._sidebar.props.model = self._selection_model
        artist_item_factory = Gtk.SignalListItemFactory()
        artist_item_factory.connect("setup", self._on_list_view_setup)
        artist_item_factory.connect("bind", self._on_list_view_bind)
        self._sidebar.props.factory = artist_item_factory

        self._artist_album = ArtistAlbumsWidget(application)
        self._artist_view.props.child = self._artist_album

        self._selection_model.connect_after(
            "items-changed", self._on_model_items_changed)
        self._on_model_items_changed(self._selection_model, 0, 0, 0)

    def _on_list_view_setup(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        list_item.props.child = ArtistTile()

        def _on_clicked(artist_tile: ArtistTile) -> None:
            self._sidebar.emit("activate", list_item.props.position)

        list_item.props.child.connect("clicked", _on_clicked)

    def _on_list_view_bind(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        coreartist = list_item.props.item
        artist_tile = list_item.props.child
        artist_tile.props.coreartist = coreartist

    def _on_model_items_changed(
            self, model: Gtk.SingleSelection, position: int, removed: int,
            added: int) -> None:
        if model.get_n_items() == 0:
            self._untouched_list = True
            # FIXME: Add an empty state.
        elif self._untouched_list is True:
            self._untouched_list = False
            self._sidebar.emit("activate", 0)

    @Gtk.Template.Callback()
    def _on_artist_activated(
            self, sidebar: Gtk.ListView, position: int) -> None:
        """Initializes new artist album widgets"""
        coreartist = self._selection_model.get_item(position)
        self._artist_album.props.coreartist = coreartist
