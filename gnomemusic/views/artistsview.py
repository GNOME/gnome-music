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

from gettext import gettext as _
from gi.repository import GObject, Gtk

from gnomemusic.widgets.artistalbumswidget import ArtistAlbumsWidget
from gnomemusic.widgets.artisttile import ArtistTile


@Gtk.Template(resource_path="/org/gnome/Music/ui/ArtistsView.ui")
class ArtistsView(Gtk.Paned):
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

    _artist_container = Gtk.Template.Child()
    _artist_view = Gtk.Template.Child()
    _sidebar = Gtk.Template.Child()

    def __init__(self, application):
        """Initialize

        :param GtkApplication application: The application object
        """
        super().__init__()

        self.props.name = "artists"

        self._application = application
        self._loaded_artists = []

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

        self._selection_model.connect_after(
            "items-changed", self._on_model_items_changed)
        self._on_model_items_changed(self._selection_model, 0, 0, 0)

        self._selection_mode = False

        self._window.bind_property(
            "selection-mode", self, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL)

    def _on_list_view_setup(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        list_item.props.child = ArtistTile()

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
            return
        elif self._untouched_list is True:
            first_artist = model.get_item(0)
            if first_artist is None:
                return

            model.props.selected = 0
            self._on_artist_activated(self._sidebar, 0, True)
            return

        if removed == 0:
            return

        removed_artist = None
        artists = [coreartist.props.artist for coreartist in model]
        for artist in self._loaded_artists:
            if artist not in artists:
                removed_artist = artist
                break

        if removed_artist is None:
            return

        self._loaded_artists.remove(removed_artist)
        if self._artist_view.get_visible_child_name() == removed_artist:
            new_position = min(position, model.get_n_items() - 1)
            if new_position >= 0:
                model.props.selected = new_position
                self._on_artist_activated(self._sidebar, new_position, True)

        removed_artist_page = self._artist_view.get_child_by_name(
            removed_artist)
        self._artist_view.remove(removed_artist_page)

    @Gtk.Template.Callback()
    def _on_artist_activated(
            self, sidebar: Gtk.ListView, position: int,
            untouched: bool = False) -> None:
        """Initializes new artist album widgets"""
        # On application start the first row of ArtistView is activated
        # to show an intial artist. When this happens while any of the
        # views are in selection mode, this artist will be incorrectly
        # selected.
        # When selecting items check that the current visible view is
        # ArtistsView, to circumvent this issue.
        if (self.props.selection_mode
                and self._window.props.active_view is self):
            return

        if untouched is False:
            self._untouched_list = False

        coreartist = sidebar.get_model().get_item(position)

        # Prepare a new artist_albums_widget here
        if coreartist.props.artist in self._loaded_artists:
            scroll_vadjustment = self._artist_container.props.vadjustment
            scroll_vadjustment.props.value = 0.
            self._artist_view.set_visible_child_name(coreartist.props.artist)
            return

        artist_albums = ArtistAlbumsWidget(self._application)
        artist_albums.props.coreartist = coreartist

        self.bind_property(
            "selection-mode", artist_albums, "selection-mode",
            GObject.BindingFlags.SYNC_CREATE
            | GObject.BindingFlags.BIDIRECTIONAL)

        self._artist_view.add_named(artist_albums, coreartist.props.artist)
        scroll_vadjustment = self._artist_container.props.vadjustment
        scroll_vadjustment.props.value = 0.
        self._artist_view.set_visible_child(artist_albums)

        self._loaded_artists.append(coreartist.props.artist)

    @GObject.Property(type=bool, default=False)
    def selection_mode(self):
        """selection mode getter

        :returns: If selection mode is active
        :rtype: bool
        """
        return self._selection_mode

    @selection_mode.setter  # type: ignore
    def selection_mode(self, value):
        """selection-mode setter

        :param bool value: Activate selection mode
        """
        if (value == self._selection_mode
                or self._window.props.active_view is not self):
            return

        self._selection_mode = value
        self._sidebar.props.sensitive = not self._selection_mode
        if not self._selection_mode:
            self.deselect_all()

    def select_all(self) -> None:
        """Select all items"""
        coreartist = self._selection_model.get_selected_item()
        if coreartist:
            coreartist.props.selected = True

    def deselect_all(self) -> None:
        """Deselect all items"""
        coreartist = self._selection_model.get_selected_item()
        if coreartist:
            coreartist.props.selected = False
