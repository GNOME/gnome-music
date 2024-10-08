# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

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
