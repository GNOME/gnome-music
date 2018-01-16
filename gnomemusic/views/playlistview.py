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
from gi.repository import Gio, GLib, GObject, Gtk, Pango

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.player import DiscoveryStatus
from gnomemusic.playlists import Playlists, StaticPlaylists
from gnomemusic.views.baseview import BaseView
from gnomemusic.widgets.playlistdialog import PlaylistDialog
import gnomemusic.utils as utils

playlists = Playlists.get_default()


class PlaylistView(BaseView):
    """Main view for playlists"""

    __gsignals__ = {
        'playlists-loaded': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'playlist-songs-loaded': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __repr__(self):
        return '<PlaylistView>'

    @log
    def __init__(self, window, player):
        """Initialize

        :param GtkWidget window: The main window
        :param player: The main player object
        """
        self._sidebar = Gtk.ListBox()
        sidebar_container = Gtk.ScrolledWindow()
        sidebar_container.add(self._sidebar)

        super().__init__(
            'playlists', _("Playlists"), window, None, True, sidebar_container)

        self._window = window
        self.player = player

        self._view.get_style_context().add_class('songs-list')

        self._add_list_renderers()

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Music/PlaylistControls.ui')
        headerbar = builder.get_object('grid')
        self._name_stack = builder.get_object('stack')
        self._name_label = builder.get_object('playlist_name')
        self._rename_entry = builder.get_object('playlist_rename_entry')
        self._rename_entry.connect('changed', self._on_rename_entry_changed)
        self._rename_done_button = builder.get_object(
            'playlist_rename_done_button')
        self._songs_count_label = builder.get_object('songs_count')
        self._menubutton = builder.get_object('playlist_menubutton')

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Music/PlaylistContextMenu.ui')
        self._popover_menu = builder.get_object('song_menu')
        self._song_popover = Gtk.Popover.new_from_model(
            self._view, self._popover_menu)
        self._song_popover.set_position(Gtk.PositionType.BOTTOM)

        play_song = Gio.SimpleAction.new('play_song', None)
        play_song.connect('activate', self._play_song)
        self._window.add_action(play_song)

        add_song_to_playlist = Gio.SimpleAction.new(
            'add_song_to_playlist', None)
        add_song_to_playlist.connect('activate', self._add_song_to_playlist)
        self._window.add_action(add_song_to_playlist)

        self._remove_song_action = Gio.SimpleAction.new('remove_song', None)
        self._remove_song_action.connect('activate', self._remove_song)
        self._window.add_action(self._remove_song_action)

        playlist_play_action = Gio.SimpleAction.new('playlist_play', None)
        playlist_play_action.connect('activate', self._on_play_activate)
        self._window.add_action(playlist_play_action)

        self._playlist_delete_action = Gio.SimpleAction.new('playlist_delete',
                                                            None)
        self._playlist_delete_action.connect('activate',
                                             self._on_delete_activate)
        self._window.add_action(self._playlist_delete_action)
        self._playlist_rename_action = Gio.SimpleAction.new(
            'playlist_rename', None)
        self._playlist_rename_action.connect(
            'activate', self._on_rename_activate)
        self._window.add_action(self._playlist_rename_action)

        self._grid.insert_row(0)
        self._grid.attach(headerbar, 1, 0, 1, 1)

        sidebar_container.set_size_request(220, -1)
        sidebar_container.get_style_context().add_class('side-panel')
        self._sidebar.get_style_context().add_class('view')
        self._sidebar.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._sidebar.connect('row-activated', self._on_playlist_activated)

        self._grid.insert_column(0)
        self._grid.child_set_property(self.stack, 'top-attach', 0)
        self._grid.child_set_property(self.stack, 'height', 2)

        self._iter_to_clean = None
        self._iter_to_clean_model = None
        self.current_playlist = None
        self._current_playlist_index = None
        self.pl_todelete = None
        self._pl_todelete_index = None
        self._songs_count = 0
        self._handler_rename_done_button = 0
        self._handler_rename_entry = 0

        self._update_songs_count()

        self.player.connect('playlist-item-changed', self._update_model)
        playlists.connect('playlist-created', self._on_playlist_created)
        playlists.connect('playlist-updated', self._on_playlist_update)
        playlists.connect('song-added-to-playlist',
                          self._on_song_added_to_playlist)
        playlists.connect('song-removed-from-playlist',
                          self._on_song_removed_from_playlist)

        self.show_all()

    @log
    def _on_changes_pending(self, data=None):
        pass

    @log
    def _setup_view(self, view_type):
        view_container = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self._box.pack_start(view_container, True, True, 0)

        self._view = Gtk.TreeView()
        self._view.set_headers_visible(False)
        self._view.set_valign(Gtk.Align.START)
        self._view.set_model(self.model)
        self._view.set_activate_on_single_click(True)
        self._view.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
        self._view.connect('row-activated', self._on_song_activated)
        self._view.connect('button-press-event', self._on_view_clicked)

        view_container.add(self._view)

    @log
    def _add_list_renderers(self):
        now_playing_symbol_renderer = Gtk.CellRendererPixbuf(xpad=0,
                                                             xalign=0.5,
                                                             yalign=0.5)
        column_now_playing = Gtk.TreeViewColumn()
        column_now_playing.set_fixed_width(48)
        column_now_playing.pack_start(now_playing_symbol_renderer, False)
        column_now_playing.set_cell_data_func(now_playing_symbol_renderer,
                                              self._on_list_widget_icon_render,
                                              None)
        self._view.append_column(column_now_playing)

        title_renderer = Gtk.CellRendererText(
            xpad=0, xalign=0.0, yalign=0.5, height=48,
            ellipsize=Pango.EllipsizeMode.END)
        column_title = Gtk.TreeViewColumn("Title", title_renderer, text=2)
        column_title.set_expand(True)
        self._view.append_column(column_title)

        column_star = Gtk.TreeViewColumn()
        self._view.append_column(column_star)
        self._star_handler.add_star_renderers(self._view, column_star)

        duration_renderer = Gtk.CellRendererText(xpad=32, xalign=1.0)
        column_duration = Gtk.TreeViewColumn()
        column_duration.pack_start(duration_renderer, False)
        column_duration.set_cell_data_func(
            duration_renderer, self._on_list_widget_duration_render, None)
        self._view.append_column(column_duration)

        artist_renderer = Gtk.CellRendererText(
            xpad=32, ellipsize=Pango.EllipsizeMode.END)
        column_artist = Gtk.TreeViewColumn("Artist", artist_renderer, text=3)
        column_artist.set_expand(True)
        self._view.append_column(column_artist)

        album_renderer = Gtk.CellRendererText(
            xpad=32, ellipsize=Pango.EllipsizeMode.END)
        column_album = Gtk.TreeViewColumn()
        column_album.set_expand(True)
        column_album.pack_start(album_renderer, True)
        column_album.set_cell_data_func(
            album_renderer, self._on_list_widget_album_render, None)
        self._view.append_column(column_album)

    def _on_list_widget_duration_render(self, col, cell, model, _iter, data):
        if not model.iter_is_valid(_iter):
            return

        item = model[_iter][5]
        if item:
            duration = item.get_duration()
            cell.set_property('text', utils.seconds_to_string(duration))

    def _on_list_widget_album_render(self, coll, cell, model, _iter, data):
        if not model.iter_is_valid(_iter):
            return

        item = model[_iter][5]
        if item:
            cell.set_property('text', utils.get_album_title(item))

    def _on_list_widget_type_render(self, coll, cell, model, _iter, data):
        if not model.iter_is_valid(_iter):
            return

        item = model[_iter][5]
        if item:
            cell.set_property('text', utils.get_album_title(item))

    def _on_list_widget_icon_render(self, col, cell, model, _iter, data):
        if not self.player.currentTrackUri:
            cell.set_visible(False)
            return

        if not model.iter_is_valid(_iter):
            return

        if model[_iter][11] == DiscoveryStatus.FAILED:
            cell.set_property('icon-name', self._error_icon_name)
            cell.set_visible(True)
        elif model[_iter][5].get_url() == self.player.currentTrackUri:
            cell.set_property('icon-name', self._now_playing_icon_name)
            cell.set_visible(True)
        else:
            cell.set_visible(False)

    @log
    def _populate(self):
        self._init = True
        self._window.push_loading_notification()
        self.populate()

    @log
    def _update_model(self, player, playlist, current_iter):
        if self._iter_to_clean:
            self._iter_to_clean_model[self._iter_to_clean][10] = False
        if playlist != self.model:
            return False

        self.model[current_iter][10] = True
        if self.model[current_iter][8] != self._error_icon_name:
            self._iter_to_clean = current_iter.copy()
            self._iter_to_clean_model = self.model

        return False

    @log
    def _add_playlist_item(self, source, param, playlist, remaining=0,
                           data=None):
        """Grilo.populate_playlists callback.

        Add all playlists found by Grilo to sidebar

        :param GrlTrackerSource source: tracker source
        :param int param: param
        :param GrlMedia playlist: playlist to add
        :param int remaining: next playlist_id or zero if None
        :param data: associated data
        """
        if not playlist:
            self._window.pop_loading_notification()
            self.emit('playlists-loaded')
            return

        self._add_playlist_to_sidebar(playlist, None)

    @log
    def _add_playlist_to_sidebar(self, playlist, index=None):
        """Add a playlist to sidebar

        :param GrlMedia playlist: playlist to add
        :param int index: position
        """
        if index is None:
            index = -1
        if playlists.is_static_playlist(playlist):
            index = 0

        title = utils.get_media_title(playlist)
        row = Gtk.ListBoxRow()
        row.playlist = playlist
        label = Gtk.Label(
            label=title, xalign=0, xpad=16, ypad=16,
            ellipsize=Pango.EllipsizeMode.END)
        row.add(label)
        row.show_all()
        self._sidebar.insert(row, index)

        if len(self._sidebar) == 1:
            self._sidebar.select_row(row)
            self._sidebar.emit('row-activated', row)

    @log
    def _on_song_activated(self, widget, path, column):
        """Action performed when clicking on a song

        clicking on star column toggles favorite
        clicking on an other columns launches player

        :param Gtk.Tree treeview: self._view
        :param Gtk.TreePath path: activated row index
        :param Gtk.TreeViewColumn column: activated column
        """
        if self._star_handler.star_renderer_click:
            self._star_handler.star_renderer_click = False
            return

        try:
            _iter = self.model.get_iter(path)
        except TypeError:
            return

        if self.model[_iter][8] != self._error_icon_name:
            self.player.set_playlist(
                'Playlist', self.current_playlist.get_id(), self.model, _iter,
                5, 11)
            self.player.set_playing(True)

    @log
    def _on_view_clicked(self, treeview, event):
        """Right click on self._view displays a context menu

        :param Gtk.TreeView treeview: self._view
        :param Gdk.EventButton event: clicked event
        """
        if event.button != 3:
            return

        path, col, cell_x, cell_y = treeview.get_path_at_pos(event.x, event.y)
        self._view.get_selection().select_path(path)

        rect = self._view.get_visible_rect()
        rect.x = event.x - rect.width / 2.0
        rect.y = event.y - rect.height + 5

        self._song_popover.set_relative_to(self._view)
        self._song_popover.set_pointing_to(rect)
        self._song_popover.popup()
        return

    @log
    def _play_song(self, menuitem, data=None):
        model, _iter = self._view.get_selection().get_selected()
        path = model.get_path(_iter)
        cols = self._view.get_columns()
        self._view.emit('row-activated', path, cols[0])

    @log
    def _add_song_to_playlist(self, menuitem, data=None):
        model, _iter = self._view.get_selection().get_selected()
        song = model[_iter][5]

        playlist_dialog = PlaylistDialog(self._window, self.pl_todelete)
        if playlist_dialog.run() == Gtk.ResponseType.ACCEPT:
            playlists.add_to_playlist(playlist_dialog.get_selected(), [song])
        playlist_dialog.destroy()

    @log
    def _remove_song(self, menuitem, data=None):
        model, _iter = self._view.get_selection().get_selected()
        song = model[_iter][5]
        playlists.remove_from_playlist(self.current_playlist, [song])

    @log
    def _on_playlist_update(self, playlists, playlist_id):
        """If the updated playlist is displayed, we need to update it

        :param playlists: playlists
        :param playlist_id: updated playlist's id
        """
        for row in self._sidebar:
            playlist = row.playlist
            if (str(playlist_id) == playlist.get_id()
                    and self.current_playlist == playlist):
                GLib.idle_add(self._on_playlist_activated, self._sidebar, row)
                break

    @log
    def activate_playlist(self, playlist_id):

        def find_and_activate_playlist():
            for row in self._sidebar:
                if row.playlist.get_id() == playlist_id:
                    selection = self._sidebar.get_selected_row()
                    if selection.get_index() == row.get_index():
                        self._on_play_activate(None)
                    else:
                        self._sidebar.select_row(row)
                        handler = 0

                        def songs_loaded_callback(view):
                            self.disconnect(handler)
                            self._on_play_activate(None)

                        handler = self.connect('playlist-songs-loaded',
                                               songs_loaded_callback)
                        self._sidebar.emit('row-activated', row)

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
                def_handler = self.connect('playlist-songs-loaded',
                                           songs_loaded_callback)

            handler = self.connect('playlists-loaded',
                                   playlists_loaded_callback)

            self._populate()

    @log
    def remove_playlist(self):
        """Removes the current selected playlist"""
        if not self._current_playlist_is_protected():
            self._on_delete_activate(None)

    @log
    def _on_playlist_activated(self, sidebar, row, data=None):
        """Update view with content from selected playlist"""
        playlist = row.playlist
        playlist_name = utils.get_media_title(playlist)

        if self.rename_active:
            self.disable_rename_playlist()

        self.current_playlist = playlist
        self._name_label.set_text(playlist_name)
        self._current_playlist_index = row.get_index()

        # if the active queue has been set by this playlist,
        # use it as model, otherwise build the liststore
        self._view.set_model(None)
        self.model.clear()
        self._songs_count = 0
        grilo.populate_playlist_songs(playlist, self._add_song)

        if self._current_playlist_is_protected():
            self._playlist_delete_action.set_enabled(False)
            self._playlist_rename_action.set_enabled(False)
            self._remove_song_action.set_enabled(False)
        else:
            self._playlist_delete_action.set_enabled(True)
            self._playlist_rename_action.set_enabled(True)
            self._remove_song_action.set_enabled(True)

    @log
    def _add_song(self, source, param, song, remaining=0, data=None):
        """Grilo.populate_playlist_songs callback.

        Add all playlists found by Grilo to self._model

        :param GrlTrackerSource source: tracker source
        :param int param: param
        :param GrlMedia song: song to add
        :param int remaining: next playlist_id or zero if None
        :param data: associated data
        """
        self._add_song_to_model(song, self.model)
        if remaining == 0:
            self._view.set_model(self.model)

    @log
    def _add_song_to_model(self, song, model):
        """Add song to a playlist
        :param Grl.Media song: song to add
        :param Gtk.ListStore model: model
        """
        if not song:
            self._update_songs_count()
            if self.player.playlist:
                self.player._validate_next_track()
            self.emit('playlist-songs-loaded')
            return

        self._offset += 1
        title = utils.get_media_title(song)
        song.set_title(title)
        artist = utils.get_artist_name(song)
        model.insert_with_valuesv(-1, [2, 3, 5, 9],
                                  [title, artist, song, song.get_favourite()])

        self._songs_count += 1

    @log
    def _update_songs_count(self):
        self._songs_count_label.set_text(
            ngettext("%d Song", "%d Songs", self._songs_count)
            % self._songs_count)

    @log
    def _on_play_activate(self, menuitem, data=None):
        _iter = self.model.get_iter_first()
        if not _iter:
            return

        selection = self._view.get_selection()
        selection.select_path(self.model.get_path(_iter))
        cols = self._view.get_columns()
        self._view.emit('row-activated', self.model.get_path(_iter), cols[0])

    @log
    def _current_playlist_is_protected(self):
        current_playlist_id = self.current_playlist.get_id()
        if current_playlist_id in StaticPlaylists().get_ids():
            return True
        else:
            return False

    @log
    def _stage_playlist_for_deletion(self):
        self.model.clear()
        selection = self._sidebar.get_selected_row()
        index = selection.get_index()
        self._pl_todelete_index = index
        self.pl_todelete = selection.playlist

        row_next = (self._sidebar.get_row_at_index(index + 1)
                    or self._sidebar.get_row_at_index(index - 1))
        self._sidebar.remove(selection)

        if row_next:
            self._sidebar.select_row(row_next)
            self._sidebar.emit('row-activated', row_next)

    @log
    def undo_playlist_deletion(self):
        """Revert the last playlist removal"""
        self._add_playlist_to_sidebar(
            self.pl_todelete, self._pl_todelete_index)

    @log
    def _on_delete_activate(self, menuitem, data=None):
        """Delete current playlist after 5 seconds via notifier"""
        self._window.show_playlist_notification()
        self._stage_playlist_for_deletion()

    @log
    @property
    def rename_active(self):
        """Indicate if renaming dialog is active"""
        return self._name_stack.get_visible_child_name() == 'renaming_dialog'

    @log
    def _on_rename_entry_changed(self, selection):
        if selection.get_text_length() > 0:
            self._rename_done_button.set_sensitive(True)
        else:
            self._rename_done_button.set_sensitive(False)

    @log
    def disable_rename_playlist(self):
        """disables rename button and entry"""
        self._name_stack.set_visible_child(self._name_label)
        self._rename_done_button.disconnect(self._handler_rename_done_button)
        self._rename_entry.disconnect(self._handler_rename_entry)

    @log
    def _stage_playlist_for_renaming(self):
        selection = self._sidebar.get_selected_row()
        pl_torename = selection.playlist

        def playlist_renamed_callback(widget):
            new_name = self._rename_entry.get_text()
            if not new_name:
                return

            selection.get_child().set_text(new_name)
            pl_torename.set_title(new_name)
            playlists.rename(pl_torename, new_name)
            self._name_label.set_text(new_name)
            self.disable_rename_playlist()

        self._name_stack.set_visible_child_name('renaming_dialog')
        self._rename_entry.set_text(utils.get_media_title(pl_torename))
        self._rename_entry.grab_focus()
        self._handler_rename_entry = self._rename_entry.connect(
            'activate', playlist_renamed_callback)
        self._handler_rename_done_button = self._rename_done_button.connect(
            'clicked', playlist_renamed_callback)

    @log
    def _on_rename_activate(self, menuitem, data=None):
        self._stage_playlist_for_renaming()

    @log
    def _on_playlist_created(self, playlists, playlist):
        """Add new playlist to sidebar"""
        self._add_playlist_to_sidebar(playlist)

    @log
    def _on_song_added_to_playlist(self, playlists, playlist, item):
        if (self.current_playlist
                and playlist.get_id() == self.current_playlist.get_id()):
            self._add_song_to_model(item, self.model)

    @log
    def _on_song_removed_from_playlist(self, playlists, playlist, item):
        if (self.current_playlist
                and playlist.get_id() == self.current_playlist.get_id()):
            model = self.model
        else:
            return

        # checks if the to be removed track is now being played
        def is_playing(row):
            if (self.current_playlist
                    and playlist.get_id() == self.current_playlist.get_id()):
                if (self.player.currentTrack is not None
                        and self.player.currentTrack.valid()):
                    track_path = self.player.currentTrack.get_path()
                    track_path_str = track_path.to_string()
                    if (row.path is not None
                            and row.path.to_string() == track_path_str):
                        return True
            return False

        for row in model:
            if row[5].get_id() == item.get_id():

                is_being_played = is_playing(row)

                next_iter = model.iter_next(row.iter)
                model.remove(row.iter)

                # Reload the model and switch to next song
                if is_being_played:
                    if next_iter is None:
                        # Get first track if next track is not valid
                        next_iter = model.get_iter_first()
                        if next_iter is None:
                            # Last track was removed
                            return

                    self._iter_to_clean = None
                    self._update_model(self.player, model, next_iter)
                    self.player.set_playlist('Playlist', playlist.get_id(),
                                             model, next_iter, 5, 11)
                    self.player.set_playing(True)

                # Update songs count
                self._songs_count -= 1
                self._update_songs_count()
                return

    @log
    def populate(self):
        """Clear sidebar, then populate it"""
        for row in self._sidebar:
            self._sidebar.remove(row)
        grilo.populate_playlists(self._offset, self._add_playlist_item)
