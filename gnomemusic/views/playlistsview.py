# Copyright 2020 The GNOME Music Developers
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

from gi.repository import GObject, Gtk

from gnomemusic.grilowrappers.grltrackerplaylists import Playlist
from gnomemusic.widgets.userplaylistwidget import UserPlaylistWidget
from gnomemusic.widgets.playlisttile import PlaylistTile
from gnomemusic.widgets.smartplaylistswidget import SmartPlaylistsWidget


@Gtk.Template(resource_path="/org/gnome/Music/ui/PlaylistsView.ui")
class PlaylistsView(Gtk.Stack):
    """Main view for playlists"""

    __gtype_name__ = "PlaylistsView"

    _all_playlists_sidebar = Gtk.Template.Child()
    _main_container = Gtk.Template.Child()
    _smart_sidebar = Gtk.Template.Child()
    _user_sidebar = Gtk.Template.Child()

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
        self._users_playlists_model = self._coremodel.props.user_playlists_sort
        self._window = application.props.window
        self._player = player

        self._user_playlist_view = UserPlaylistWidget(application, self)
        self._main_container.add(self._user_playlist_view)

        self._smart_playlist_view = SmartPlaylistsWidget(
            self._coremodel, player)
        self._main_container.add(self._smart_playlist_view)

        self._user_sidebar.bind_model(
            self._users_playlists_model, self._add_user_playlist_to_sidebar)

        self._coremodel.connect(
            "notify::active-playlist", self._on_active_playlist_changed)

        self._users_playlists_model.connect(
            "items-changed", self._on_user_playlists_model_changed)
        self._on_user_playlists_model_changed(
            self._users_playlists_model, 0, 0, 0)

    def _add_user_playlist_to_sidebar(self, playlist):
        """Add a playlist to sidebar

        :param GrlMedia playlist: playlist to add
        :param int index: position
        """
        row = PlaylistTile(playlist)
        return row

    def _on_user_playlists_model_changed(
            self, model, position, removed, added):
        if model.get_n_items() == 0:
            smart_row = self._smart_sidebar.get_row_at_index(0)
            self._smart_sidebar.select_row(smart_row)
            self._on_smart_playlist_activated(self._smart_sidebar, smart_row)
            self._all_playlists_sidebar.props.visible = False
            return

        self._all_playlists_sidebar.props.visible = (model.get_n_items() > 0)
        if removed == 0:
            return

        row_next = (self._user_sidebar.get_row_at_index(position)
                    or self._user_sidebar.get_row_at_index(position - 1))
        if row_next:
            self._user_sidebar.select_row(row_next)
            self._on_user_playlist_activated(self._user_sidebar, row_next)

    @GObject.Property(
        type=Playlist, default=None, flags=GObject.ParamFlags.READABLE)
    def current_playlist(self):
        selection = self._user_sidebar.get_selected_row()
        if selection is None:
            return None
        return selection.props.playlist

    @Gtk.Template.Callback()
    def _on_smart_playlist_activated(self, sidebar, row):
        self._user_sidebar.unselect_all()
        self._user_playlist_view.props.visible = False
        self._smart_playlist_view.props.visible = True

    @Gtk.Template.Callback()
    def _on_user_playlist_activated(self, sidebar, row):
        """Update view with content from selected playlist"""
        self._smart_sidebar.unselect_all()
        self._smart_playlist_view.props.visible = False
        self._user_playlist_view.props.visible = True
        self.notify("current-playlist")

    def _on_active_playlist_changed(self, klass, val):
        """Selects the active playlist when an MPRIS client
           has changed it.
        """
        playlist = self._coremodel.props.active_playlist
        if playlist is None:
            return

        if playlist.props.is_smart:
            smart_row = self._smart_sidebar.get_row_at_index(0)
            self._smart_sidebar.select_row(smart_row)
            self._on_smart_playlist_activated(self._smart_sidebar, smart_row)
            self._smart_playlist_view.select(playlist)
            return

        playlist_row = None
        for row in self._user_sidebar:
            if row.props.playlist == playlist:
                playlist_row = row
                break

        if not playlist_row:
            return

        self._user_sidebar.select_row(playlist_row)
        self._on_user_playlist_activated(self._user_sidebar, playlist_row)

    @GObject.Property(type=bool, default=False)
    def rename_active(self):
        """Indicate if renaming dialog is active"""
        return self._user_playlist_view.props.rename_active
