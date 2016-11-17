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

from gettext import gettext as _, ngettext
from gi.repository import Gd, GdkPixbuf, Gio, GLib, GObject, Gtk, Pango

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.player import DiscoveryStatus
from gnomemusic.playlists import Playlists, StaticPlaylists
from gnomemusic.views.baseview import BaseView
import gnomemusic.utils as utils

playlists = Playlists.get_default()


class PlaylistView(BaseView):
    __gsignals__ = {
        'playlists-loaded': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'playlist-songs-loaded': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __repr__(self):
        return '<PlaylistView>'

    @log
    def __init__(self, window, player):
        self.playlists_sidebar = Gd.MainView()

        BaseView.__init__(self, 'playlists', _("Playlists"), window,
                               Gd.MainViewType.LIST, True, self.playlists_sidebar)

        self.view.get_generic_view().get_style_context()\
            .add_class('songs-list')
        self._add_list_renderers()
        self.view.get_generic_view().get_style_context().remove_class('content-view')

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Music/PlaylistControls.ui')
        self.headerbar = builder.get_object('grid')
        self.name_label = builder.get_object('playlist_name')
        self.songs_count_label = builder.get_object('songs_count')
        self.menubutton = builder.get_object('playlist_menubutton')
        playlistPlayAction = Gio.SimpleAction.new('playlist_play', None)
        playlistPlayAction.connect('activate', self._on_play_activate)
        window.add_action(playlistPlayAction)
        self.playlistDeleteAction = Gio.SimpleAction.new('playlist_delete', None)
        self.playlistDeleteAction.connect('activate', self._on_delete_activate)
        window.add_action(self.playlistDeleteAction)
        self._grid.insert_row(0)
        self._grid.attach(self.headerbar, 1, 0, 1, 1)

        self.playlists_model = Gtk.ListStore(
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GdkPixbuf.Pixbuf,
            GObject.TYPE_OBJECT,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT,
            GObject.TYPE_STRING,
            GObject.TYPE_INT,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT
        )

        self.playlists_sidebar.set_view_type(Gd.MainViewType.LIST)
        self.playlists_sidebar.set_model(self.playlists_model)
        self.playlists_sidebar.set_hexpand(False)
        self.playlists_sidebar.get_style_context().add_class('side-panel')
        self.playlists_sidebar.get_generic_view().get_selection().set_mode(
            Gtk.SelectionMode.SINGLE)
        self.playlists_sidebar.connect('item-activated', self._on_playlist_activated)
        self._grid.insert_column(0)
        self._grid.child_set_property(self.stack, 'top-attach', 0)
        self._grid.child_set_property(self.stack, 'height', 2)
        self._add_sidebar_renderers()
        self.playlists_sidebar.get_generic_view().get_style_context().remove_class('content-view')

        self.iter_to_clean = None
        self.iter_to_clean_model = None
        self.current_playlist = None
        self.current_playlist_index = None
        self.pl_todelete = None
        self.pl_todelete_index = None
        self.really_delete = True
        self.songs_count = 0
        self.window = window
        self._update_songs_count()
        self.player = player
        self.player.connect('playlist-item-changed', self.update_model)
        playlists.connect('playlist-created', self._on_playlist_created)
        playlists.connect('playlist-updated', self.on_playlist_update)
        playlists.connect('song-added-to-playlist', self._on_song_added_to_playlist)
        playlists.connect('song-removed-from-playlist', self._on_song_removed_from_playlist)
        self.show_all()

    @log
    def _on_changes_pending(self, data=None):
        pass

    @log
    def _add_list_renderers(self):
        list_widget = self.view.get_generic_view()
        cols = list_widget.get_columns()
        cells = cols[0].get_cells()
        cells[2].set_visible(False)
        now_playing_symbol_renderer = Gtk.CellRendererPixbuf(xpad=0,
                                                             xalign=0.5,
                                                             yalign=0.5)

        column_now_playing = Gtk.TreeViewColumn()
        column_now_playing.set_fixed_width(48)
        column_now_playing.pack_start(now_playing_symbol_renderer, False)
        column_now_playing.set_cell_data_func(now_playing_symbol_renderer,
                                              self._on_list_widget_icon_render, None)
        list_widget.insert_column(column_now_playing, 0)

        title_renderer = Gtk.CellRendererText(
            xpad=0,
            xalign=0.0,
            yalign=0.5,
            height=48,
            ellipsize=Pango.EllipsizeMode.END
        )
        list_widget.add_renderer(title_renderer,
                                 self._on_list_widget_title_render, None)
        cols[0].add_attribute(title_renderer, 'text', 2)

        self.star_handler.add_star_renderers(list_widget, cols)

        duration_renderer = Gd.StyledTextRenderer(
            xpad=32,
            xalign=1.0
        )
        duration_renderer.add_class('dim-label')
        list_widget.add_renderer(duration_renderer,
                                 self._on_list_widget_duration_render, None)

        artist_renderer = Gd.StyledTextRenderer(
            xpad=32,
            ellipsize=Pango.EllipsizeMode.END
        )
        artist_renderer.add_class('dim-label')
        list_widget.add_renderer(artist_renderer,
                                 self._on_list_widget_artist_render, None)
        cols[0].add_attribute(artist_renderer, 'text', 3)

        type_renderer = Gd.StyledTextRenderer(
            xpad=32,
            ellipsize=Pango.EllipsizeMode.END
        )
        type_renderer.add_class('dim-label')
        list_widget.add_renderer(type_renderer,
                                 self._on_list_widget_type_render, None)

    @log
    def _add_sidebar_renderers(self):
        list_widget = self.playlists_sidebar.get_generic_view()

        cols = list_widget.get_columns()
        cells = cols[0].get_cells()
        cells[1].set_visible(False)
        cells[2].set_visible(False)
        type_renderer = Gd.StyledTextRenderer(
            xpad=16,
            ypad=16,
            ellipsize=Pango.EllipsizeMode.END,
            xalign=0.0,
            width=220
        )
        list_widget.add_renderer(type_renderer, lambda *args: None, None)
        cols[0].clear_attributes(type_renderer)
        cols[0].add_attribute(type_renderer, "text", 2)

    def _on_list_widget_title_render(self, col, cell, model, _iter, data):
        pass

    def _on_list_widget_duration_render(self, col, cell, model, _iter, data):
        if not model.iter_is_valid(_iter):
            return

        item = model.get_value(_iter, 5)
        if item:
            seconds = item.get_duration()
            minutes = seconds // 60
            seconds %= 60
            cell.set_property('text', '%i:%02i' % (minutes, seconds))

    def _on_list_widget_artist_render(self, col, cell, model, _iter, data):
        pass

    def _on_list_widget_type_render(self, coll, cell, model, _iter, data):
        if not model.iter_is_valid(_iter):
            return

        item = model.get_value(_iter, 5)
        if item:
            cell.set_property('text', utils.get_album_title(item))

    def _on_list_widget_icon_render(self, col, cell, model, _iter, data):
        if not self.player.currentTrackUri:
            cell.set_visible(False)
            return

        if not model.iter_is_valid(_iter):
            return

        if model.get_value(_iter, 11) == DiscoveryStatus.FAILED:
            cell.set_property('icon-name', self.errorIconName)
            cell.set_visible(True)
        elif model.get_value(_iter, 5).get_url() == self.player.currentTrackUri:
            cell.set_property('icon-name', self.nowPlayingIconName)
            cell.set_visible(True)
        else:
            cell.set_visible(False)

    @log
    def _populate(self):
        self._init = True
        self.window._init_loading_notification()
        self.populate()

    @log
    def update_model(self, player, playlist, currentIter):
        if self.iter_to_clean:
            self.iter_to_clean_model.set_value(self.iter_to_clean, 10, False)
        if playlist != self.model:
            return False

        self.model.set_value(currentIter, 10, True)
        if self.model.get_value(currentIter, 8) != self.errorIconName:
            self.iter_to_clean = currentIter.copy()
            self.iter_to_clean_model = self.model

        return False

    @log
    def _add_playlist_item(self, source, param, item, remaining=0, data=None):
        self._add_playlist_item_to_model(item)

    @log
    def _add_playlist_item_to_model(self, item, index=None):
        self.window.notification.set_timeout(0)
        if index is None:
            index = -1
        if not item:
            self.window.notification.dismiss()
            self.emit('playlists-loaded')
            return
        _iter = self.playlists_model.insert_with_valuesv(
            index,
            [2, 5],
            [utils.get_media_title(item), item])
        if self.playlists_model.iter_n_children(None) == 1:
            _iter = self.playlists_model.get_iter_first()
            selection = self.playlists_sidebar.get_generic_view().get_selection()
            selection.select_iter(_iter)
            self.playlists_sidebar.emit('item-activated', '0',
                                        self.playlists_model.get_path(_iter))

    @log
    def _on_item_activated(self, widget, id, path):
        if self.star_handler.star_renderer_click:
            self.star_handler.star_renderer_click = False
            return

        try:
            _iter = self.model.get_iter(path)
        except TypeError:
            return
        if self.model.get_value(_iter, 8) != self.errorIconName:
            self.player.set_playlist(
                'Playlist', self.current_playlist.get_id(),
                self.model, _iter, 5, 11
            )
            self.player.set_playing(True)

    @log
    def on_playlist_update(self, widget, playlist_id):
        _iter = self.playlists_model.get_iter_first()
        while _iter:
            playlist = self.playlists_model.get_value(_iter, 5)
            if str(playlist_id) == playlist.get_id() and self.current_playlist == playlist:
                path = self.playlists_model.get_path(_iter)
                GLib.idle_add(self._on_playlist_activated, None, None, path)
                break
            _iter = self.playlists_model.iter_next(_iter)

    @log
    def activate_playlist(self, playlist_id):

        def find_and_activate_playlist():
            for playlist in self.playlists_model:
                if playlist[5].get_id() == playlist_id:
                    selection = self.playlists_sidebar.get_generic_view().get_selection()
                    if selection.iter_is_selected(playlist.iter):
                        self._on_play_activate(None)
                    else:
                        selection.select_iter(playlist.iter)
                        handler = 0

                        def songs_loaded_callback(view):
                            self.disconnect(handler)
                            self._on_play_activate(None)

                        handler = self.connect('playlist-songs-loaded', songs_loaded_callback)
                        self.playlists_sidebar.emit('item-activated', '0', playlist.path)

                    return

        if self._init:
            find_and_activate_playlist()
        else:
            handler = 0

            def playlists_loaded_callback(view):
                self.disconnect(handler)
                def_handler = 0

                def songs_loaded_callback(view):
                    self.disconnect(def_handler)
                    find_and_activate_playlist()

                # Skip load of default playlist
                def_handler = self.connect('playlist-songs-loaded', songs_loaded_callback)

            handler = self.connect('playlists-loaded', playlists_loaded_callback)

            self._populate()

    @log
    def remove_playlist(self):
        if not self.current_playlist_is_protected():
            self._on_delete_activate(None)

    @log
    def _on_playlist_activated(self, widget, item_id, path):
        _iter = self.playlists_model.get_iter(path)
        playlist_name = self.playlists_model.get_value(_iter, 2)
        playlist = self.playlists_model.get_value(_iter, 5)

        self.current_playlist = playlist
        self.name_label.set_text(playlist_name)
        self.current_playlist_index = int(path.to_string())

        # if the active queue has been set by this playlist,
        # use it as model, otherwise build the liststore
        self.view.set_model(None)
        self.model.clear()
        self.songs_count = 0
        grilo.populate_playlist_songs(playlist, self._add_item)

        # disable delete button if current playlist is a smart playlist
        if self.current_playlist_is_protected():
            self.playlistDeleteAction.set_enabled(False)
        else:
            self.playlistDeleteAction.set_enabled(True)

    @log
    def _add_item(self, source, param, item, remaining=0, data=None):
        self._add_item_to_model(item, self.model)
        if remaining == 0:
            self.view.set_model(self.model)

    @log
    def _add_item_to_model(self, item, model):
        if not item:
            self._update_songs_count()
            if self.player.playlist:
                self.player._validate_next_track()
            self.emit('playlist-songs-loaded')
            return
        self._offset += 1
        title = utils.get_media_title(item)
        item.set_title(title)
        artist = utils.get_album_title(item)
        model.insert_with_valuesv(
            -1,
            [2, 3, 5, 9],
            [title, artist, item, item.get_favourite()])
        self.songs_count += 1

    @log
    def _update_songs_count(self):
        self.songs_count_label.set_text(
            ngettext("%d Song", "%d Songs", self.songs_count)
            % self.songs_count)

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        self.playlists_sidebar.set_sensitive(not self.header_bar._selectionMode)
        self.menubutton.set_sensitive(not self.header_bar._selectionMode)

    @log
    def _on_play_activate(self, menuitem, data=None):
        _iter = self.model.get_iter_first()
        if not _iter:
            return

        self.view.get_generic_view().get_selection().\
            select_path(self.model.get_path(_iter))
        self.view.emit('item-activated', '0',
                       self.model.get_path(_iter))

    @log
    def current_playlist_is_protected(self):
        current_playlist_id = self.current_playlist.get_id()
        if current_playlist_id in StaticPlaylists().get_ids():
            return True
        else:
            return False

    @log
    def stage_playlist_for_deletion(self):
        self.model.clear()
        self.pl_todelete_index = self.current_playlist_index
        _iter = self.playlists_sidebar.get_generic_view().get_selection().get_selected()[1]
        self.pl_todelete = self.playlists_model.get_value(_iter, 5)

        if not _iter:
            return

        iter_next = self.playlists_model.iter_next(_iter)\
            or self.playlists_model.iter_previous(_iter)
        self.playlists_model.remove(_iter)

        if iter_next:
            selection = self.playlists_sidebar.get_generic_view().get_selection()
            selection.select_iter(iter_next)
            self.playlists_sidebar.emit('item-activated', '0',
                                        self.playlists_model.get_path(iter_next))

    @log
    def undo_playlist_deletion(self):
        self._add_playlist_item_to_model(self.pl_todelete, self.pl_todelete_index)

    @log
    def _on_delete_activate(self, menuitem, data=None):
        self.window._init_playlist_removal_notification()
        self.stage_playlist_for_deletion()

    @log
    def _on_playlist_created(self, playlists, item):
        self._add_playlist_item_to_model(item)
        if self.playlists_model.iter_n_children(None) == 1:
            _iter = self.playlists_model.get_iter_first()
            selection = self.playlists_sidebar.get_generic_view().get_selection()
            selection.select_iter(_iter)
            self.playlists_sidebar.emit('item-activated', '0',
                                        self.playlists_model.get_path(_iter))

    @log
    def _on_song_added_to_playlist(self, playlists, playlist, item):
        if self.current_playlist and \
           playlist.get_id() == self.current_playlist.get_id():
            self._add_item_to_model(item, self.model)

    @log
    def _on_song_removed_from_playlist(self, playlists, playlist, item):
        if self.current_playlist and \
           playlist.get_id() == self.current_playlist.get_id():
            model = self.model
        else:
            return

        update_playing_track = False
        for row in model:
            if row[5].get_id() == item.get_id():
                # Is the removed track now being played?
                if self.current_playlist and \
                   playlist.get_id() == self.current_playlist.get_id():
                    if self.player.currentTrack is not None and self.player.currentTrack.valid():
                        currentTrackpath = self.player.currentTrack.get_path().to_string()
                        if row.path is not None and row.path.to_string() == currentTrackpath:
                            update_playing_track = True

                nextIter = model.iter_next(row.iter)
                model.remove(row.iter)

                # Reload the model and switch to next song
                if update_playing_track:
                    if nextIter is None:
                        # Get first track if next track is not valid
                        nextIter = model.get_iter_first()
                        if nextIter is None:
                            # Last track was removed
                            return

                    self.iter_to_clean = None
                    self.update_model(self.player, model, nextIter)
                    self.player.set_playlist('Playlist', playlist.get_id(), model, nextIter, 5, 11)
                    self.player.set_playing(True)

                # Update songs count
                self.songs_count -= 1
                self._update_songs_count()
                return

    @log
    def populate(self):
        self.playlists_model.clear()
        grilo.populate_playlists(self._offset, self._add_playlist_item)

    @log
    def get_selected_tracks(self, callback):
        callback([self.model.get_value(self.model.get_iter(path), 5)
                  for path in self.view.get_selection()])
