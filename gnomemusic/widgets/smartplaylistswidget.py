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

from gi.repository import Gtk

from gnomemusic.widgets.smartplaylistcover import SmartPlaylistCover


@Gtk.Template(resource_path="/org/gnome/Music/ui/SmartPlaylistsWidget.ui")
class SmartPlaylistsWidget(Gtk.Box):
    """

    """

    __gtype_name__ = "SmartPlaylistsWidget"

    _flowbox = Gtk.Template.Child()

    def __init__(self, coremodel, player):
        """FIXME! briefly describe function

        :param CoreModel coremodel: Main CoreModel object
        :param Player player: Main Player object
        """
        super().__init__()

        self._coremodel = coremodel
        self._smart_pls_model = self._coremodel.props.smart_playlists_sort

        self._player = player

        self._playing_cover = None

        self._flowbox.bind_model(self._smart_pls_model, self._add_playlist)
        self._smart_pls_model.connect(
            "items-changed", self._on_model_items_changed)
        self._on_model_items_changed(
            self._smart_pls_model, 0, 0, self._smart_pls_model.get_n_items())

    def _add_playlist(self, smart_playlist):
        child = SmartPlaylistCover(
            smart_playlist, self._coremodel, self._player)
        child.connect("notify::state", self._on_cover_state_changed)

        return child

    def _on_model_items_changed(self, model, position, removed, added):
        if added == 0:
            return

        for index in range(added):
            cover = self._flowbox.get_child_at_index(position + index)
            cover.set_visibility()

    def _on_cover_state_changed(self, selected_cover, value):
        if (selected_cover.props.state != SmartPlaylistCover.State.PLAYING
                or selected_cover == self._playing_cover):
            return

        if self._playing_cover is not None:
            self._playing_cover.stop()
        self._playing_cover = selected_cover

    def select(self, playlist):
        """Changes the state of the corresponding cover to playing.
           This function is called when the playlist is starts playing
           from MPRIS.

        :param SmartPlaylist playlist: new active playlist
        """
        for cover in self._flowbox:
            if cover.props.playlist == playlist:
                cover.props.state = SmartPlaylistCover.State.PLAYING
                break
