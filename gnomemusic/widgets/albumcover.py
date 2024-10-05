# Copyright 2018 The GNOME Music developers
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

from gnomemusic.corealbum import CoreAlbum
from gnomemusic.widgets.albumtile import AlbumTile


@Gtk.Template(resource_path="/org/gnome/Music/ui/AlbumCover.ui")
class AlbumCover(Gtk.FlowBoxChild):
    """FlowBoxChild wrapper for AlbumTile

    Includes cover, album title and artist name.
    """

    __gtype_name__ = "AlbumCover"

    def __init__(self, corealbum: CoreAlbum) -> None:
        """Initialize the AlbumCover

        :param CoreAlbum corealbum: The corealbum to display
        """
        super().__init__()

        self._corealbum = corealbum

        album_tile = AlbumTile()
        album_tile.props.corealbum = corealbum
        self.props.child = album_tile

    @GObject.Property(type=CoreAlbum, flags=GObject.ParamFlags.READABLE)
    def corealbum(self):
        """CoreAlbum object used in AlbumCover

        :returns: The album used
        :rtype: CoreAlbum
        """
        return self._corealbum
