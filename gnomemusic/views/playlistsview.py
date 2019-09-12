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

from gi.repository import Gdk, GObject, Gtk

from gnomemusic.player import PlayerPlaylist
from gnomemusic.widgets.playlistcontextmenu import PlaylistContextMenu
from gnomemusic.widgets.playlistcontrols import PlaylistControls  # noqa: F401
from gnomemusic.widgets.playlistdialog import PlaylistDialog
from gnomemusic.widgets.notificationspopup import PlaylistNotification
from gnomemusic.widgets.playlisttile import PlaylistTile
from gnomemusic.widgets.songwidget import SongWidget


@Gtk.Template(resource_path="/org/gnome/Music/ui/PlaylistsView.ui")
class PlaylistsView(Gtk.Stack):
    """Main view for playlists"""

    __gtype_name__ = "PlaylistsView"

    _pl_ctrls = Gtk.Template.Child()
    _sidebar = Gtk.Template.Child()
    _view = Gtk.Template.Child()
    _view_ctrlr = Gtk.Template.Child()

    def __init__(self, application, player):
        """Initialize

        :param GtkApplication window: The application object
        :param player: The main player object
        """
        super().__init__(transition_type=Gtk.StackTransitionType.CROSSFADE)

        # FIXME: Make these properties.
        self.name = "playlists"
        self.title = _("Playlists")

        self._coremodel = application.props.coremodel
        self._model = self._coremodel.props.playlists_sort
        self._window = application.props.window
        self._player = player

        # This indicates if the current list has been empty and has
        # had no user interaction since.
        self._untouched_list = True

        self._song_popover = PlaylistContextMenu(application, self._view)

        self._pl_ctrls.props.application = application

        play_song = self._window.lookup_action("play_song")
        play_song.connect("activate", self._play_song)

        add_song = self._window.lookup_action("add_song_to_playlist")
        add_song.connect("activate", self._add_song_to_playlist)

        self._remove_song_action = self._window.lookup_action("remove_song")
        self._remove_song_action.connect(
            "activate", self._stage_song_for_deletion)

        playlist_play_action = self._window.lookup_action("playlist_play")
        playlist_play_action.connect("activate", self._on_play_playlist)

        self._sidebar.bind_model(self._model, self._add_playlist_to_sidebar)

        self._coremodel.connect(
            "notify::active-playlist", self._on_active_playlist_changed)

        self._model.connect("items-changed", self._on_playlists_model_changed)
        self._on_playlists_model_changed(self._model, 0, 0, 0)

    def _add_playlist_to_sidebar(self, playlist):
        """Add a playlist to sidebar

        :param GrlMedia playlist: playlist to add
        :param int index: position
        """
        row = PlaylistTile(playlist)
        return row

    def _on_playlists_model_changed(self, model, position, removed, added):
        if model.get_n_items() == 0:
            self._untouched_list = True
            return
        elif self._untouched_list is True:
            first_row = self._sidebar.get_row_at_index(0)
            self._sidebar.select_row(first_row)
            self._on_playlist_activated(self._sidebar, first_row, True)
            return

        if removed == 0:
            return

        row_next = (self._sidebar.get_row_at_index(position)
                    or self._sidebar.get_row_at_index(position - 1))
        if row_next:
            self._sidebar.select_row(row_next)
            self._on_playlist_activated(self._sidebar, row_next, True)

    @Gtk.Template.Callback()
    def _on_view_right_clicked(self, gesture, n_press, x, y):
        requested_row = self._view.get_row_at_y(y)
        self._view.select_row(requested_row)

        _, y0 = requested_row.translate_coordinates(self._view, 0, 0)
        row_height = requested_row.get_allocated_height()
        rect = Gdk.Rectangle()
        rect.x = x
        rect.y = y0 + 0.5 * row_height

        self._song_popover.props.relative_to = self._view
        self._song_popover.props.pointing_to = rect
        self._song_popover.popup()

    def _play_song(self, menuitem, data=None):
        selected_row = self._view.get_selected_row()
        song_widget = selected_row.get_child()
        self._view.unselect_all()
        self._song_activated(song_widget)

    def _add_song_to_playlist(self, menuitem, data=None):
        selected_row = self._view.get_selected_row()
        song_widget = selected_row.get_child()
        coresong = song_widget.props.coresong

        playlist_dialog = PlaylistDialog(self._window)
        if playlist_dialog.run() == Gtk.ResponseType.ACCEPT:
            playlist = playlist_dialog.props.selected_playlist
            playlist.add_songs([coresong])

        self._view.unselect_all()
        playlist_dialog.destroy()

    def _stage_song_for_deletion(self, menuitem, data=None):
        selected_row = self._view.get_selected_row()
        position = selected_row.get_index()
        song_widget = selected_row.get_child()
        coresong = song_widget.props.coresong

        selection = self._sidebar.get_selected_row()
        selected_playlist = selection.props.playlist

        notification = PlaylistNotification(  # noqa: F841
            self._window.notifications_popup, self._coremodel,
            PlaylistNotification.Type.SONG, selected_playlist, position,
            coresong)

    @Gtk.Template.Callback()
    def _on_playlist_activated(self, sidebar, row, untouched=False):
        """Update view with content from selected playlist"""
        if untouched is False:
            self._untouched_list = False

        playlist = row.props.playlist

        self._view.bind_model(
            playlist.props.model, self._create_song_widget, playlist)

        self._pl_ctrls.props.playlist = playlist

        self._remove_song_action.set_enabled(not playlist.props.is_smart)

    def _on_active_playlist_changed(self, klass, val):
        """Selects the active playlist when an MPRIS client
           has changed it.
        """
        playlist = self._coremodel.props.active_playlist
        selection = self._sidebar.get_selected_row()
        if (playlist is None
                or playlist == selection.props.playlist):
            return

        playlist_row = None
        for row in self._sidebar:
            if row.props.playlist == playlist:
                playlist_row = row
                break

        if not playlist_row:
            return

        self._sidebar.select_row(playlist_row)
        self._on_playlist_activated(self._sidebar, playlist_row)

    def _create_song_widget(self, coresong, playlist):
        can_dnd = not playlist.props.is_smart
        song_widget = SongWidget(coresong, can_dnd, True)
        song_widget.props.show_song_number = False

        song_widget.connect('button-release-event', self._song_activated)
        if can_dnd is True:
            song_widget.connect("widget_moved", self._on_song_widget_moved)

        return song_widget

    def _song_activated(self, widget=None, event=None):
        coresong = None
        if widget is not None:
            coresong = widget.props.coresong

        signal_id = None

        def _on_playlist_loaded(klass, playlist_type):
            self._player.play(coresong)
            self._coremodel.disconnect(signal_id)

        selection = self._sidebar.get_selected_row()
        current_playlist = selection.props.playlist
        signal_id = self._coremodel.connect(
            "playlist-loaded", _on_playlist_loaded)
        self._coremodel.props.active_playlist = current_playlist
        self._coremodel.set_player_model(
            PlayerPlaylist.Type.PLAYLIST, current_playlist.props.model)

        return True

    def _on_play_playlist(self, menuitem, data=None):
        self._song_activated()

    @GObject.Property(type=bool, default=False)
    def rename_active(self):
        """Indicate if renaming dialog is active"""
        return self._pl_ctrls.props.rename_active

    def _on_song_widget_moved(self, target, source_position):
        target_position = target.get_parent().get_index()
        selection = self._sidebar.get_selected_row()
        current_playlist = selection.props.playlist
        current_playlist.reorder(source_position, target_position)
