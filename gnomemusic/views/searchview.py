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
from enum import IntEnum
from typing import Optional
import typing

from gi.repository import Adw, GObject, Gtk
from gettext import gettext as _

from gnomemusic.search import Search
from gnomemusic.utils import ArtSize
from gnomemusic.widgets.albumcover import AlbumCover
from gnomemusic.widgets.albumnavigationpage import AlbumNavigationPage
from gnomemusic.widgets.albumssearchnavigationpage import (
    AlbumsSearchNavigationPage)
from gnomemusic.widgets.artistnavigationpage import ArtistNavigationPage
from gnomemusic.widgets.artistsearchtile import ArtistSearchTile
from gnomemusic.widgets.artistssearchnavigationpage import (
    ArtistsSearchNavigationPage)
from gnomemusic.widgets.searchheaderbar import SearchHeaderBar
from gnomemusic.widgets.songwidget import SongWidget
from gnomemusic.widgets.songwidgetmenu import SongWidgetMenu
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.corealbum import CoreAlbum
    from gnomemusic.coresong import CoreSong


@Gtk.Template(resource_path="/org/gnome/Music/ui/SearchView.ui")
class SearchView(Adw.NavigationPage):
    """Gridlike view of search results.

    Three sections: artists, albums, songs.
    """

    __gtype_name__ = "SearchView"

    class State(IntEnum):
        """The different states of SearchView
        """
        MAIN = 0
        ALL_ALBUMS = 1
        ALL_ARTISTS = 2
        ALBUM = 3
        ARTIST = 4

    search_mode_active = GObject.Property(type=bool, default=False)
    search_state = GObject.Property(type=int, default=Search.State.NONE)
    search_text = GObject.Property(type=str)

    _album_header = Gtk.Template.Child()
    _album_flowbox = Gtk.Template.Child()
    _artist_header = Gtk.Template.Child()
    _artist_flowbox = Gtk.Template.Child()
    _search_results = Gtk.Template.Child()
    _search_toolbar_view = Gtk.Template.Child()
    _songs_header = Gtk.Template.Child()
    _songs_listbox = Gtk.Template.Child()
    _stack = Gtk.Template.Child()
    _status_page = Gtk.Template.Child()
    _view_all_albums = Gtk.Template.Child()
    _view_all_artists = Gtk.Template.Child()

    def __init__(self, application: Application) -> None:
        """Initialize SearchView

        :param GtkApplication application: The Application object
        """
        super().__init__()

        self.props.name = "search"

        self._application = application
        self._coremodel = application.props.coremodel
        self._model = self._coremodel.props.songs_search
        self._player = self._application.props.player
        self._window = application.props.window
        self._navigation_view = self._window.props.navigation_view
        self._headerbar = self._window.props.headerbar

        self._search_headerbar = SearchHeaderBar(self._application)
        self._search_toolbar_view.add_top_bar(self._search_headerbar)

        self.bind_property(
            "search-text", self._search_headerbar, "search-text")

        self.bind_property(
            "search-state", self._search_headerbar, "search-state",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self.connect(
            "notify::search-state", self._on_search_state_changed)

        self._navigation_view.connect(
            "replaced", self._on_navigation_view_replaced)

        self._album_model = self._coremodel.props.albums_search
        self._artist_model = self._coremodel.props.artists_search

        self._album_slice = Gtk.SliceListModel.new(self._album_model, 0, 8)
        self._artist_slice = Gtk.SliceListModel.new(self._artist_model, 0, 6)

        self._model.connect_after(
            "items-changed", self._on_model_items_changed)
        self._songs_listbox.bind_model(self._model, self._create_song_widget)
        self._on_model_items_changed(self._model, 0, 0, 0)

        self.bind_property(
            "search_mode_active", self._search_headerbar, "search_mode_active",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        self._album_slice.connect_after(
            "items-changed", self._on_album_model_items_changed)
        self._album_flowbox.bind_model(
            self._album_slice, self._create_album_cover)
        self._application.props.window.connect(
            "notify::default-width", self._on_window_width_change)

        self._artist_slice.connect_after(
            "items-changed", self._on_artist_model_items_changed)
        self._artist_flowbox.bind_model(
            self._artist_slice, self._create_artist_widget)

        self._scrolled_artist_window: Optional[Gtk.ScrolledWindow] = None

        self._set_empty_status_page()
        self._stack.props.visible_child_name = "status"

    def _create_song_widget(self, coresong: CoreSong) -> Gtk.ListBoxRow:
        song_widget = SongWidget(coresong, False, True)
        song_widget.props.show_song_number = False
        song_widget.props.menu = SongWidgetMenu(
            self._application, song_widget, coresong)

        return song_widget

    def _create_album_cover(self, corealbum: CoreAlbum) -> AlbumCover:
        album_cover = AlbumCover(corealbum)

        return album_cover

    def _create_artist_widget(self, coreartist):
        artist_tile = ArtistSearchTile(coreartist)

        return artist_tile

    def _on_album_model_items_changed(self, model, position, removed, added):
        items_found = model.get_n_items() > 0
        self._album_header.props.visible = items_found
        self._album_flowbox.props.visible = items_found
        self._check_visibility()

        nr_albums = self._album_model.get_n_items()
        self._view_all_albums.props.visible = (nr_albums > model.get_n_items())

    def _on_artist_model_items_changed(self, model, position, removed, added):
        items_found = model.get_n_items() > 0
        self._artist_header.props.visible = items_found
        self._artist_flowbox.props.visible = items_found
        self._check_visibility()

        nr_artists = self._artist_model.get_n_items()
        self._view_all_artists.props.visible = (
            nr_artists > model.get_n_items())

    def _on_model_items_changed(self, model, position, removed, added):
        items_found = model.get_n_items() > 0
        self._songs_header.props.visible = items_found
        self._songs_listbox.props.visible = items_found
        self._check_visibility()

    def _on_navigation_view_replaced(self, view: Adw.NavigationView) -> None:
        if view.props.visible_page.props.tag != self.props.tag:
            self.props.search_state = Search.State.NONE

    def _on_search_state_changed(
            self, searchview: SearchView, state: GObject.GParamInt) -> None:
        state = self.props.search_state

        if state == Search.State.RESULT:
            self._stack.props.visible_child_name = "main"
        elif state == Search.State.NONE:
            self._set_empty_status_page()
            self._stack.props.visible_child_name = "status"
        elif state == Search.State.NO_RESULT:
            self._set_no_result_status_page()
            self._stack.props.visible_child_name = "status"

    def _set_empty_status_page(self) -> None:
        self._status_page.props.title = _("No Search Started")
        self._status_page.props.description = _(
            "Use the searchbar to start searching for "
            "albums, artists or songs")

    def _set_no_result_status_page(self) -> None:
        self._status_page.props.title = _("No Results Found")
        self._status_page.props.description = _(
            "Try a different search")

    def _check_visibility(self):
        if not self.props.search_mode_active:
            return

        items_found = (self._model.get_n_items() > 0
                       or self._artist_model.get_n_items() > 0
                       or self._album_model.get_n_items() > 0)
        if items_found:
            self.props.search_state = Search.State.RESULT
        elif (not items_found
              and len(self.props.search_text) > 0):
            self.props.search_state = Search.State.NO_RESULT

    @Gtk.Template.Callback()
    def _song_activated(
            self, list_box: Gtk.ListBox, song_widget: SongWidget) -> bool:
        coresong = song_widget.props.coresong

        self._coremodel.props.active_core_object = coresong
        self._player.play(coresong)

        return True

    def _on_window_width_change(self, widget, value):
        allocation = self._album_flowbox.get_allocation()
        # FIXME: Just a bit of guesswork here.
        padding = 32
        items_per_row = allocation.width // (ArtSize.MEDIUM.width + padding)

        self._album_slice.props.size = 2 * items_per_row
        self._artist_slice.props.size = items_per_row

    @Gtk.Template.Callback()
    def _on_album_activated(self, widget, child, user_data=None):
        corealbum = child.props.corealbum
        album_page = AlbumNavigationPage(self._application, corealbum)
        self._navigation_view.push(album_page)

    @Gtk.Template.Callback()
    def _on_artist_activated(self, widget, child, user_data=None):
        coreartist = child.props.coreartist
        artist_page = ArtistNavigationPage(self._application, coreartist)
        self._navigation_view.push(artist_page)

    @Gtk.Template.Callback()
    def _on_all_artists_clicked(self, widget, user_data=None):
        all_artists_page = ArtistsSearchNavigationPage(
            self._application, self._artist_model)
        self._navigation_view.push(all_artists_page)

    @Gtk.Template.Callback()
    def _on_all_albums_clicked(self, widget, user_data=None):
        all_albums_page = AlbumsSearchNavigationPage(
            self._application, self._album_model)
        self._navigation_view.push(all_albums_page)
