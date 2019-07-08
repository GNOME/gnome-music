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

from gi.repository import GObject, Gio, Gtk

from gnomemusic import log
from gnomemusic.player import PlayerPlaylist
from gnomemusic.views.baseview import BaseView
from gnomemusic.widgets.playlistcontextmenu import PlaylistContextMenu
from gnomemusic.widgets.playlistcontrols import PlaylistControls
from gnomemusic.widgets.sidebarrow import SidebarRow
from gnomemusic.widgets.songwidget import SongWidget


class PlaylistsView(BaseView):
    """Main view for playlists"""

    def __repr__(self):
        return '<PlaylistsView>'

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

        self._coremodel = window._app.props.coremodel
        self._model = self._coremodel.props.playlists
        self._window = window
        self.player = player

        # self._view.get_style_context().add_class('songs-list')

        # self._add_list_renderers()

        self._pl_ctrls = PlaylistControls()
        self._pl_ctrls.connect('playlist-renamed', self._on_playlist_renamed)

        self._song_popover = PlaylistContextMenu(self._view)

        # play_song = Gio.SimpleAction.new('play_song', None)
        # play_song.connect('activate', self._play_song)
        # self._window.add_action(play_song)

        # add_song_to_playlist = Gio.SimpleAction.new(
        #     'add_song_to_playlist', None)
        # add_song_to_playlist.connect('activate', self._add_song_to_playlist)
        # self._window.add_action(add_song_to_playlist)

        # self._remove_song_action = Gio.SimpleAction.new('remove_song', None)
        # self._remove_song_action.connect(
        #     'activate', self._stage_song_for_deletion)
        # self._window.add_action(self._remove_song_action)

        # playlist_play_action = Gio.SimpleAction.new('playlist_play', None)
        # playlist_play_action.connect('activate', self._on_play_activate)
        # self._window.add_action(playlist_play_action)

        # self._playlist_delete_action = Gio.SimpleAction.new(
        #     'playlist_delete', None)
        # self._playlist_delete_action.connect(
        #     'activate', self._stage_playlist_for_deletion)
        # self._window.add_action(self._playlist_delete_action)
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
        self._plays_songs_on_activation = False
        self._songs_todelete = {}
        self._songs_count = 0

        self._sidebar.bind_model(
            self._coremodel.props.playlists_sort,
            self._add_playlist_to_sidebar)

        self.show_all()

    @log
    def _update_songs_count(self, songs_count):
        self._songs_count = songs_count
        self._pl_ctrls.props.songs_count = songs_count

    @log
    def _setup_view(self):
        view_container = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self._box.pack_start(view_container, True, True, 0)

        self._view = Gtk.ListBox()

        # self._controller = Gtk.GestureMultiPress().new(self._view)
        # self._controller.props.propagation_phase =
        #    Gtk.PropagationPhase.CAPTURE
        # self._controller.props.button = Gdk.BUTTON_SECONDARY
        # self._controller.connect("pressed", self._on_view_right_clicked)

        view_container.add(self._view)

    @log
    def _add_playlist_to_sidebar(self, playlist):
        """Add a playlist to sidebar

        :param GrlMedia playlist: playlist to add
        :param int index: position
        """
        row = SidebarRow()
        row.props.text = playlist.props.title
        row.playlist = playlist

        return row

    def _on_playlists_model_changed(self, model, position, removed, added):
        if removed == 0:
            return

    @log
    def _on_playlist_activated(self, sidebar, row, data=None):
        """Update view with content from selected playlist"""
        playlist = row.playlist
        playlist_name = playlist.props.title

        if self.rename_active:
            self._pl_ctrls.disable_rename_playlist()

        self._view.bind_model(playlist.props.model, self._create_song_widget)

        self._current_playlist = playlist
        self._pl_ctrls.props.playlist_name = playlist_name
        self._update_songs_count(playlist.props.count)
        playlist.connect("notify::count", self._on_song_count_changed)

        self._playlist_rename_action.set_enabled(not playlist.props.is_smart)

    def _on_song_count_changed(self, playlist, value):
        self._update_songs_count(playlist.props.count)

    def _create_song_widget(self, coresong):
        song_widget = SongWidget(coresong)

        song_widget.connect('button-release-event', self._song_activated)

        return song_widget

    def _song_activated(self, widget, event):
        self._coremodel.set_playlist_model(
            PlayerPlaylist.Type.PLAYLIST, widget.props.coresong,
            self._current_playlist.props.model)
        self.player.play()

        return True

    @log
    def _is_current_playlist(self, playlist):
        """Check if playlist is currently displayed"""
        if self._current_playlist is None:
            return False

        return playlist.props.pl_id == self._current_playlist.props.pl_id

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
        pl_torename.rename(new_name)

    @log
    def _populate(self, data=None):
        """Populate sidebar.
        Do not reload playlists already displayed.
        """
        self._init = True
