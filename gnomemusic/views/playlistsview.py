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
from gnomemusic.widgets.playlistswidget import PlaylistsWidget
from gnomemusic.widgets.playlisttile import PlaylistTile


@Gtk.Template(resource_path="/org/gnome/Music/ui/PlaylistsView.ui")
class PlaylistsView(Gtk.Box):
    """Main view for playlists"""

    __gtype_name__ = "PlaylistsView"

    title = GObject.Property(
        type=str, default=_("Playlists"), flags=GObject.ParamFlags.READABLE)

    _sidebar = Gtk.Template.Child()

    def __init__(self, application):
        """Initialize

        :param GtkApplication application: The application object
        """
        super().__init__()

        self.props.name = "playlists"

        self._coremodel = application.props.coremodel
        self._model = self._coremodel.props.playlists_sort

        # This indicates if the current list has been empty and has
        # had no user interaction since.
        self._untouched_list = True

        self._playlist_widget = PlaylistsWidget(application, self)
        self.add(self._playlist_widget)

        self._sidebar.bind_model(self._model, self._add_playlist_to_sidebar)

        self._coremodel.connect(
            "notify::active-media", self._on_active_media_changed)

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

    @GObject.Property(
        type=Playlist, default=None, flags=GObject.ParamFlags.READABLE)
    def current_playlist(self):
        selection = self._sidebar.get_selected_row()
        if selection is None:
            return None

        return selection.props.playlist

    @Gtk.Template.Callback()
    def _on_playlist_activated(self, sidebar, row, untouched=False):
        """Update view with content from selected playlist"""
        if untouched is False:
            self._untouched_list = False

        self.notify("current-playlist")

    def _on_active_media_changed(self, klass, val):
        """Selects the active playlist when an MPRIS client
           has changed it.
        """
        active_media = self._coremodel.props.active_media
        selection = self._sidebar.get_selected_row()
        if (not isinstance(active_media, Playlist)
                or active_media == selection.props.playlist):
            return

        playlist_row = None
        for row in self._sidebar:
            if row.props.playlist == active_media:
                playlist_row = row
                break

        if not playlist_row:
            return

        self._sidebar.select_row(playlist_row)
        self._on_playlist_activated(self._sidebar, playlist_row)

    @GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READABLE)
    def rename_active(self):
        """Indicate if renaming dialog is active"""
        return self._playlist_widget.props.rename_active
