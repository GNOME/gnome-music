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

from gi.repository import Gdk, Gio, GLib, GObject, Gtk, Pango

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.player import ValidationStatus, PlayerPlaylist
from gnomemusic.playlists import Playlists, StaticPlaylists
from gnomemusic.views.baseview import BaseView
from gnomemusic.widgets.notificationspopup import PlaylistNotification
from gnomemusic.widgets.playlistcontextmenu import PlaylistContextMenu
from gnomemusic.widgets.playlistcontrols import PlaylistControls
from gnomemusic.widgets.playlistdialog import PlaylistDialog
from gnomemusic.widgets.sidebarrow import SidebarRow
import gnomemusic.utils as utils

playlists = Playlists.get_default()


class PlaylistView(BaseView):
    """Main view for playlists"""

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
            'playlists', _("Playlists"), window, sidebar_container)

        self._window = window
        self.player = player

        self._view.get_style_context().add_class('songs-list')

        self._add_list_renderers()

        self._pl_ctrls = PlaylistControls()
        self._pl_ctrls.connect('playlist-renamed', self._on_playlist_renamed)

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
        sidebar_container.get_style_context().add_class('sidebar')
        self._sidebar.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._sidebar.connect('row-activated', self._on_playlist_activated)

        self._grid.child_set_property(sidebar_container, 'top-attach', 0)
        self._grid.child_set_property(sidebar_container, 'height', 2)

        self._iter_to_clean = None
        self._iter_to_clean_model = None
        self._current_playlist = None
        self._current_playlist_index = None
        self._plays_songs_on_activation = False
        self.pls_todelete = {}
        self._songs_todelete = {}
        self._songs_count = 0

        self.model.connect('row-inserted', self._on_song_inserted)
        self.model.connect('row-deleted', self._on_song_deleted)

        self.player.connect('song-changed', self._update_model)
        self.player.connect('song-validated', self._on_song_validated)
        playlists.connect('playlist-created', self._on_playlist_created)
        playlists.connect('playlist-updated', self._on_playlist_update)
        playlists.connect(
            'song-added-to-playlist', self._on_song_added_to_playlist)

        self.show_all()

    @log
    def _update_songs_count(self, songs_count):
        self._songs_count = songs_count
        self._pl_ctrls.props.songs_count = songs_count

    @log
    def _setup_view(self):
        view_container = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self._box.pack_start(view_container, True, True, 0)

        self._view = Gtk.TreeView()
        self._view.set_headers_visible(False)
        self._view.set_valign(Gtk.Align.START)
        self._view.set_model(self.model)
        self._view.set_activate_on_single_click(True)
        self._view.get_selection().set_mode(Gtk.SelectionMode.SINGLE)

        self._view.connect('row-activated', self._on_song_activated)
        self._view.connect('drag-begin', self._drag_begin)
        self._view.connect('drag-end', self._drag_end)
        self._song_drag = {'active': False}

        self._controller = Gtk.GestureMultiPress().new(self._view)
        self._controller.props.propagation_phase = Gtk.PropagationPhase.CAPTURE
        self._controller.props.button = Gdk.BUTTON_SECONDARY
        self._controller.connect("pressed", self._on_view_right_clicked)

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
                PlayerPlaylist.Type.PLAYLIST, self._current_playlist.get_id()):
            cell.set_visible(False)
            return

        if not model.iter_is_valid(_iter):
            return

        current_song = self.player.props.current_song
        if model[_iter][11] == ValidationStatus.FAILED:
            cell.set_property('icon-name', self._error_icon_name)
            cell.set_visible(True)
        elif model[_iter][5].get_id() == current_song.get_id():
            cell.set_property('icon-name', self._now_playing_icon_name)
            cell.set_visible(True)
        else:
            cell.set_visible(False)

    @log
    def _update_model(self, player, position):
        """Updates model when the song changes

        :param Player player: The main player object
        :param int position: current song position
        """
        if self._current_playlist is None:
            return

        if self._iter_to_clean:
            self._iter_to_clean_model[self._iter_to_clean][10] = False
        if not player.playing_playlist(
                PlayerPlaylist.Type.PLAYLIST, self._current_playlist.get_id()):
            return False

        iter_ = self.model.get_iter_from_string(str(position))
        self.model[iter_][10] = True
        path = self.model.get_path(iter_)
        self._view.scroll_to_cell(path, None, False, 0., 0.)
        if self.model[iter_][8] != self._error_icon_name:
            self._iter_to_clean = iter_.copy()
            self._iter_to_clean_model = self.model

        return False

    @log
    def _add_playlist_item(
            self, source, param, playlist, remaining=0,
            select_playlist_id=None):
        """Grilo.populate_playlists callback.

        Add all playlists found by Grilo to sidebar

        :param GrlTrackerSource source: tracker source
        :param int param: param
        :param GrlMedia playlist: playlist to add
        :param int remaining: next playlist_id or zero if None
        :param str select_playlist_id: playlist id to select on load
        """
        if not playlist:
            self._window.notifications_popup.pop_loading()
            if not self._sidebar.get_selected_row():
                first_row = self._sidebar.get_row_at_index(0)
                self._sidebar.select_row(first_row)
                first_row.emit('activate')
            return

        select_playlist = (playlist.get_id() == select_playlist_id)
        self._add_playlist_to_sidebar(playlist, None, select_playlist)

    @log
    def _add_playlist_to_sidebar(
            self, playlist, index=None, select_playlist=False):
        """Add a playlist to sidebar

        :param GrlMedia playlist: playlist to add
        :param int index: position
        """
        if index is None:
            index = -1
        if playlists.is_static_playlist(playlist):
            index = 0

        title = utils.get_media_title(playlist)
        row = SidebarRow()
        row.props.text = title
        # FIXME: Passing the Grl.Media with the row object is ugly.
        row.playlist = playlist

        self._sidebar.insert(row, index)
        self._offset += 1

        if select_playlist:
            self._sidebar.select_row(row)
            row.emit('activate')

    @log
    def _on_song_validated(self, player, index, status):
        if self._current_playlist is None:
            return

        if not self.player.playing_playlist(
                PlayerPlaylist.Type.PLAYLIST, self._current_playlist.get_id()):
            return

        iter_ = self.model.get_iter_from_string(str(index))
        self.model[iter_][11] = status

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
                return GLib.SOURCE_REMOVE

            if self._star_handler.star_renderer_click:
                self._star_handler.star_renderer_click = False
                return GLib.SOURCE_REMOVE

            _iter = None
            if path:
                _iter = self.model.get_iter(path)
            playlist_id = self._current_playlist.get_id()
            self.player.set_playlist(
                PlayerPlaylist.Type.PLAYLIST, playlist_id, self.model, _iter)
            self.player.play()

            return GLib.SOURCE_REMOVE

        # 'row-activated' signal is emitted before 'drag-begin' signal.
        # Need to wait to check if drag and drop operation is active.
        GLib.idle_add(activate_song)

    @log
    def _on_view_right_clicked(self, gesture, n_press, x, y):
        (path, column, cell_x, cell_y) = self._view.get_path_at_pos(x, y)
        self._view.get_selection().select_path(path)
        row_height = self._view.get_cell_area(path, None).height

        rect = Gdk.Rectangle()
        rect.x = x
        rect.y = y - cell_y + 0.5 * row_height

        self._song_popover.props.relative_to = self._view
        self._song_popover.props.pointing_to = rect
        self._song_popover.popup()

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

        Update player's playlist if the playlist is being played.
        """
        if not self._song_drag['active']:
            return

        new_pos = self._song_drag['new_pos']
        prev_pos = int(path.to_string())

        if abs(new_pos - prev_pos) == 1:
            return

        first_pos = min(new_pos, prev_pos)
        last_pos = max(new_pos, prev_pos)

        # update player's playlist if necessary
        if self.player.playing_playlist(
                PlayerPlaylist.Type.PLAYLIST, self._current_playlist.get_id()):
            if new_pos < prev_pos:
                prev_pos -= 1
            else:
                new_pos -= 1
            current_index = self.player.playlist_change_position(
                prev_pos, new_pos)
            if current_index >= 0:
                current_iter = model.get_iter_from_string(str(current_index))
                self._iter_to_clean = current_iter
                self._iter_to_clean_model = model

        # update playlist's storage
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
        self._view.emit('row-activated', path, None)

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
                self._star_handler.star_renderer_click = False
                self._on_playlist_activated(self._sidebar, row)
                break

    @log
    def activate_playlist(self, playlist_id):
        """Selects and starts playing a playlist.

        If the view has not been populated yet, populate it and then
        select the requested playlist. Otherwise, directly select the
        requested playlist and start playing.

        :param str playlist_id: requested playlist id
        """
        if not self._init:
            self._plays_songs_on_activation = True
            self._populate(playlist_id)
            return

        playlist_row = None
        for row in self._sidebar:
            if row.playlist.get_id() == playlist_id:
                playlist_row = row
                break

        if not playlist_row:
            return

        selection = self._sidebar.get_selected_row()
        if selection.get_index() == row.get_index():
            self._on_play_activate(None)
        else:
            self._plays_songs_on_activation = True
            self._sidebar.select_row(row)
            row.emit('activate')

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
            self._pl_ctrls.disable_rename_playlist()

        self._current_playlist = playlist
        self._pl_ctrls.props.playlist_name = playlist_name
        self._current_playlist_index = row.get_index()

        # if the active queue has been set by this playlist,
        # use it as model, otherwise build the liststore
        self._view.set_model(None)
        self.model.clear()
        self._iter_to_clean = None
        self._iter_to_clean_model = None
        self._update_songs_count(0)
        self._pl_ctrls.props.display_songs_count = False
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
            self._pl_ctrls.props.display_songs_count = True
            if self._plays_songs_on_activation:
                first_iter = self.model.get_iter_first()
                self.player.set_playlist(
                    PlayerPlaylist.Type.PLAYLIST,
                    self._current_playlist.get_id(), self.model, first_iter)
                self.player.play()
                self._plays_songs_on_activation = False

    @log
    def _add_song_to_model(self, song, model, index=-1):
        """Add song to a playlist
        :param Grl.Media song: song to add
        :param Gtk.ListStore model: model
        """
        if not song:
            return None

        title = utils.get_media_title(song)
        song.set_title(title)
        artist = utils.get_artist_name(song)
        iter_ = model.insert_with_valuesv(
            index, [2, 3, 5, 9],
            [title, artist, song, song.get_favourite()])

        self._update_songs_count(self._songs_count + 1)
        return iter_

    @log
    def _on_play_activate(self, menuitem, data=None):
        self._view.emit('row-activated', None, None)

    @log
    def _current_playlist_is_protected(self):
        current_playlist_id = self._current_playlist.get_id()
        return current_playlist_id in StaticPlaylists().get_ids()

    @log
    def _is_current_playlist(self, playlist):
        """Check if playlist is currently displayed"""
        if self._current_playlist is None:
            return False

        return playlist.get_id() == self._current_playlist.get_id()

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

        if self.player.playing_playlist(
                PlayerPlaylist.Type.PLAYLIST, playlist_id):
            self.player.stop()
            self._window.set_player_visible(False)

        if row_next:
            self._sidebar.select_row(row_next)
            row_next.emit('activate')

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
                playlist_id = self._current_playlist.get_id()
                if self.player.playing_playlist(
                        PlayerPlaylist.Type.PLAYLIST, playlist_id):
                    song = self.model[iter_][5]
                    path = self.model.get_path(iter_)
                    self.player.add_song(song, int(path.to_string()))
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
        return self._pl_ctrls.props.rename_active

    @log
    def _stage_playlist_for_renaming(self, menuitem, data=None):
        selection = self._sidebar.get_selected_row()
        pl_torename = selection.playlist
        self._pl_ctrls.enable_rename_playlist(pl_torename)

    @log
    def _on_playlist_renamed(self, arguments, new_name):
        selection = self._sidebar.get_selected_row()
        selection.props.text = new_name

        pl_torename = selection.playlist
        pl_torename.set_title(new_name)
        playlists.rename(pl_torename, new_name)

    @log
    def _on_playlist_created(self, playlists, playlist):
        """Adds new playlist to sidebar

        If the sidebar has not been populated yet, it has no effect:
        the playlist will be displayed once the playlists are loaded.
        """
        if not self._init:
            return
        self._add_playlist_to_sidebar(playlist)

    @log
    def _on_song_added_to_playlist(self, playlists, playlist, item):
        if self._is_current_playlist(playlist):
            iter_ = self._add_song_to_model(item, self.model)
            playlist_id = self._current_playlist.get_id()
            if self.player.playing_playlist(
                    PlayerPlaylist.Type.PLAYLIST, playlist_id):
                path = self.model.get_path(iter_)
                self.player.add_song(item, int(path.to_string()))

    @log
    def _remove_song_from_playlist(self, playlist, item, index):
        if not self._is_current_playlist(playlist):
            return

        if self.player.playing_playlist(
                PlayerPlaylist.Type.PLAYLIST, self._current_playlist.get_id()):
            self.player.remove_song(index)

        iter_ = self.model.get_iter_from_string(str(index))
        self.model.remove(iter_)

        self._update_songs_count(self._songs_count - 1)

    @log
    def _populate(self, data=None):
        """Populate sidebar.
        Do not reload playlists already displayed.
        """
        self._window.notifications_popup.push_loading()
        grilo.populate_playlists(
            self._offset, self._add_playlist_item, -1, data)
        self._init = True
