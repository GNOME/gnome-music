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
from gi.repository import Gd, Gdk, GdkPixbuf, GObject, Grl, Gtk, Pango

from gnomemusic.albumartcache import DefaultIcon, ArtSize
from gnomemusic.grilo import grilo
from gnomemusic import log
from gnomemusic.player import DiscoveryStatus
from gnomemusic.playlists import Playlists
from gnomemusic.query import Query
from gnomemusic.toolbar import ToolbarState
from gnomemusic.views.baseview import BaseView
from gnomemusic.widgets.albumwidget import AlbumWidget
from gnomemusic.widgets.artistalbumswidget import ArtistAlbumsWidget
import gnomemusic.utils as utils

playlists = Playlists.get_default()


class SearchView(BaseView):

    __gsignals__ = {
        'no-music-found': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __repr__(self):
        return '<SearchView>'

    @log
    def __init__(self, window, player):
        BaseView.__init__(self, 'search', None, window, Gd.MainViewType.LIST)

        scale = self.get_scale_factor()
        loading_icon_surface = DefaultIcon(scale).get(
            DefaultIcon.Type.loading, ArtSize.small)
        self._loading_icon = Gdk.pixbuf_get_from_surface(
            loading_icon_surface, 0, 0, loading_icon_surface.get_width(),
            loading_icon_surface.get_height())

        self._add_list_renderers()
        self.player = player
        self._head_iters = [None, None, None, None]
        self._filter_model = None

        self.previous_view = None
        self.connect('no-music-found', self._no_music_found_callback)

        self._albums_selected = []
        self._albums = {}
        self._albums_index = 0
        self._albumWidget = AlbumWidget(player, self)
        self.add(self._albumWidget)

        self._artists_albums_selected = []
        self._artists_albums_index = 0
        self._artists = {}
        self._artistAlbumsWidget = None

        self._view.get_generic_view().set_show_expanders(False)
        self._items_selected = []
        self._items_selected_callback = None

        self._items_found = None

    @log
    def _no_music_found_callback(self, view):
        # FIXME: call into private members
        self._window._stack.set_visible_child_name('emptysearch')
        emptysearch = self._window._stack.get_child_by_name('emptysearch')
        emptysearch._artistAlbumsWidget = self._artistAlbumsWidget

    @log
    def _back_button_clicked(self, widget, data=None):
        self._header_bar.searchbar.show_bar(True, False)

        if self.get_visible_child() == self._artistAlbumsWidget:
            self._artistAlbumsWidget.destroy()
            self._artistAlbumsWidget = None
        elif self.get_visible_child() == self._grid:
            self._window.views[0].set_visible_child(
                self._window.views[0]._grid)

        self.set_visible_child(self._grid)
        self._window.toolbar.set_state(ToolbarState.MAIN)

    @log
    def _on_item_activated(self, widget, id, path):
        if self._star_handler.star_renderer_click:
            self._star_handler.star_renderer_click = False
            return

        try:
            child_path = self._filter_model.convert_path_to_child_path(path)
        except TypeError:
            return

        _iter = self.model.get_iter(child_path)
        if self.model[_iter][11] == 'album':
            title = self.model[_iter][2]
            artist = self.model[_iter][3]
            item = self.model[_iter][5]

            self._albumWidget.update(
                artist, title, item, self._header_bar, self._selection_toolbar)
            self._header_bar.set_state(ToolbarState.SEARCH_VIEW)

            self._header_bar.header_bar.set_title(title)
            self._header_bar.header_bar.sub_title = artist
            self.set_visible_child(self._albumWidget)
            self._header_bar.searchbar.show_bar(False)
        elif self.model[_iter][11] == 'artist':
            artist = self.model[_iter][2]
            albums = self._artists[artist.casefold()]['albums']

            self._artistAlbumsWidget = ArtistAlbumsWidget(
                artist, albums, self.player, self._header_bar,
                self._selection_toolbar, self._window, True)
            self.add(self._artistAlbumsWidget)
            self._artistAlbumsWidget.show()

            self._header_bar.set_state(ToolbarState.SEARCH_VIEW)
            self._header_bar.header_bar.set_title(artist)
            self.set_visible_child(self._artistAlbumsWidget)
            self._header_bar.searchbar.show_bar(False)
        elif self.model[_iter][11] == 'song':
            if self.model[_iter][12] != DiscoveryStatus.FAILED:
                c_iter = self._songs_model.convert_child_iter_to_iter(_iter)[1]
                self.player.set_playlist(
                    'Search Results', None, self._songs_model, c_iter, 5, 12)
                self.player.set_playing(True)
        else:  # Headers
            if self._view.get_generic_view().row_expanded(path):
                self._view.get_generic_view().collapse_row(path)
            else:
                self._view.get_generic_view().expand_row(path, False)

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        if (self._artistAlbumsWidget is not None
                and self.get_visible_child() == self._artistAlbumsWidget):
            self._artistAlbumsWidget.set_selection_mode(
                self._header_bar._selectionMode)

    @log
    def _add_search_item(self, source, param, item, remaining=0, data=None):
        if not item:
            if (grilo._search_callback_counter == 0
                    and grilo.search_source):
                self.emit('no-music-found')
            return

        if data != self.model:
            return

        artist = utils.get_artist_name(item)
        album = utils.get_album_title(item)
        composer = item.get_composer()

        key = '%s-%s' % (artist, album)
        if key not in self._albums:
            self._albums[key] = Grl.Media()
            self._albums[key].set_title(album)
            self._albums[key].add_artist(artist)
            self._albums[key].set_composer(composer)
            self._albums[key].set_source(source.get_id())
            self._albums[key].songs = []
            self._add_item(
                source, None, self._albums[key], 0, [self.model, 'album'])
            self._add_item(
                source, None, self._albums[key], 0, [self.model, 'artist'])

        self._albums[key].songs.append(item)
        self._add_item(source, None, item, 0, [self.model, 'song'])

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

        if (category == 'song'
                and self._items_found == 0
                and remaining == 0):
            if grilo.search_source:
                self.emit('no-music-found')

        # We need to remember the view before the search view
        if (self._window.curr_view != self._window.views[5]
                and self._window.prev_view != self._window.views[5]):
            self.previous_view = self._window.prev_view

        if remaining == 0:
            self._window.pop_loading_notification()
            self._view.show()

        if not item or model != self.model:
            return

        self._offset += 1
        title = utils.get_media_title(item)
        item.set_title(title)
        artist = utils.get_artist_name(item)
        # FIXME: Can't be None in treemodel
        composer = item.get_composer() or ""

        group = 3
        try:
            group = {'album': 0, 'artist': 1, 'song': 2}[category]
        except:
            pass

        # FIXME: HiDPI icon lookups return a surface that can't be
        # scaled by GdkPixbuf, so it results in a * scale factor sized
        # icon for the search view.
        _iter = None
        if category == 'album':
            _iter = self.model.insert_with_values(
                self._head_iters[group], -1, [0, 2, 3, 4, 5, 9, 11, 13],
                [str(item.get_id()), title, artist, self._loading_icon, item,
                 2, category, composer])
            self._cache.lookup(
                item, ArtSize.small, self._on_lookup_ready, _iter)
        elif category == 'song':
            # FIXME: source specific hack
            if source.get_id() != 'grl-tracker-source':
                fav = 2
            else:
                fav = item.get_favourite()
            _iter = self.model.insert_with_values(
                self._head_iters[group], -1, [0, 2, 3, 4, 5, 9, 11, 13],
                [str(item.get_id()), title, artist, self._loading_icon, item,
                 fav, category, composer])
            self._cache.lookup(
                item, ArtSize.small, self._on_lookup_ready, _iter)
        else:
            if not artist.casefold() in self._artists:
                _iter = self.model.insert_with_values(
                    self._head_iters[group], -1, [0, 2, 4, 5, 9, 11, 13],
                    [str(item.get_id()), artist, self._loading_icon, item, 2,
                     category, composer])
                self._cache.lookup(
                    item, ArtSize.small, self._on_lookup_ready, _iter)
                self._artists[artist.casefold()] = {
                    'iter': _iter,
                    'albums': []
                }

            self._artists[artist.casefold()]['albums'].append(item)

        if self.model.iter_n_children(self._head_iters[group]) == 1:
            path = self.model.get_path(self._head_iters[group])
            path = self._filter_model.convert_child_path_to_path(path)
            self._view.get_generic_view().expand_row(path, False)

    @log
    def _add_list_renderers(self):
        list_widget = self._view.get_generic_view()
        list_widget.set_halign(Gtk.Align.CENTER)
        list_widget.set_size_request(530, -1)
        cols = list_widget.get_columns()

        title_renderer = Gtk.CellRendererText(
            xpad=12, xalign=0.0, yalign=0.5, height=32,
            ellipsize=Pango.EllipsizeMode.END, weight=Pango.Weight.BOLD)
        list_widget.add_renderer(
            title_renderer, self._on_list_widget_title_render, None)
        cols[0].add_attribute(title_renderer, 'text', 2)

        self._star_handler.add_star_renderers(list_widget, cols[0])

        cells = cols[0].get_cells()
        cols[0].reorder(cells[0], -1)
        cols[0].set_cell_data_func(
            cells[0], self._on_list_widget_selection_render, None)

    def _on_list_widget_selection_render(self, col, cell, model, _iter, data):
        if (self._view.get_selection_mode()
                and model.iter_parent(_iter) is not None):
            cell.set_visible(True)
        else:
            cell.set_visible(False)

    def _on_list_widget_title_render(self, col, cell, model, _iter, data):
        cells = col.get_cells()
        cells[0].set_visible(model.iter_parent(_iter) is not None)
        cells[1].set_visible(model.iter_parent(_iter) is not None)
        cells[2].set_visible(model.iter_parent(_iter) is None)

    @log
    def populate(self):
        self._init = True
        self._window.push_loading_notification()
        self._header_bar.set_state(ToolbarState.MAIN)

    @log
    def get_selected_songs(self, callback):
        if self.get_visible_child() == self._albumWidget:
            callback(self._albumWidget.view.get_selected_items())
        elif self.get_visible_child() == self._artistAlbumsWidget:
            items = []
            # FIXME: calling into private model
            for row in self._artistAlbumsWidget._model:
                if row[6]:
                    items.append(row[5])
            callback(items)
        else:
            self._items_selected = []
            self._items_selected_callback = callback
            self._get_selected_albums()

    @log
    def _get_selected_albums(self):
        paths = [
            self._filter_model.convert_path_to_child_path(path)
            for path in self._view.get_selection()]

        self._albums_selected = [
            self.model[child_path][5]
            for child_path in paths
            if self.model[child_path][11] == 'album']

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
        artists_selected = [
            self._artists[self.model[child_path][2].casefold()]
            for child_path in [
                self._filter_model.convert_path_to_child_path(path)
                for path in self._view.get_selection()]
            if self.model[child_path][11] == 'artist']

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
        self._items_selected.extend([
            self.model[child_path][5]
            for child_path in [
                self._filter_model.convert_path_to_child_path(path)
                for path in self._view.get_selection()]
            if self.model[child_path][11] == 'song'])
        self._items_selected_callback(self._items_selected)

    @log
    def _filter_visible_func(self, model, _iter, data=None):
        visible = (model.iter_parent(_iter) is not None
                        or model.iter_has_child(_iter))
        return visible

    @log
    def set_search_text(self, search_term, fields_filter):
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
            GdkPixbuf.Pixbuf,       # album art
            GObject.TYPE_OBJECT,    # item
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT,
            GObject.TYPE_STRING,
            GObject.TYPE_INT,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_STRING,    # type
            GObject.TYPE_INT,
            GObject.TYPE_STRING,    # composer
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
                grilo.populate_custom_query(
                    query, self._add_item, -1, [self.model, category])
        if (not grilo.search_source
                or grilo.search_source.get_id() != 'grl-tracker-source'):
            # nope, can't do - reverting to Search
            grilo.search(search_term, self._add_search_item, self.model)
