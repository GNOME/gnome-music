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
from gnomemusic.views.baseview import BaseView
from gnomemusic.widgets.albumcover import AlbumCover
from gnomemusic.widgets.albumwidget import AlbumWidget
from gnomemusic.widgets.headerbar import HeaderBar
from gnomemusic.widgets.artistalbumswidget import ArtistAlbumsWidget
from gnomemusic.widgets.songwidget import SongWidget


class SearchView(BaseView):

    search_state = GObject.Property(type=int, default=Search.State.NONE)

    def __repr__(self):
        return '<SearchView>'

    @log
    def __init__(self, window, player):
        self._coremodel = window._app._coremodel
        self._model = self._coremodel.get_songs_search_model()
        self._album_model = self._coremodel.get_album_search_model()
        self._artist_model = self._coremodel.get_artist_search_model()
        super().__init__('search', None, window)

        self.player = player

        self.previous_view = None

        self._album_widget = AlbumWidget(player, self)
        self._album_widget.bind_property(
            "selection-mode", self, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL)

        self.add(self._album_widget)

        self._artist_albums_widget = None

        self._search_mode_active = False
        # self.connect("notify::search-state", self._on_search_state_changed)

    @log
    def _setup_view(self):
        view_container = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self._box.pack_start(view_container, True, True, 0)

        self._songs_listbox = Gtk.ListBox()
        self._songs_listbox.bind_model(self._model, self._create_song_widget)

        self._album_flowbox = Gtk.FlowBox(
            homogeneous=True, hexpand=True, halign=Gtk.Align.FILL,
            valign=Gtk.Align.START, selection_mode=Gtk.SelectionMode.NONE,
            margin=18, row_spacing=12, column_spacing=6,
            min_children_per_line=1, max_children_per_line=20, visible=True)
        self._album_flowbox.get_style_context().add_class('content-view')
        self._album_flowbox.bind_model(
            self._album_model, self._create_album_widget)
        self._album_flowbox.connect(
            "child-activated", self._on_album_activated)

        self._artist_listbox = Gtk.ListBox()
        self._artist_listbox.bind_model(
            self._artist_model, self._create_artist_widget)

        self._all_results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._all_results_box.pack_start(self._album_flowbox, True, True, 0)
        self._all_results_box.pack_start(self._artist_listbox, True, True, 0)
        self._all_results_box.pack_start(self._songs_listbox, True, True, 0)

        # self._ctrl = Gtk.GestureMultiPress().new(self._view)
        # self._ctrl.props.propagation_phase = Gtk.PropagationPhase.CAPTURE
        # self._ctrl.connect("released", self._on_view_clicked)

        view_container.add(self._all_results_box)

        self._box.show_all()

    def _create_song_widget(self, coresong):
        song_widget = SongWidget(coresong.props.media)
        song_widget.props.coresong = coresong

        coresong.bind_property(
            "favorite", song_widget, "favorite",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        coresong.bind_property(
            "selected", song_widget, "selected",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        coresong.bind_property(
            "state", song_widget, "state",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

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

    def _create_artist_widget(self, coresong):
        # FIXME: Hacky quick 'artist' widget. Needs its own tile.
        song_widget = SongWidget(coresong.props.media)
        song_widget._title_label.props.label = coresong.props.artist
        song_widget.props.show_duration = False
        song_widget.props.show_favorite = False
        song_widget.props.show_song_number = False
        song_widget.coreartist = coresong

        coresong.bind_property(
            "selected", song_widget, "selected",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        self.bind_property(
            "selection-mode", song_widget, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        song_widget.connect('button-release-event', self._artist_activated)

        song_widget.show_all()

        return song_widget

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

            self._coremodel.set_playlist_model(
                PlayerPlaylist.Type.SEARCH_RESULT, widget.props.coresong,
                self._model)
            self.player.play()

        # FIXME: Need to ignore the event from the checkbox.
        # if self.props.selection_mode:
        #     widget.props.selected = not widget.props.selected

        return True

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
                coreartist, self.player, self._window, False)
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

    def _child_select(self, child, value):
        widget = child.get_child()
        widget.props.selected = value

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
        elif self.get_visible_child() == self._grid:
            self._window.views[View.ALBUM].set_visible_child(
                self._window.views[View.ALBUM]._grid)

        self.set_visible_child(self._grid)
        self.props.search_mode_active = True
        self._headerbar.props.state = HeaderBar.State.MAIN

    @log
    def _on_view_clicked(self, gesture, n_press, x, y):
        """Ctrl+click on self._view triggers selection mode."""
        _, state = Gtk.get_current_event_state()
        modifiers = Gtk.accelerator_get_default_mod_mask()
        if (state & modifiers == Gdk.ModifierType.CONTROL_MASK
                and not self.props.selection_mode):
            self.props.selection_mode = True

        if (self.selection_mode
                and not self._star_handler.star_renderer_click):
            path, col, cell_x, cell_y = self._view.get_path_at_pos(x, y)
            iter_ = self.model.get_iter(path)
            self.model[iter_][6] = not self.model[iter_][6]
            selected_iters = self._get_selected_iters()

            self.props.selected_items_count = len(selected_iters)

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        super()._on_selection_mode_changed(widget, data)

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
                and self.get_visible_child() == self._grid):
            self.props.search_state = Search.State.NONE

    @log
    def _populate(self, data=None):
        self._init = True
        self._headerbar.props.state = HeaderBar.State.MAIN
