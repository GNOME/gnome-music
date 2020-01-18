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

from gi.repository import GObject, Gtk

from gnomemusic import log
from gnomemusic.grilowrappers.grltrackerplaylists import Playlist
from gnomemusic.widgets.playlistswidget import PlaylistsWidget
from gnomemusic.widgets.playlisttile import PlaylistTile


@Gtk.Template(resource_path="/org/gnome/Music/ui/PlaylistsView.ui")
class PlaylistsView(Gtk.Stack):
    """Main view for playlists"""

    __gtype_name__ = "PlaylistsView"

    _main_container = Gtk.Template.Child()
    _sidebar = Gtk.Template.Child()

    def __repr__(self):
        return '<PlaylistsView>'

    @log
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

        self._playlist_widget = PlaylistsWidget(application, self)
        self._main_container.add(self._playlist_widget)

        self._sidebar.bind_model(self._model, self._add_playlist_to_sidebar)

        self._loaded_id = self._coremodel.connect(
            "playlists-loaded", self._on_playlists_loaded)
        self._coremodel.connect(
            "notify::active-playlist", self._on_active_playlist_changed)

    @log
    def _add_playlist_to_sidebar(self, playlist):
        """Add a playlist to sidebar

        :param GrlMedia playlist: playlist to add
        :param int index: position
        """
        row = PlaylistTile(playlist)
        return row

    def _on_playlists_loaded(self, klass):
        self._coremodel.disconnect(self._loaded_id)
        self._model.connect("items-changed", self._on_playlists_model_changed)

        first_row = self._sidebar.get_row_at_index(0)
        self._sidebar.select_row(first_row)
        self._on_playlist_activated(self._sidebar, first_row)

    def _on_playlists_model_changed(self, model, position, removed, added):
        if removed == 0:
            return

        row_next = (self._sidebar.get_row_at_index(position)
                    or self._sidebar.get_row_at_index(position - 1))
        if row_next:
            self._sidebar.select_row(row_next)
            self._on_playlist_activated(self._sidebar, row_next)

    @GObject.Property(
        type=Playlist, default=None, flags=GObject.ParamFlags.READABLE)
    def current_playlist(self):
        selection = self._sidebar.get_selected_row()
        if selection is None:
            return None
        return selection.props.playlist

    @Gtk.Template.Callback()
    @log
    def _on_playlist_activated(self, sidebar, row):
        """Update view with content from selected playlist"""
        self.notify("current-playlist")

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

    @GObject.Property(type=bool, default=False)
    def rename_active(self):
        """Indicate if renaming dialog is active"""
        return self._playlist_widget.props.rename_active
