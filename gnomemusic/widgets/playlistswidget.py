# Copyright 2020 The GNOME Music developers
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

from gnomemusic.player import PlayerPlaylist
from gnomemusic.widgets.notificationspopup import PlaylistNotification
from gnomemusic.widgets.playlistcontextmenu import PlaylistContextMenu
from gnomemusic.widgets.playlistcontrols import PlaylistControls  # noqa: F401
from gnomemusic.widgets.playlistdialog import PlaylistDialog
from gnomemusic.widgets.songwidget import SongWidget


@Gtk.Template(resource_path="/org/gnome/Music/ui/PlaylistsWidget.ui")
class PlaylistsWidget(Gtk.Box):
    """Widget to display the playlist controls and list"""

    __gtype_name__ = "PlaylistsWidget"

    _pl_ctrls = Gtk.Template.Child()
    _songs_list = Gtk.Template.Child()
    _songs_list_ctrlr = Gtk.Template.Child()

    def __init__(self, application, playlists_view):
        """Initialize the PlaylistsWidget.

        :param Application application: The application object
        :param PlaylistsView playlists_view: The parent view
        """
        super().__init__()

        self._application = application
        self._window = application.props.window
        self._coremodel = application.props.coremodel
        self._player = application.props.player
        self._playlists_view = playlists_view

        self._playlists_view.connect(
            "notify::current-playlist", self._on_current_playlist_changed)

        self._pl_ctrls.props.application = application

        self._song_popover = PlaylistContextMenu(application, self._songs_list)

        play_song = self._window.lookup_action("play_song")
        play_song.connect("activate", self._play_song)

        add_song = self._window.lookup_action("add_song_to_playlist")
        add_song.connect("activate", self._add_song_to_playlist)

        self._remove_song_action = self._window.lookup_action("remove_song")
        self._remove_song_action.connect(
            "activate", self._stage_song_for_deletion)

        playlist_play_action = self._window.lookup_action("playlist_play")
        playlist_play_action.connect("activate", self._on_play_playlist)

        self._coremodel.connect(
            "smart-playlist-change", self._on_smart_playlist_change)

    def _on_current_playlist_changed(self, playlists_view, value):
        """Update view with content from selected playlist"""
        playlist = self._playlists_view.props.current_playlist

        self._songs_list.bind_model(
            playlist.props.model, self._create_song_widget, playlist)
        if playlist.props.is_smart:
            playlist.update()

        self._pl_ctrls.props.playlist = playlist

        self._remove_song_action.set_enabled(not playlist.props.is_smart)

    def _create_song_widget(self, coresong, playlist):
        can_dnd = not playlist.props.is_smart
        song_widget = SongWidget(coresong, can_dnd, True)
        song_widget.props.show_song_number = False

        song_widget.connect("button-release-event", self._on_song_activated)
        if can_dnd is True:
            song_widget.connect("widget_moved", self._on_song_widget_moved)

        return song_widget

    def _on_song_activated(self, widget, event):
        coresong = widget.props.coresong
        self._play(coresong)
        return True

    def _play(self, coresong=None):
        signal_id = None

        def _on_playlist_loaded(klass, playlist_type):
            self._player.play(coresong)
            self._coremodel.disconnect(signal_id)

        current_playlist = self._playlists_view.props.current_playlist
        signal_id = self._coremodel.connect(
            "playlist-loaded", _on_playlist_loaded)
        self._coremodel.props.active_media = current_playlist

    def _on_song_widget_moved(self, target, source_position):
        target_position = target.get_parent().get_index()
        current_playlist = self._playlists_view.props.current_playlist
        current_playlist.reorder(source_position, target_position)

    def _on_smart_playlist_change(self, coremodel):
        current_playlist = self._playlists_view.props.current_playlist
        if (current_playlist is not None
                and current_playlist.props.is_smart):
            current_playlist.update()

    @Gtk.Template.Callback()
    def _songs_list_right_click(self, gesture, n_press, x, y):
        requested_row = self._songs_list.get_row_at_y(y)
        self._songs_list.select_row(requested_row)

        _, y0 = requested_row.translate_coordinates(self._songs_list, 0, 0)
        row_height = requested_row.get_allocated_height()
        rect = Gdk.Rectangle()
        rect.x = x
        rect.y = y0 + 0.5 * row_height

        self._song_popover.props.relative_to = self._songs_list
        self._song_popover.props.pointing_to = rect
        self._song_popover.popup()

    def _play_song(self, menuitem, data=None):
        selected_row = self._songs_list.get_selected_row()
        song_widget = selected_row.get_child()
        coresong = song_widget.props.coresong
        self._songs_list.unselect_all()
        self._play(coresong)

    def _add_song_to_playlist(self, menuitem, data=None):
        selected_row = self._songs_list.get_selected_row()
        song_widget = selected_row.get_child()
        coresong = song_widget.props.coresong

        playlist_dialog = PlaylistDialog(self._application)
        playlist_dialog.props.transient_for = self._window
        if playlist_dialog.run() == Gtk.ResponseType.ACCEPT:
            playlist = playlist_dialog.props.selected_playlist
            playlist.add_songs([coresong])

        self._songs_list.unselect_all()
        playlist_dialog.destroy()

    def _stage_song_for_deletion(self, menuitem, data=None):
        selected_row = self._songs_list.get_selected_row()
        position = selected_row.get_index()
        song_widget = selected_row.get_child()
        coresong = song_widget.props.coresong

        current_playlist = self._playlists_view.props.current_playlist

        notification = PlaylistNotification(  # noqa: F841
            self._window.notifications_popup, self._application,
            PlaylistNotification.Type.SONG, current_playlist, position,
            coresong)

    def _on_play_playlist(self, menuitem, data=None):
        self._play()

    @GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READABLE)
    def rename_active(self):
        """Indicate if renaming dialog is active"""
        return self._pl_ctrls.props.rename_active
