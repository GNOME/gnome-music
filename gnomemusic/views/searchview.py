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
import gi
gi.require_version('Gd', '1.0')
from gi.repository import Gd, Gdk, GdkPixbuf, GObject, Grl, Gtk, Pango

from gnomemusic.albumartcache import Art
from gnomemusic.grilo import grilo
from gnomemusic import log
from gnomemusic.player import ValidationStatus, PlayerPlaylist
from gnomemusic.query import Query
from gnomemusic.utils import View
from gnomemusic.search import Search
from gnomemusic.views.baseview import BaseView
from gnomemusic.widgets.headerbar import HeaderBar
from gnomemusic.widgets.artistalbumswidget import ArtistAlbumsWidget
from gnomemusic.widgets.songwidget import SongWidget
import gnomemusic.utils as utils


class SearchView(BaseView):

    search_state = GObject.Property(type=int, default=Search.State.NONE)

    def __repr__(self):
        return '<SearchView>'

    @log
    def __init__(self, window, player):
        self._coremodel = window._app._coremodel
        self._model = self._coremodel.get_songs_search_model()
        super().__init__('search', None, window)

        # self._add_list_renderers()
        self.player = player
        self._head_iters = [None, None, None, None]
        self._filter_model = None

        self.previous_view = None

        self._albums_selected = []
        self._albums = {}
        self._albums_index = 0

        # self._album_widget = AlbumWidget(player)
        # self._album_widget.bind_property(
        #     "selection-mode", self, "selection-mode",
        #     GObject.BindingFlags.BIDIRECTIONAL)
        # self._album_widget.bind_property(
        #     "selected-items-count", self, "selected-items-count")

        # self.add(self._album_widget)

        self._artists_albums_selected = []
        self._artists_albums_index = 0
        self._artists = {}
        self._artist_albums_widget = None

        self._items_selected = []
        self._items_selected_callback = None

        self._items_found = None

        self._search_mode_active = False
        # self.connect("notify::search-state", self._on_search_state_changed)

    @log
    def _setup_view(self):
        view_container = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self._box.pack_start(view_container, True, True, 0)

        self._songs_listbox = Gtk.ListBox()
        self._songs_listbox.bind_model(self._model, self._create_song_widget)

        self._all_results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._all_results_box.pack_start(self._songs_listbox, True, True, 0)

        # self._view = Gtk.TreeView(
        #     activate_on_single_click=True, can_focus=False,
        #     halign=Gtk.Align.CENTER, headers_visible=False,
        #     show_expanders=False, width_request=530)
        # self._view.get_style_context().add_class('view')
        # self._view.get_style_context().add_class('content-view')
        # self._view.get_selection().props.mode = Gtk.SelectionMode.NONE
        # self._view.connect('row-activated', self._on_item_activated)

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
                PlayerPlaylist.Type.SEARCH_RESULT, None, widget.props.coresong,
                self._model)
            self.player.play()

        # FIXME: Need to ignore the event from the checkbox.
        # if self.props.selection_mode:
        #     widget.props.selected = not widget.props.selected

        return True

    def select_all(self):
        with self._model.freeze_notify():
            def child_select_all(child):
                song_widget = child.get_child()
                song_widget.props.selected = True

            self._songs_listbox.foreach(child_select_all)

    def unselect_all(self):
        with self._model.freeze_notify():
            def child_select_none(child):
                song_widget = child.get_child()
                song_widget.props.selected = False

            self._songs_listbox.foreach(child_select_none)

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
    def _on_item_activated(self, treeview, path, column):
        if self._star_handler.star_renderer_click:
            self._star_handler.star_renderer_click = False
            return

        if self.props.selection_mode:
            return

        try:
            child_path = self._filter_model.convert_path_to_child_path(path)
        except TypeError:
            return

        _iter = self.model.get_iter(child_path)
        if self.model[_iter][12] == 'album':
            title = self.model[_iter][2]
            artist = self.model[_iter][3]
            item = self.model[_iter][5]

            self._album_widget.update(item)
            self._headerbar.props.state = HeaderBar.State.SEARCH

            self._headerbar.props.title = title
            self._headerbar.props.subtitle = artist
            self.set_visible_child(self._album_widget)
            self.props.search_mode_active = False

        elif self.model[_iter][12] == 'artist':
            artist = self.model[_iter][2]
            albums = self._artists[artist.casefold()]['albums']

            self._artist_albums_widget = ArtistAlbumsWidget(
                artist, albums, self.player, self._window, True)
            self.add(self._artist_albums_widget)
            self._artist_albums_widget.show()

            self._artist_albums_widget.bind_property(
                'selected-items-count', self, 'selected-items-count')
            self.bind_property(
                'selection-mode', self._artist_albums_widget, 'selection-mode',
                GObject.BindingFlags.BIDIRECTIONAL)

            self._headerbar.props.state = HeaderBar.State.SEARCH
            self._headerbar.props.title = artist
            self._headerbar.props.subtitle = None
            self.set_visible_child(self._artist_albums_widget)
            self.props.search_mode_active = False
        elif self.model[_iter][12] == 'song':
            if self.model[_iter][11] != ValidationStatus.FAILED:
                c_iter = self._songs_model.convert_child_iter_to_iter(_iter)[1]
                self.player.set_playlist(
                    PlayerPlaylist.Type.SEARCH_RESULT, None, self._songs_model,
                    c_iter)
                self.player.play()
        else:  # Headers
            if self._view.row_expanded(path):
                self._view.collapse_row(path)
            else:
                self._view.expand_row(path, False)

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
    def _get_selected_iters(self):
        iters = []
        for row in self.model:
            iter_child = self.model.iter_children(row.iter)
            while iter_child is not None:
                if self.model[iter_child][6]:
                    iters.append(iter_child)
                iter_child = self.model.iter_next(iter_child)
        return iters

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        super()._on_selection_mode_changed(widget, data)
        return

        col = self._view.get_columns()[0]
        cells = col.get_cells()
        cells[4].props.visible = self.props.selection_mode
        col.queue_resize()

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
    def _add_search_item(self, source, param, item, remaining=0, data=None):
        if not item:
            if (grilo._search_callback_counter == 0
                    and grilo.search_source):
                self.props.search_state = Search.State.NO_RESULT
            return

        if data != self.model:
            return

        artist = utils.get_artist_name(item)
        album = utils.get_album_title(item)

        key = '%s-%s' % (artist, album)
        if key not in self._albums:
            self._albums[key] = Grl.Media()
            self._albums[key].set_title(album)
            self._albums[key].add_artist(artist)
            self._albums[key].set_source(source.get_id())
            self._albums[key].songs = []
            self._add_item(
                source, None, self._albums[key], 0, [self.model, 'album'])
            self._add_item(
                source, None, self._albums[key], 0, [self.model, 'artist'])

        self._albums[key].songs.append(item)
        self._add_item(source, None, item, 0, [self.model, 'song'])

    @log
    def _retrieval_finished(self, klass, model, _iter):
        if not model[_iter][13]:
            return

        model[_iter][13] = klass.surface

    @log
    def _add_item(self, source, param, item, remaining=0, data=None):
        if data is None:
            return

        model, category = data

        self._items_found = (
            self.model.iter_n_children(self._head_iters[0])
            + self.model.iter_n_children(self._head_iters[1])
            + self.model.iter_n_children(self._head_iters[2])
            + self.model.iter_n_children(self._head_iters[3])
        )

        # We need to remember the view before the search view
        emptysearchview = self._window.views[View.EMPTY]
        if (self._window.curr_view != emptysearchview
                and self._window.prev_view != emptysearchview):
            self.previous_view = self._window.prev_view

        if self._items_found == 0:
            self.props.search_state = Search.State.NO_RESULT
        else:
            self.props.search_state = Search.State.RESULT

        if remaining == 0:
            self._window.notifications_popup.pop_loading()
            self._view.show()

        if not item or model != self.model:
            return

        self._offset += 1
        title = utils.get_media_title(item)
        item.set_title(title)
        artist = utils.get_artist_name(item)

        group = 3
        try:
            group = {'album': 0, 'artist': 1, 'song': 2}[category]
        except KeyError:
            pass

        _iter = None
        if category == 'album':
            _iter = self.model.insert_with_values(
                self._head_iters[group], -1, [0, 2, 3, 5, 9, 12],
                [str(item.get_id()), title, artist, item, 2,
                 category])
        elif category == 'song':
            # FIXME: source specific hack
            if source.get_id() != 'grl-tracker-source':
                fav = 2
            else:
                fav = item.get_favourite()
            _iter = self.model.insert_with_values(
                self._head_iters[group], -1, [0, 2, 3, 5, 9, 12],
                [str(item.get_id()), title, artist, item, fav,
                 category])
        else:
            if not artist.casefold() in self._artists:
                _iter = self.model.insert_with_values(
                    self._head_iters[group], -1, [0, 2, 5, 9, 12],
                    [str(item.get_id()), artist, item, 2,
                     category])
                self._artists[artist.casefold()] = {
                    'iter': _iter,
                    'albums': []
                }
            self._artists[artist.casefold()]['albums'].append(item)

        # FIXME: Figure out why iter can be None here, seems illogical.
        if _iter is not None:
            scale = self._view.get_scale_factor()
            art = Art(Art.Size.SMALL, item, scale)
            self.model[_iter][13] = art.surface
            art.connect(
                'finished', self._retrieval_finished, self.model, _iter)
            art.lookup()

        if self.model.iter_n_children(self._head_iters[group]) == 1:
            path = self.model.get_path(self._head_iters[group])
            path = self._filter_model.convert_child_path_to_path(path)
            self._view.expand_row(path, False)

    @log
    def _add_list_renderers(self):
        column = Gtk.TreeViewColumn()

        # Add our own surface renderer, instead of the one provided by
        # Gd. This avoids us having to set the model to a cairo.Surface
        # which is currently not a working solution in pygobject.
        # https://gitlab.gnome.org/GNOME/pygobject/issues/155
        pixbuf_renderer = Gtk.CellRendererPixbuf(
            xalign=0.5, yalign=0.5, xpad=12, ypad=2)
        column.pack_start(pixbuf_renderer, False)
        column.set_cell_data_func(
            pixbuf_renderer, self._on_list_widget_pixbuf_renderer)
        column.add_attribute(pixbuf_renderer, 'surface', 13)

        # With the bugfix in libgd 9117650bda, the search results
        # stopped aligning at the top. With the artists results not
        # having a second line of text, this looks off.
        # Revert to old behaviour by forcing the alignment to be top.
        two_lines_renderer = Gd.TwoLinesRenderer(
            wrap_mode=Pango.WrapMode.WORD_CHAR, xpad=12, xalign=0.0,
            yalign=0, text_lines=2)
        column.pack_start(two_lines_renderer, True)
        column.set_cell_data_func(
            two_lines_renderer, self._on_list_widget_two_lines_renderer)
        column.add_attribute(two_lines_renderer, 'text', 2)
        column.add_attribute(two_lines_renderer, 'line_two', 3)

        title_renderer = Gtk.CellRendererText(
            xpad=12, xalign=0.0, yalign=0.5, height=32,
            ellipsize=Pango.EllipsizeMode.END, weight=Pango.Weight.BOLD)
        column.pack_start(title_renderer, False)
        column.set_cell_data_func(
            title_renderer, self._on_list_widget_title_renderer)
        column.add_attribute(title_renderer, 'text', 2)

        self._star_handler.add_star_renderers(column)

        selection_renderer = Gtk.CellRendererToggle(xpad=12, xalign=1.0)
        column.pack_start(selection_renderer, False)
        column.set_cell_data_func(
            selection_renderer, self._on_list_widget_selection_renderer)
        column.add_attribute(selection_renderer, 'active', 6)

        self._view.append_column(column)

    @log
    def _is_header(self, model, iter_):
        return model.iter_parent(iter_) is None

    @log
    def _on_list_widget_title_renderer(self, col, cell, model, iter_, data):
        cell.props.visible = self._is_header(model, iter_)

    @log
    def _on_list_widget_pixbuf_renderer(self, col, cell, model, iter_, data):
        if (not model[iter_][13]
                or self._is_header(model, iter_)):
            cell.props.visible = False
            return

        cell.props.surface = model[iter_][13]
        cell.props.visible = True

    @log
    def _on_list_widget_two_lines_renderer(
            self, col, cell, model, iter_, data):
        if self._is_header(model, iter_):
            cell.props.visible = False
            return

        cell.props.visible = True

    @log
    def _on_list_widget_selection_renderer(
            self, col, cell, model, iter_, data):
        if (self.props.selection_mode
                and not self._is_header(model, iter_)):
            cell.props.visible = True
        else:
            cell.props.visible = False

    @log
    def _populate(self, data=None):
        self._init = True
        self._headerbar.props.state = HeaderBar.State.MAIN

    @log
    def get_selected_songs(self, callback):
        if self.get_visible_child() == self._album_widget:
            callback(self._album_widget.get_selected_songs())
        elif self.get_visible_child() == self._artist_albums_widget:
            callback(self._artist_albums_widget.get_selected_songs())
        else:
            self._albums_index = 0
            self._artists_albums_index = 0
            self._items_selected = []
            self._items_selected_callback = callback
            self._get_selected_albums()

    @log
    def _get_selected_albums(self):
        selected_iters = self._get_selected_iters()

        self._albums_selected = [
            self.model[iter_][5]
            for iter_ in selected_iters
            if self.model[iter_][12] == 'album']

        if len(self._albums_selected):
            self._get_selected_albums_songs()
        else:
            self._get_selected_artists()

    @log
    def _get_selected_albums_songs(self):
        grilo.populate_album_songs(
            self._albums_selected[self._albums_index],
            self._add_selected_albums_songs)
        self._albums_index += 1

    @log
    def _add_selected_albums_songs(
            self, source, param, item, remaining=0, data=None):
        if item:
            self._items_selected.append(item)
        if remaining == 0:
            if self._albums_index < len(self._albums_selected):
                self._get_selected_albums_songs()
            else:
                self._get_selected_artists()

    @log
    def _get_selected_artists(self):
        selected_iters = self._get_selected_iters()

        artists_selected = [
            self._artists[self.model[iter_][2].casefold()]
            for iter_ in selected_iters
            if self.model[iter_][12] == 'artist']

        self._artists_albums_selected = []
        for artist in artists_selected:
            self._artists_albums_selected.extend(artist['albums'])

        if len(self._artists_albums_selected):
            self._get_selected_artists_albums_songs()
        else:
            self._get_selected_songs()

    @log
    def _get_selected_artists_albums_songs(self):
        grilo.populate_album_songs(
            self._artists_albums_selected[self._artists_albums_index],
            self._add_selected_artists_albums_songs)
        self._artists_albums_index += 1

    @log
    def _add_selected_artists_albums_songs(
            self, source, param, item, remaining=0, data=None):
        if item:
            self._items_selected.append(item)
        if remaining == 0:
            artist_albums = len(self._artists_albums_selected)
            if self._artists_albums_index < artist_albums:
                self._get_selected_artists_albums_songs()
            else:
                self._get_selected_songs()

    @log
    def _get_selected_songs(self):
        selected_iters = self._get_selected_iters()
        self._items_selected.extend([
            self.model[iter_][5]
            for iter_ in selected_iters
            if self.model[iter_][12] == 'song'])
        self._items_selected_callback(self._items_selected)

    @log
    def _filter_visible_func(self, model, _iter, data=None):
        top_level = model.iter_parent(_iter) is None
        visible = (not top_level or model.iter_has_child(_iter))

        return visible

    @log
    def set_search_text(self, search_term, fields_filter):
        return

        query_matcher = {
            'album': {
                'search_all': Query.get_albums_with_any_match,
                'search_artist': Query.get_albums_with_artist_match,
                'search_composer': Query.get_albums_with_composer_match,
                'search_album': Query.get_albums_with_album_match,
                'search_track': Query.get_albums_with_track_match,
            },
            'artist': {
                'search_all': Query.get_artists_with_any_match,
                'search_artist': Query.get_artists_with_artist_match,
                'search_composer': Query.get_artists_with_composer_match,
                'search_album': Query.get_artists_with_album_match,
                'search_track': Query.get_artists_with_track_match,
            },
            'song': {
                'search_all': Query.get_songs_with_any_match,
                'search_artist': Query.get_songs_with_artist_match,
                'search_composer': Query.get_songs_with_composer_match,
                'search_album': Query.get_songs_with_album_match,
                'search_track': Query.get_songs_with_track_match,
            },
        }

        self.model = Gtk.TreeStore(
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,    # item title or header text
            GObject.TYPE_STRING,    # artist for albums and songs
            GdkPixbuf.Pixbuf,       # Gd placeholder album art
            GObject.TYPE_OBJECT,    # item
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT,
            GObject.TYPE_STRING,
            GObject.TYPE_INT,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT,       # validation status
            GObject.TYPE_STRING,    # type
            object                  # album art surface
        )

        self._filter_model = self.model.filter_new(None)
        self._filter_model.set_visible_func(self._filter_visible_func)
        self._view.set_model(self._filter_model)

        self._albums = {}
        self._artists = {}

        if search_term == "":
            return

        albums_iter = self.model.insert_with_values(
            None, -1, [2, 9], [_("Albums"), 2])
        artists_iter = self.model.insert_with_values(
            None, -1, [2, 9], [_("Artists"), 2])
        songs_iter = self.model.insert_with_values(
            None, -1, [2, 9], [_("Songs"), 2])
        playlists_iter = self.model.insert_with_values(
            None, -1, [2, 9], [_("Playlists"), 2])

        self._head_iters = [
            albums_iter,
            artists_iter,
            songs_iter,
            playlists_iter
        ]

        self._songs_model = self.model.filter_new(
            self.model.get_path(songs_iter))

        # Use queries for Tracker
        if (not grilo.search_source
                or grilo.search_source.get_id() == 'grl-tracker-source'):
            for category in ('album', 'artist', 'song'):
                query = query_matcher[category][fields_filter](search_term)
                self._window.notifications_popup.push_loading()
                grilo.populate_custom_query(
                    query, self._add_item, -1, [self.model, category])
        if (not grilo.search_source
                or grilo.search_source.get_id() != 'grl-tracker-source'):
            # nope, can't do - reverting to Search
            grilo.search(search_term, self._add_search_item, self.model)
