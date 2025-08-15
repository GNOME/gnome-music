# Copyright 2019 The GNOME Music Developers
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

from gi.repository import GObject, Gtk

from gnomemusic.grilowrappers.playlist import Playlist


@Gtk.Template(resource_path="/org/gnome/Music/ui/PlaylistDialogRow.ui")
class PlaylistDialogRow(Gtk.ListBoxRow):

    __gtype_name__ = "PlaylistDialogRow"

    playlist = GObject.Property(type=Playlist, default=None)
    selected = GObject.Property(type=bool, default=False)

    _label = Gtk.Template.Child()
    _selection_icon = Gtk.Template.Child()

    def __init__(self, playlist):
        """Create a row of the PlaylistDialog

        :param Playlist playlist: the associated playlist
        """
        super().__init__()

        self.props.playlist = playlist
        self._label.props.label = playlist.props.title

        self.bind_property(
            "selected", self._selection_icon, "visible",
            GObject.BindingFlags.SYNC_CREATE)
