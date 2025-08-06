# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from typing import Optional

from gi.repository import GObject, Gtk

from gnomemusic.coreartist import CoreAlbum
from gnomemusic.coverpaintable import CoverPaintable
from gnomemusic.utils import ArtSize, DefaultIconType


@Gtk.Template(resource_path='/org/gnome/Music/ui/AlbumTile.ui')
class AlbumTile(Gtk.Box):

    __gtype_name__ = "AlbumTile"

    _album_label = Gtk.Template.Child()
    _artist_label = Gtk.Template.Child()
    _cover_image = Gtk.Template.Child()

    def __init__(self) -> None:
        """Initialise AlbumTile"""
        super().__init__()

        self._corealbum: Optional[CoreAlbum] = None

        self._cover_image.set_size_request(
            ArtSize.MEDIUM.width, ArtSize.MEDIUM.height)
        self._cover_image.props.pixel_size = ArtSize.MEDIUM.height
        self._cover_image.props.paintable = CoverPaintable(
            self, ArtSize.MEDIUM, icon_type=DefaultIconType.ALBUM)

    @GObject.Property(
        type=CoreAlbum, flags=GObject.ParamFlags.READWRITE, default=None)
    def corealbum(self) -> CoreAlbum:
        """CoreAlbum to use for AlbumTile

        :returns: The album object
        :rtype: CoreAlbum
        """
        return self._corealbum

    @corealbum.setter  # type: ignore
    def corealbum(self, corealbum: CoreAlbum) -> None:
        """CoreAlbum setter

        :param CoreAlbum corealbum: The corealbum to use
        """
        self._corealbum = corealbum

        self._cover_image.props.paintable.props.coreobject = corealbum
        self._album_label.props.label = corealbum.props.title
        self._album_label.props.tooltip_text = corealbum.props.title
        self._artist_label.props.label = corealbum.props.artist
        self._artist_label.props.tooltip_text = corealbum.props.artist
