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

from gi.repository import Gdk, GObject, Gtk

from gnomemusic import log
from gnomemusic.player import PlayerPlaylist
from gnomemusic.utils import View
from gnomemusic.search import Search
from gnomemusic.widgets.albumcover import AlbumCover
from gnomemusic.widgets.albumwidget import AlbumWidget
from gnomemusic.widgets.headerbar import HeaderBar
from gnomemusic.widgets.artistalbumswidget import ArtistAlbumsWidget
from gnomemusic.widgets.artisttile import ArtistTile
from gnomemusic.widgets.songwidget import SongWidget


@Gtk.Template(resource_path="/org/gnome/Music/ui/SearchView.ui")
class SearchView(Gtk.Stack):
    """Gridlike view of search results.

    Three sections: artists, albums, songs.
    """

    __gtype_name__ = "SearchView"

    search_state = GObject.Property(type=int, default=Search.State.NONE)
    selected_items_count = GObject.Property(type=int, default=0, minimum=0)
    selection_mode = GObject.Property(type=bool, default=False)

    _album_flowbox = Gtk.Template.Child()
    _artist_listbox = Gtk.Template.Child()
    _search_results = Gtk.Template.Child()
    _songs_listbox = Gtk.Template.Child()

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

        self._songs_listbox.bind_model(self._model, self._create_song_widget)

        self._album_flowbox.bind_model(
            self._album_filter, self._create_album_widget)
        self._album_flowbox.connect(
            "child-activated", self._on_album_activated)

        self._artist_listbox.bind_model(
            self._artist_filter, self._create_artist_widget)

        self._player = self._application.props.player

        self._window = application.props.window
        self._headerbar = self._window._headerbar

        self.connect("notify::selection-mode", self._on_selection_mode_changed)

        self.bind_property(
            'selection-mode', self._window, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL)

        self.previous_view = None

        self._album_widget = AlbumWidget(player, self)
        self._album_widget.bind_property(
            "selection-mode", self, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL)

        self.show_all()
        self.add(self._album_widget)

        self._artist_albums_widget = None

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
        song_widget = SongWidget(coresong)

        self.bind_property(
            "selection-mode", song_widget, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        song_widget.connect('button-release-event', self._song_activated)

        song_widget.show_all()

        return song_widget

    def _create_album_widget(self, corealbum):
        album_widget = AlbumCover(corealbum)

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
        artist_tile = ArtistTile(coreartist)
        artist_tile.props.text = coreartist.props.artist
        artist_tile.connect('button-release-event', self._artist_activated)

        self.bind_property(
            "selection-mode", artist_tile, "selection-mode",
            GObject.BindingFlags.SYNC_CREATE
            | GObject.BindingFlags.BIDIRECTIONAL)

        return artist_tile

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

    @Gtk.Template.Callback()
    def _on_album_activated(self, widget, child, user_data=None):
        corealbum = child.props.corealbum
        if self.props.selection_mode:
            return

        # Update and display the album widget if not in selection mode
        self._album_widget.update(corealbum)

        self._headerbar.props.state = HeaderBar.State.SEARCH
        self._headerbar.props.title = corealbum.props.title
        self._headerbar.props.subtitle = corealbum.props.artist
        self.props.search_mode_active = False

        self.set_visible_child(self._album_widget)

    def _artist_activated(self, widget, event):
        coreartist = widget.coreartist

        mod_mask = Gtk.accelerator_get_default_mod_mask()
        if ((event.get_state() & mod_mask) == Gdk.ModifierType.CONTROL_MASK
                and not self.props.selection_mode):
            self.props.selection_mode = True
            return

        (_, button) = event.get_button()
        if (button == Gdk.BUTTON_PRIMARY
                and not self.props.selection_mode):
            # self.emit('song-activated', widget)

            self._artist_albums_widget = ArtistAlbumsWidget(
                coreartist, self._application, False)
            self.add(self._artist_albums_widget)
            self._artist_albums_widget.show()

            self.bind_property(
                'selection-mode', self._artist_albums_widget, 'selection-mode',
                GObject.BindingFlags.BIDIRECTIONAL)

            self._headerbar.props.state = HeaderBar.State.SEARCH
            self._headerbar.props.title = coreartist.artist
            self._headerbar.props.subtitle = None
            self.set_visible_child(self._artist_albums_widget)
            self.props.search_mode_active = False

        # FIXME: Need to ignore the event from the checkbox.
        # if self.props.selection_mode:
        #     widget.props.selected = not widget.props.selected

        return True

    def _select_all(self, value):
        with self._model.freeze_notify():
            def song_select(child):
                song_widget = child.get_child()
                song_widget.props.selected = value

            def album_select(child):
                child.props.selected = value

            def artist_select(child):
                artist_widget = child.get_child()
                artist_widget.props.selected = value

            self._songs_listbox.foreach(song_select)
            self._album_flowbox.foreach(album_select)
            self._artist_listbox.foreach(artist_select)

    def select_all(self):
        self._select_all(True)

    def unselect_all(self):
        self._select_all(False)

    @log
    def _back_button_clicked(self, widget, data=None):
        if self.get_visible_child() == self._artist_albums_widget:
            self._artist_albums_widget.destroy()
            self._artist_albums_widget = None
        elif self.get_visible_child() == self._search_results:
            self._window.views[View.ALBUM].set_visible_child(
                self._window.views[View.ALBUM]._grid)

        self.set_visible_child(self._search_results)
        self.props.search_mode_active = True
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
