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

from enum import IntEnum
from gettext import gettext as _

from gi.repository import Gdk, GObject, Gtk

from gnomemusic import log
from gnomemusic.player import PlayerPlaylist
from gnomemusic.search import Search
from gnomemusic.widgets.albumcover import AlbumCover
from gnomemusic.widgets.albumwidget import AlbumWidget
from gnomemusic.widgets.headerbar import HeaderBar
from gnomemusic.widgets.artistalbumswidget import ArtistAlbumsWidget
from gnomemusic.widgets.artistsearchtile import ArtistSearchTile
from gnomemusic.widgets.songwidget import SongWidget


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
    selected_items_count = GObject.Property(type=int, default=0, minimum=0)
    selection_mode = GObject.Property(type=bool, default=False)
    state = GObject.Property(type=int, default=State.MAIN)

    _album_header = Gtk.Template.Child()
    _album_flowbox = Gtk.Template.Child()
    _album_all_flowbox = Gtk.Template.Child()
    _all_search_results = Gtk.Template.Child()
    _artist_header = Gtk.Template.Child()
    _artist_all_flowbox = Gtk.Template.Child()
    _artist_flowbox = Gtk.Template.Child()
    _search_results = Gtk.Template.Child()
    _songs_header = Gtk.Template.Child()
    _songs_listbox = Gtk.Template.Child()
    _view_all_albums = Gtk.Template.Child()
    _view_all_artists = Gtk.Template.Child()

    def __repr__(self):
        return '<SearchView>'

    @log
    def __init__(self, application, player=None):
        """Initialize SearchView

        :param GtkApplication application: The Application object
        """
        super().__init__(transition_type=Gtk.StackTransitionType.CROSSFADE)

        # FIXME: Make these properties.
        self.name = "search"
        self.title = None

        self._application = application
        self._coremodel = application.props.coremodel
        self._model = self._coremodel.props.songs_search
        self._album_model = self._coremodel.props.albums_search
        self._album_filter = self._coremodel.props.albums_search_filter
        self._album_filter.set_filter_func(
            self._core_filter, self._album_model, 12)

        self._artist_model = self._coremodel.props.artists_search
        self._artist_filter = self._coremodel.props.artists_search_filter
        self._artist_filter.set_filter_func(
            self._core_filter, self._artist_model, 6)

        self._model.connect_after(
            "items-changed", self._on_model_items_changed)
        self._songs_listbox.bind_model(self._model, self._create_song_widget)
        self._on_model_items_changed(self._model, 0, 0, 0)

        self._album_filter.connect_after(
            "items-changed", self._on_album_model_items_changed)
        self._album_flowbox.bind_model(
            self._album_filter, self._create_album_widget)
        self._album_flowbox.connect(
            "size-allocate", self._on_album_flowbox_size_allocate)
        self._on_album_model_items_changed(self._album_filter, 0, 0, 0)

        self._artist_filter.connect_after(
            "items-changed", self._on_artist_model_items_changed)
        self._artist_flowbox.bind_model(
            self._artist_filter, self._create_artist_widget)
        self._artist_flowbox.connect(
            "size-allocate", self._on_artist_flowbox_size_allocate)
        self._on_artist_model_items_changed(self._artist_filter, 0, 0, 0)

        self._player = self._application.props.player

        self._window = application.props.window
        self._headerbar = self._window._headerbar

        self.connect("notify::selection-mode", self._on_selection_mode_changed)

        self.bind_property(
            'selection-mode', self._window, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL)

        self._album_widget = AlbumWidget(player, self)
        self._album_widget.bind_property(
            "selection-mode", self, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL)

        self.add(self._album_widget)

        self._scrolled_artist_window = None

        self._search_mode_active = False
        # self.connect("notify::search-state", self._on_search_state_changed)

    def _core_filter(self, coreitem, coremodel, nr_items):
        if coremodel.get_n_items() <= 5:
            return True

        for i in range(nr_items):
            if coremodel.get_item(i) == coreitem:
                return True

        return False

    def _create_song_widget(self, coresong):
        song_widget = SongWidget(coresong, False, True)
        song_widget.props.show_song_number = False

        self.bind_property(
            "selection-mode", song_widget, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        song_widget.connect('button-release-event', self._song_activated)

        return song_widget

    def _create_album_widget(self, corealbum):
        album_widget = AlbumCover(corealbum)
        album_widget.retrieve()

        self.bind_property(
            "selection-mode", album_widget, "selection-mode",
            GObject.BindingFlags.SYNC_CREATE
            | GObject.BindingFlags.BIDIRECTIONAL)

        # NOTE: Adding SYNC_CREATE here will trigger all the nested
        # models to be created. This will slow down initial start,
        # but will improve initial 'selecte all' speed.
        album_widget.bind_property(
            "selected", corealbum, "selected",
            GObject.BindingFlags.BIDIRECTIONAL)

        return album_widget

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

        def set_child_visible(child):
            child.props.visible = True

        self._album_flowbox.foreach(set_child_visible)

    def _on_artist_model_items_changed(self, model, position, removed, added):
        items_found = model.get_n_items() > 0
        self._artist_header.props.visible = items_found
        self._artist_flowbox.props.visible = items_found
        self._check_visibility()

        nr_artists = self._artist_model.get_n_items()
        self._view_all_artists.props.visible = (
            nr_artists > model.get_n_items())

        def set_child_visible(child):
            child.props.visible = True

        self._artist_flowbox.foreach(set_child_visible)

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

    def _song_activated(self, widget, event):
        mod_mask = Gtk.accelerator_get_default_mod_mask()
        if ((event.get_state() & mod_mask) == Gdk.ModifierType.CONTROL_MASK
                and not self.props.selection_mode):
            self.props.selection_mode = True
            return

        (_, button) = event.get_button()
        if (button == Gdk.BUTTON_PRIMARY
                and not self.props.selection_mode):
            # self.emit('song-activated', widget)

            self._coremodel.set_player_model(
                PlayerPlaylist.Type.SEARCH_RESULT, self._model)
            self._player.play(widget.props.coresong)

        # FIXME: Need to ignore the event from the checkbox.
        # if self.props.selection_mode:
        #     widget.props.selected = not widget.props.selected

        return True

    def _on_album_flowbox_size_allocate(self, widget, allocation, data=None):
        nb_children = self._album_filter.get_n_items()
        if nb_children == 0:
            return

        first_child = self._album_flowbox.get_child_at_index(0)
        child_height = first_child.get_allocation().height
        if allocation.height > 2.5 * child_height:
            for i in range(nb_children - 1, -1, -1):
                child = self._album_flowbox.get_child_at_index(i)
                if child.props.visible is True:
                    child.props.visible = False
                    return

        children_hidden = False
        for idx in range(nb_children):
            child = self._album_flowbox.get_child_at_index(idx)
            if not child.props.visible:
                children_hidden = True
                break
        if children_hidden is False:
            return

        last_visible_child = self._album_flowbox.get_child_at_index(idx - 1)
        first_row_last = self._album_flowbox.get_child_at_index((idx - 1) // 2)
        second_row_pos = last_visible_child.get_allocation().x
        first_row_pos = first_row_last.get_allocation().x
        child_width = last_visible_child.get_allocation().width
        nb_children_to_add = (first_row_pos - second_row_pos) // child_width
        nb_children_to_add = min(nb_children_to_add + idx, nb_children)
        for i in range(idx, nb_children_to_add):
            child = self._album_flowbox.get_child_at_index(i)
            child.props.visible = True

    def _on_artist_flowbox_size_allocate(self, widget, allocation, data=None):
        nb_children = self._artist_filter.get_n_items()
        if nb_children == 0:
            return

        first_child = self._artist_flowbox.get_child_at_index(0)
        # FIXME: It looks like it is possible that the widget is not
        # yet created, resulting in a crash with first_child being
        # None.
        # Look for a cleaner solution.
        if first_child is None:
            return

        child_height = first_child.get_allocation().height
        if allocation.height > 1.5 * child_height:
            for i in range(nb_children - 1, -1, -1):
                child = self._artist_flowbox.get_child_at_index(i)
                if child.props.visible is True:
                    child.props.visible = False
                    return

        children_hidden = False
        for idx in range(nb_children):
            child = self._artist_flowbox.get_child_at_index(idx)
            if not child.props.visible:
                children_hidden = True
                break
        if children_hidden is False:
            return

        last_child = self._artist_flowbox.get_child_at_index(idx - 1)
        last_child_allocation = last_child.get_allocation()
        child_width = last_child_allocation.width
        if (last_child_allocation.x + 2 * child_width) < allocation.width:
            child = self._artist_flowbox.get_child_at_index(idx)
            child.props.visible = True

    @Gtk.Template.Callback()
    def _on_album_activated(self, widget, child, user_data=None):
        corealbum = child.props.corealbum
        if self.props.selection_mode:
            return

        # Update and display the album widget if not in selection mode
        self._album_widget.update(corealbum)

        self.props.state = SearchView.State.ALBUM
        self._headerbar.props.state = HeaderBar.State.SEARCH
        self._headerbar.props.title = corealbum.props.title
        self._headerbar.props.subtitle = corealbum.props.artist

        self.set_visible_child(self._album_widget)
        self.props.search_mode_active = False

    @Gtk.Template.Callback()
    def _on_artist_activated(self, widget, child, user_data=None):
        coreartist = child.props.coreartist
        if self.props.selection_mode:
            return

        artist_albums_widget = ArtistAlbumsWidget(
            coreartist, self._application, True)
        # FIXME: Recreating a view here. Alternate solution is used
        # in AlbumsView: one view created and an update function.
        # Settle on one design.
        self._scrolled_artist_window = Gtk.ScrolledWindow()
        self._scrolled_artist_window.add(artist_albums_widget)
        self._scrolled_artist_window.props.visible = True
        self.add(self._scrolled_artist_window)
        artist_albums_widget.show()

        self.bind_property(
            "selection-mode", artist_albums_widget, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL)

        self.props.state = SearchView.State.ARTIST
        self._headerbar.props.state = HeaderBar.State.SEARCH
        self._headerbar.props.title = coreartist.props.artist
        self._headerbar.props.subtitle = None

        self.set_visible_child(self._scrolled_artist_window)
        self.props.search_mode_active = False

    @Gtk.Template.Callback()
    def _on_all_artists_clicked(self, widget, event, user_data=None):
        self.props.state = SearchView.State.ALL_ARTISTS
        self._headerbar.props.state = HeaderBar.State.SEARCH
        self._headerbar.props.title = _("Artists Results")
        self._headerbar.props.subtitle = None

        self._artist_all_flowbox.props.visible = True
        self._album_all_flowbox.props.visible = False
        self._artist_all_flowbox.bind_model(
            self._artist_model, self._create_artist_widget)

        self.props.visible_child = self._all_search_results
        self.props.search_mode_active = False

    @Gtk.Template.Callback()
    def _on_all_albums_clicked(self, widget, event, user_data=None):
        self.props.state = SearchView.State.ALL_ALBUMS
        self._headerbar.props.state = HeaderBar.State.SEARCH
        self._headerbar.props.title = _("Albums Results")
        self._headerbar.props.subtitle = None

        self._artist_all_flowbox.props.visible = False
        self._album_all_flowbox.props.visible = True
        self._album_all_flowbox.bind_model(
            self._album_model, self._create_album_widget)

        self.props.visible_child = self._all_search_results
        self.props.search_mode_active = False

    def _select_all(self, value):
        def child_select(child):
            child.props.selected = value

        if self.props.state == SearchView.State.MAIN:
            with self._model.freeze_notify():
                def song_select(child):
                    song_widget = child.get_child()
                    song_widget.props.coresong.props.selected = value

                self._songs_listbox.foreach(song_select)
                self._album_flowbox.foreach(child_select)
                self._artist_flowbox.foreach(child_select)
        elif self.props.state == SearchView.State.ALL_ALBUMS:
            with self._model.freeze_notify():
                self._album_all_flowbox.foreach(child_select)
        elif self.props.state == SearchView.State.ALL_ARTISTS:
            with self._model.freeze_notify():
                self._artist_all_flowbox.foreach(child_select)
        elif self.props.state == SearchView.State.ALBUM:
            view = self.get_visible_child()
            if value is True:
                view.select_all()
            else:
                view.select_none()
        elif self.props.state == SearchView.State.ARTIST:
            view = self.get_visible_child().get_child().get_child()
            if value is True:
                view.select_all()
            else:
                view.select_none()

    def select_all(self):
        self._select_all(True)

    def unselect_all(self):
        self._select_all(False)

    @log
    def _back_button_clicked(self, widget, data=None):
        if self.get_visible_child() == self._search_results:
            return
        elif self.get_visible_child() == self._scrolled_artist_window:
            self.remove(self._scrolled_artist_window)
            self._scrolled_artist_window.destroy()
            self._scrolled_artist_window = None

        self.set_visible_child(self._search_results)
        self.props.search_mode_active = True
        self.props.state = SearchView.State.MAIN
        self._headerbar.props.state = HeaderBar.State.MAIN

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        if not self.props.selection_mode:
            self.unselect_all()

    @log
    def _on_search_state_changed(self, klass, param):
        # If a search is triggered when selection mode is activated,
        # reset the number of selected items.
        if (self.props.selection_mode
                and self.props.search_state != Search.State.NONE):
            self.props.selected_items_count = 0

    @GObject.Property(type=bool, default=False)
    def search_mode_active(self):
        """Get search mode status.

        :returns: the search mode status
        :rtype: bool
        """
        return self._search_mode_active

    @search_mode_active.setter
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
