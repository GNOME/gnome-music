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
from gi.repository import Gio, GLib, GObject, Gtk, Pango

import logging

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.player import DiscoveryStatus
from gnomemusic.playlists import Playlists, StaticPlaylists
from gnomemusic.views.baseview import BaseView
from gnomemusic.widgets.notificationspopup import PlaylistNotification
from gnomemusic.widgets.playlistcontextmenu import PlaylistContextMenu
from gnomemusic.widgets.playlistcontrols import PlaylistControls
from gnomemusic.widgets.playlistdialog import PlaylistDialog
import gnomemusic.utils as utils

logger = logging.getLogger(__name__)

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

        self._pl_ctrls = PlaylistControls()

        self._song_popover = PlaylistContextMenu(self._view)

        play_song = Gio.SimpleAction.new('play_song', None)
        play_song.connect('activate', self._play_song)
        self._window.add_action(play_song)

        add_song_to_playlist = Gio.SimpleAction.new(
            'add_song_to_playlist', None)
        add_song_to_playlist.connect('activate', self._add_song_to_playlist)
        self._window.add_action(add_song_to_playlist)

        self._remove_song_action = Gio.SimpleAction.new('remove_song', None)
        self._remove_song_action.connect(
            'activate', self._stage_song_for_deletion)
        self._window.add_action(self._remove_song_action)

        playlist_play_action = Gio.SimpleAction.new('playlist_play', None)
        playlist_play_action.connect('activate', self._on_play_activate)
        self._window.add_action(playlist_play_action)

        self._playlist_delete_action = Gio.SimpleAction.new(
            'playlist_delete', None)
        self._playlist_delete_action.connect(
            'activate', self._stage_playlist_for_deletion)
        self._window.add_action(self._playlist_delete_action)
        self._playlist_rename_action = Gio.SimpleAction.new(
            'playlist_rename', None)
        self._playlist_rename_action.connect(
            'activate', self._stage_playlist_for_renaming)
        self._window.add_action(self._playlist_rename_action)

        self._grid.insert_row(0)
        self._grid.attach(self._pl_ctrls, 1, 0, 1, 1)

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
        self._current_playlist = None
        self._current_playlist_index = None
        self.pls_todelete = {}
        self._songs_todelete = {}
        self._songs_count = 0

        self._pl_ctrls.update_songs_count(self._songs_count)

        self.model.connect('row-inserted', self._on_song_inserted)
        self.model.connect('row-deleted', self._on_song_deleted)

        self.player.connect('song-changed', self._update_model)
        playlists.connect('playlist-created', self._on_playlist_created)
        playlists.connect('playlist-updated', self._on_playlist_update)
        playlists.connect(
            'song-added-to-playlist', self._on_song_added_to_playlist)

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
        self._view.connect('drag-begin', self._drag_begin)
        self._view.connect('drag-end', self._drag_end)
        self._song_drag = {'active': False}

        view_container.add(self._view)

    @log
    def _add_list_renderers(self):
        now_playing_symbol_renderer = Gtk.CellRendererPixbuf(
            xpad=0, xalign=0.5, yalign=0.5)
        column_now_playing = Gtk.TreeViewColumn()
        column_now_playing.set_fixed_width(48)
        column_now_playing.pack_start(now_playing_symbol_renderer, False)
        column_now_playing.set_cell_data_func(
            now_playing_symbol_renderer, self._on_list_widget_icon_render,
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
        self._star_handler.add_star_renderers(column_star)

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

    def _on_list_widget_icon_render(self, col, cell, model, _iter, data):
        if not self.player.playing_playlist(
                'Playlist', self._current_playlist.get_id()):
            cell.set_visible(False)
            return

        if not model.iter_is_valid(_iter):
            return

        if model[_iter][11] == DiscoveryStatus.FAILED:
            cell.set_property('icon-name', self._error_icon_name)
            cell.set_visible(True)
        elif model[_iter][5].get_url() == self.player.url:
            cell.set_property('icon-name', self._now_playing_icon_name)
            cell.set_visible(True)
        else:
            cell.set_visible(False)

    @log
    def _update_model(self, player, playlist, current_iter):
        if self._iter_to_clean:
            self._iter_to_clean_model[self._iter_to_clean][10] = False
        if not player.playing_playlist(
                'Playlist', self._current_playlist.get_id()):
            return False

        pos_str = playlist.get_path(current_iter).to_string()
        iter_ = self.model.get_iter_from_string(pos_str)
        self.model[iter_][10] = True
        if self.model[iter_][8] != self._error_icon_name:
            self._iter_to_clean = iter_.copy()
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
            self._window.notifications_popup.pop_loading()
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
        self._offset += 1

        if len(self._sidebar) == 1:
            self._sidebar.select_row(row)
            self._sidebar.emit('row-activated', row)

    @log
    def _on_song_activated(self, widget, path, column):
        """Action performed when clicking on a song

        clicking on star column toggles favorite
        clicking on an other columns launches player
        Action is not performed if drag and drop is active

        :param Gtk.Tree treeview: self._view
        :param Gtk.TreePath path: activated row index
        :param Gtk.TreeViewColumn column: activated column
        """
        def activate_song():
            if self._song_drag['active']:
                return

            if self._star_handler.star_renderer_click:
                self._star_handler.star_renderer_click = False
                return

            _iter = self.model.get_iter(path)
            if self.model[_iter][8] != self._error_icon_name:
                self.player.set_playlist(
                    'Playlist', self._current_playlist.get_id(), self.model,
                    _iter)
                self.player.play()

        # 'row-activated' signal is emitted before 'drag-begin' signal.
        # Need to wait to check if drag and drop operation is active.
        GLib.idle_add(activate_song)

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
    def _drag_begin(self, widget_, drag_context):
        self._song_drag['active'] = True

    @log
    def _drag_end(self, widget_, drag_context):
        self._song_drag['active'] = False

    @log
    def _on_song_inserted(self, model, path, iter_):
        if not self._song_drag['active']:
            return

        self._song_drag['new_pos'] = int(path.to_string())

    @log
    def _on_song_deleted(self, model, path):
        """Save new playlist order after drag and drop operation.

        Update player's playlist if necessary.
        """
        if not self._song_drag['active']:
            return

        new_pos = self._song_drag['new_pos']
        prev_pos = int(path.to_string())

        if abs(new_pos - prev_pos) == 1:
            return

        first_pos = min(new_pos, prev_pos)
        last_pos = max(new_pos, prev_pos)

        # update player's playlist.
        if self.player.playing_playlist(
                'Playlist', self._current_playlist.get_id()):
            playing_old_path = self.player.current_song.get_path().to_string()
            playing_old_pos = int(playing_old_path)
            iter_ = model.get_iter_from_string(playing_old_path)
            # if playing song position has changed
            if playing_old_pos >= first_pos and playing_old_pos < last_pos:
                current_player_song = self.player.get_current_media()
                for row in model:
                    if row[5].get_id() == current_player_song.get_id():
                        iter_ = row.iter
                        self._iter_to_clean = iter_
                        self._iter_to_clean_model = model
                        break
            self.player.set_playlist(
                'Playlist', self._current_playlist.get_id(), model, iter_)

        positions = []
        songs = []
        for pos in range(first_pos, last_pos):
            _iter = model.get_iter_from_string(str(pos))
            songs.append(model[_iter][5])
            positions.append(pos + 1)

        playlists.reorder_playlist(self._current_playlist, songs, positions)

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

        playlist_dialog = PlaylistDialog(
            self._window, self.pls_todelete)
        if playlist_dialog.run() == Gtk.ResponseType.ACCEPT:
            playlists.add_to_playlist(playlist_dialog.get_selected(), [song])
        playlist_dialog.destroy()

    @log
    def _stage_song_for_deletion(self, menuitem, data=None):
        model, _iter = self._view.get_selection().get_selected()
        song = model[_iter][5]
        index = int(model.get_path(_iter).to_string())
        song_id = song.get_id()
        self._songs_todelete[song_id] = {
            'playlist': self._current_playlist,
            'song': song,
            'index': index
        }
        self._remove_song_from_playlist(self._current_playlist, song, index)
        self._create_notification(PlaylistNotification.Type.SONG, song_id)

    @log
    def _on_playlist_update(self, playlists, playlist_id):
        """Refresh the displayed playlist if necessary

        :param playlists: playlists
        :param playlist_id: updated playlist's id
        """
        for row in self._sidebar:
            playlist = row.playlist
            if (str(playlist_id) == playlist.get_id()
                    and self._is_current_playlist(playlist)):
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
            self._stage_playlist_for_deletion(None)

    @log
    def _on_playlist_activated(self, sidebar, row, data=None):
        """Update view with content from selected playlist"""
        playlist = row.playlist
        playlist_name = utils.get_media_title(playlist)

        if self.rename_active:
            self.disable_rename_playlist()

        self._current_playlist = playlist
        self._pl_ctrls.props.playlist_name = playlist_name
        self._current_playlist_index = row.get_index()

        # if the active queue has been set by this playlist,
        # use it as model, otherwise build the liststore
        self._view.set_model(None)
        self.model.clear()
        self._iter_to_clean = None
        self._iter_to_clean_model = None
        self._songs_count = 0
        grilo.populate_playlist_songs(playlist, self._add_song)

        if self._current_playlist_is_protected():
            self._playlist_delete_action.set_enabled(False)
            self._playlist_rename_action.set_enabled(False)
            self._remove_song_action.set_enabled(False)
            self._view.set_reorderable(False)
        else:
            self._playlist_delete_action.set_enabled(True)
            self._playlist_rename_action.set_enabled(True)
            self._remove_song_action.set_enabled(True)
            self._view.set_reorderable(True)

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
    def _add_song_to_model(self, song, model, index=-1):
        """Add song to a playlist
        :param Grl.Media song: song to add
        :param Gtk.ListStore model: model
        """
        if not song:
            self._pl_ctrls.update_songs_count(self._songs_count)
            self.emit('playlist-songs-loaded')
            return None

        title = utils.get_media_title(song)
        song.set_title(title)
        artist = utils.get_artist_name(song)
        iter_ = model.insert_with_valuesv(
            index, [2, 3, 5, 9],
            [title, artist, song, song.get_favourite()])

        self._songs_count += 1
        return iter_

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
        current_playlist_id = self._current_playlist.get_id()
        if current_playlist_id in StaticPlaylists().get_ids():
            return True
        else:
            return False

    @log
    def _is_current_playlist(self, playlist):
        """Check if playlist is currently displayed"""
        if (self._current_playlist
                and playlist.get_id() == self._current_playlist.get_id()):
            return True
        return False

    @log
    def _get_removal_notification_message(self, type_, media_id):
        """ Returns a label for the playlist notification popup

        Handles two cases:
        - playlist removal
        - songs from playlist removal
        """
        msg = ""

        if type_ == PlaylistNotification.Type.PLAYLIST:
            pl_todelete = self.pls_todelete[media_id]
            playlist_title = utils.get_media_title(pl_todelete['playlist'])
            msg = _("Playlist {} removed".format(playlist_title))

        else:
            song_todelete = self._songs_todelete[media_id]
            playlist_title = utils.get_media_title(song_todelete['playlist'])
            song_title = utils.get_media_title(song_todelete['song'])
            msg = _("{} removed from {}".format(
                song_title, playlist_title))

        return msg

    @log
    def _create_notification(self, type_, media_id):
        msg = self._get_removal_notification_message(type_, media_id)
        playlist_notification = PlaylistNotification(
            self._window.notifications_popup, type_, msg, media_id)
        playlist_notification.connect(
            'undo-deletion', self._undo_pending_deletion)
        playlist_notification.connect(
            'finish-deletion', self._finish_pending_deletion)

    @log
    def _stage_playlist_for_deletion(self, menutime, data=None):
        self.model.clear()
        selection = self._sidebar.get_selected_row()
        index = selection.get_index()
        playlist_id = self._current_playlist.get_id()
        self.pls_todelete[playlist_id] = {
            'playlist': selection.playlist,
            'index': index
        }
        row_next = (self._sidebar.get_row_at_index(index + 1)
                    or self._sidebar.get_row_at_index(index - 1))
        self._sidebar.remove(selection)

        if self.player.playing_playlist('Playlist', playlist_id):
            self.player.stop()
            self.set_player_visible(False)

        if row_next:
            self._sidebar.select_row(row_next)
            self._sidebar.emit('row-activated', row_next)

        self._create_notification(
            PlaylistNotification.Type.PLAYLIST, playlist_id)

    @log
    def _undo_pending_deletion(self, playlist_notification):
        """Revert the last playlist removal"""
        notification_type = playlist_notification.type_
        media_id = playlist_notification.media_id

        if notification_type == PlaylistNotification.Type.PLAYLIST:
            pl_todelete = self.pls_todelete[media_id]
            self._add_playlist_to_sidebar(
                pl_todelete['playlist'], pl_todelete['index'])
            self.pls_todelete.pop(media_id)

        else:
            song_todelete = self._songs_todelete[media_id]
            playlist = song_todelete['playlist']
            if (self._current_playlist
                    and playlist.get_id() == self._current_playlist.get_id()):
                iter_ = self._add_song_to_model(
                    song_todelete['song'], self.model, song_todelete['index'])
                if self.player.playing_playlist(
                        'Playlist', self._current_playlist.get_id()):
                    path = self.model.get_path(iter_)
                    self.player.add_song(self.model, path, iter_)
                self._pl_ctrls.update_songs_count(self._songs_count)
            self._songs_todelete.pop(media_id)

    @log
    def _finish_pending_deletion(self, playlist_notification):
        notification_type = playlist_notification.type_
        media_id = playlist_notification.media_id

        if notification_type == PlaylistNotification.Type.PLAYLIST:
            pl_todelete = self.pls_todelete[media_id]
            playlists.delete_playlist(pl_todelete['playlist'])
            self.pls_todelete.pop(media_id)

        else:
            song_todelete = self._songs_todelete[media_id]
            playlists.remove_from_playlist(
                song_todelete['playlist'], [song_todelete['song']])
            self._songs_todelete.pop(media_id)

    @GObject.Property(type=bool, default=False)
    def rename_active(self):
        """Indicate if renaming dialog is active"""
        return self._pl_ctrls.rename_active()

    @log
    def _stage_playlist_for_renaming(self, menuitem, data=None):
        selection = self._sidebar.get_selected_row()
        pl_torename = selection.playlist

        def playlist_renamed_callback(widget):
            new_name = self._pl_ctrls.get_rename_entry_text()
            if not new_name:
                return

            selection.get_child().set_text(new_name)
            pl_torename.set_title(new_name)
            playlists.rename(pl_torename, new_name)
            self._pl_ctrls.set_playlist_name(new_name)
            self._pl_ctrls.disable_rename_playlist()

        self._pl_ctrls.enable_rename_playlist(pl_torename)

        self._pl_ctrls.connect_rename_entry('activate',
                                            playlist_renamed_callback)
        self._pl_ctrls.connect_rename_done_btn('clicked',
                                               playlist_renamed_callback)

    @log
    def _on_playlist_created(self, playlists, playlist):
        """Add new playlist to sidebar"""
        self._add_playlist_to_sidebar(playlist)

    @log
    def _on_song_added_to_playlist(self, playlists, playlist, item):
        if self._is_current_playlist(playlist):
            iter_ = self._add_song_to_model(item, self.model)
            if self.player.playing_playlist(
                    'Playlist', self._current_playlist.get_id()):
                path = self.model.get_path(iter_)
                self.player.add_song(self.model, path, iter_)

    @log
    def _remove_song_from_playlist(self, playlist, item, index):
        if (self._is_current_playlist(playlist)):
            model = self.model
        else:
            return

        iter_ = model.get_iter_from_string(str(index))
        if self.player.playing_playlist(
                'Playlist', self._current_playlist.get_id()):
            self.player.remove_song(model, model.get_path(iter_))
        model.remove(iter_)

        self._songs_count -= 1
        self._pl_ctrls.update_songs_count(self._songs_count)
        return

    @log
    def populate(self):
        """Populate sidebar.
        Do not reload playlists already displayed.
        """
        self._window.notifications_popup.push_loading()
        grilo.populate_playlists(self._offset, self._add_playlist_item)
