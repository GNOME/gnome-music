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
from gettext import gettext as _
from typing import Optional
import typing

from gi.repository import GObject, Gtk

from gnomemusic.search import Search
from gnomemusic.utils import ArtSize
from gnomemusic.widgets.albumcover import AlbumCover
from gnomemusic.widgets.albumwidget import AlbumWidget
from gnomemusic.widgets.headerbar import HeaderBar
from gnomemusic.widgets.artistalbumswidget import ArtistAlbumsWidget
from gnomemusic.widgets.artistsearchtile import ArtistSearchTile
from gnomemusic.widgets.songwidget import SongWidget
from gnomemusic.widgets.songwidgetmenu import SongWidgetMenu
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.corealbum import CoreAlbum
    from gnomemusic.coresong import CoreSong


@Gtk.Template(resource_path="/org/gnome/Music/ui/SearchView.ui")
class SearchView(Gtk.Stack):
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

    search_state = GObject.Property(type=int, default=Search.State.NONE)
    selection_mode = GObject.Property(type=bool, default=False)
    state = GObject.Property(type=int, default=State.MAIN)
    title = GObject.Property(
        type=str, default="", flags=GObject.ParamFlags.READABLE)

    _album_header = Gtk.Template.Child()
    _album_flowbox = Gtk.Template.Child()
    _album_all_flowbox = Gtk.Template.Child()
    _all_search_results = Gtk.Template.Child()
    _artist_header = Gtk.Template.Child()
    _artist_all_flowbox = Gtk.Template.Child()
    _artist_flowbox = Gtk.Template.Child()
    _scrolled_album_widget = Gtk.Template.Child()
    _search_results = Gtk.Template.Child()
    _songs_header = Gtk.Template.Child()
    _songs_listbox = Gtk.Template.Child()
    _view_all_albums = Gtk.Template.Child()
    _view_all_artists = Gtk.Template.Child()

    def __init__(self, application: Application) -> None:
        """Initialize SearchView

        :param GtkApplication application: The Application object
        """
        super().__init__(transition_type=Gtk.StackTransitionType.CROSSFADE)

        self.props.name = "search"

        self._application = application
        self._coremodel = application.props.coremodel
        self._model = self._coremodel.props.songs_search
        self._player = self._application.props.player
        self._window = application.props.window
        self._headerbar = self._window._headerbar

        self._album_model = self._coremodel.props.albums_search
        self._artist_model = self._coremodel.props.artists_search

        self._album_slice = Gtk.SliceListModel.new(self._album_model, 0, 8)
        self._artist_slice = Gtk.SliceListModel.new(self._artist_model, 0, 6)

        self._model.connect_after(
            "items-changed", self._on_model_items_changed)
        self._songs_listbox.bind_model(self._model, self._create_song_widget)
        self._on_model_items_changed(self._model, 0, 0, 0)

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

        self.connect("notify::selection-mode", self._on_selection_mode_changed)

        self.bind_property(
            'selection-mode', self._window, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL)

        self._album_widget = AlbumWidget(self._application)
        self._album_widget.bind_property(
            "selection-mode", self, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL)
        viewport = self._scrolled_album_widget.get_first_child()
        viewport.set_child(self._album_widget)

        self._scrolled_artist_window: Optional[Gtk.ScrolledWindow] = None

        self._search_mode_active = False

    def _core_filter(self, coreitem, coremodel, nr_items):
        if coremodel.get_n_items() <= 5:
            return True

        for i in range(nr_items):
            if coremodel.get_item(i) == coreitem:
                return True

        return False

    def _create_song_widget(self, coresong: CoreSong) -> Gtk.ListBoxRow:
        song_widget = SongWidget(coresong, False, True)
        song_widget.props.show_song_number = False
        song_widget.props.menu = SongWidgetMenu(
            self._application, song_widget, coresong)

        self.bind_property(
            "selection-mode", song_widget, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        return song_widget

    def _create_album_cover(self, corealbum: CoreAlbum) -> AlbumCover:
        album_cover = AlbumCover(corealbum)
        album_cover.retrieve()

        self.bind_property(
            "selection-mode", album_cover, "selection-mode",
            GObject.BindingFlags.SYNC_CREATE
            | GObject.BindingFlags.BIDIRECTIONAL)

        # NOTE: Adding SYNC_CREATE here will trigger all the nested
        # models to be created. This will slow down initial start,
        # but will improve initial 'select all' speed.
        album_cover.bind_property(
            "selected", corealbum, "selected",
            GObject.BindingFlags.BIDIRECTIONAL)

        return album_cover

    def _create_artist_widget(self, coreartist):
        artist_tile = ArtistSearchTile(coreartist)

        self.bind_property(
            "selection-mode", artist_tile, "selection-mode",
            GObject.BindingFlags.SYNC_CREATE
            | GObject.BindingFlags.BIDIRECTIONAL)

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

    def _check_visibility(self):
        if not self.props.search_mode_active:
            return

        items_found = (self._model.get_n_items() > 0
                       or self._artist_model.get_n_items() > 0
                       or self._album_model.get_n_items() > 0)
        if items_found:
            self.props.search_state = Search.State.RESULT
        else:
            self.props.search_state = Search.State.NO_RESULT

    @Gtk.Template.Callback()
    def _song_activated(
            self, list_box: Gtk.ListBox, song_widget: SongWidget) -> bool:
        coresong = song_widget.props.coresong
        if self.props.selection_mode:
            selection_state = coresong.props.selected
            song_widget.props.selected = not selection_state
            coresong.props.selected = not selection_state
            return True

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
        if self.props.selection_mode:
            corealbum.props.selected = not corealbum.props.selected
            return

        # Update and display the album widget if not in selection mode
        self._album_widget.props.corealbum = corealbum

        self.props.state = SearchView.State.ALBUM
        self._headerbar.props.state = HeaderBar.State.SEARCH
        self._headerbar.set_label_title(
            corealbum.props.title, corealbum.props.artist)

        self.set_visible_child(self._scrolled_album_widget)
        self.props.search_mode_active = False

    @Gtk.Template.Callback()
    def _on_artist_activated(self, widget, child, user_data=None):
        coreartist = child.props.coreartist
        if self.props.selection_mode:
            return

        artist_albums_widget = ArtistAlbumsWidget(self._application)
        artist_albums_widget.props.coreartist = coreartist
        # FIXME: Recreating a view here. Alternate solution is used
        # in AlbumsView: one view created and an update function.
        # Settle on one design.
        self._scrolled_artist_window = Gtk.ScrolledWindow()
        self._scrolled_artist_window.props.child = artist_albums_widget
        self._scrolled_artist_window.props.visible = True
        self.add_child(self._scrolled_artist_window)
        artist_albums_widget.show()

        self.bind_property(
            "selection-mode", artist_albums_widget, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL)

        self.props.state = SearchView.State.ARTIST
        self._headerbar.props.state = HeaderBar.State.SEARCH
        self._headerbar.set_label_title(coreartist.props.artist, "")

        self.set_visible_child(self._scrolled_artist_window)
        self.props.search_mode_active = False

    @Gtk.Template.Callback()
    def _on_all_artists_clicked(self, widget, user_data=None):
        self.props.state = SearchView.State.ALL_ARTISTS
        self._headerbar.props.state = HeaderBar.State.SEARCH
        self._headerbar.set_label_title(_("Artists Results"), "")

        self._artist_all_flowbox.props.visible = True
        self._album_all_flowbox.props.visible = False
        self._artist_all_flowbox.bind_model(
            self._artist_model, self._create_artist_widget)

        self.props.visible_child = self._all_search_results
        self.props.search_mode_active = False

    @Gtk.Template.Callback()
    def _on_all_albums_clicked(self, widget, user_data=None):
        self.props.state = SearchView.State.ALL_ALBUMS
        self._headerbar.props.state = HeaderBar.State.SEARCH
        self._headerbar.set_label_title(_("Albums Results"), "")

        self._artist_all_flowbox.props.visible = False
        self._album_all_flowbox.props.visible = True
        self._album_all_flowbox.bind_model(
            self._album_model, self._create_album_cover)

        self.props.visible_child = self._all_search_results
        self.props.search_mode_active = False

    def _select_all(self, value: bool) -> None:
        if self.props.state == SearchView.State.MAIN:
            with self._model.freeze_notify():
                for coresong in self._model:
                    coresong.props.selected = value
                for corealbum in self._album_model:
                    corealbum.props.selected = value
                for coreartist in self._artist_model:
                    coreartist.props.selected = value
        elif self.props.state == SearchView.State.ALL_ALBUMS:
            with self._model.freeze_notify():
                for corealbum in self._album_model:
                    corealbum.props.selected = value
        elif self.props.state == SearchView.State.ALL_ARTISTS:
            with self._model.freeze_notify():
                for corealbum in self._album_model:
                    corealbum.props.selected = value
        elif self.props.state == SearchView.State.ALBUM:
            view = self._album_widget
            if value is True:
                view.select_all()
            else:
                view.deselect_all()
        elif self.props.state == SearchView.State.ARTIST:
            view = self.get_visible_child().get_child().get_child()
            if value is True:
                view.select_all()
            else:
                view.deselect_all()

    def select_all(self):
        self._select_all(True)

    def deselect_all(self):
        self._select_all(False)

    def _back_button_clicked(self, widget, data=None):
        if self.get_visible_child() == self._search_results:
            return
        elif self.get_visible_child() == self._scrolled_artist_window:
            self.remove(self._scrolled_artist_window)

        self.set_visible_child(self._search_results)
        self.props.search_mode_active = True
        self.props.state = SearchView.State.MAIN
        self._headerbar.props.state = HeaderBar.State.MAIN

    def _on_selection_mode_changed(self, widget, data=None):
        if (not self.props.selection_mode
                and self.get_parent().get_visible_child() == self):
            self.deselect_all()

    @GObject.Property(type=bool, default=False)
    def search_mode_active(self):
        """Get search mode status.

        :returns: the search mode status
        :rtype: bool
        """
        return self._search_mode_active

    @search_mode_active.setter  # type: ignore
    def search_mode_active(self, value):
        """Set search mode status.

        :param bool mode: new search mode
        """
        # FIXME: search_mode_active should not change search_state.
        # This is necessary because Search state cannot interact with
        # the child views.
        self._search_mode_active = value
        if (not self._search_mode_active
                and self.get_visible_child() == self._search_results):
            self.props.search_state = Search.State.NONE
