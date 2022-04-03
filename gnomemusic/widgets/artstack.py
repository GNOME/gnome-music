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

from __future__ import annotations
from typing import Optional, Union
import typing

from gi.repository import GObject, Gtk

from gnomemusic.coverpaintable import CoverPaintable
from gnomemusic.utils import ArtSize, DefaultIconType
if typing.TYPE_CHECKING:
    from gnomemusic.corealbum import CoreAlbum
    from gnomemusic.coreartist import CoreArtist
    from gnomemusic.coresong import CoreSong


if typing.TYPE_CHECKING:
    CoreObject = Union[CoreAlbum, CoreArtist, CoreSong]


class ArtStack(Gtk.Stack):
    """Provides a smooth transition between image states

    Uses a Gtk.Stack to provide an in-situ transition between an image
    state. Between the 'loading' and 'default' art state and in between
    songs.
    """

    __gtype_name__ = "ArtStack"

    def __init__(self, size: ArtSize = ArtSize.MEDIUM) -> None:
        """Initialize the ArtStack

        :param ArtSize size: The size of the art used for the cover
        """
        super().__init__()

        self._art_type = DefaultIconType.ALBUM
        self._coreobject: Optional[CoreObject] = None
        self._cover_paintable = CoverPaintable(
            self, size, self._art_type)
        self._size = size

        self._cover = Gtk.Image()
        self._cover.props.visible = True

        self.add_child(self._cover)

        self.props.size = size

    @GObject.Property(type=object, flags=GObject.ParamFlags.READWRITE)
    def size(self) -> ArtSize:
        """Size of the cover

        :returns: The size used
        :rtype: ArtSize
        """
        return self._size

    @size.setter  # type: ignore
    def size(self, value: ArtSize) -> None:
        """Set the cover size

        :param ArtSize value: The size to use for the cover
        """
        self.set_size_request(value.width, value.height)
        self._size = value

    @GObject.Property(type=object, flags=GObject.ParamFlags.READWRITE)
    def art_type(self) -> DefaultIconType:
        """Type of the stack cover

        :returns: The type of the default icon
        :rtype: DefaultIconType
        """
        return self._art_type

    @art_type.setter  # type: ignore
    def art_type(self, value: DefaultIconType) -> None:
        """Set the stack cover type

        :param DefaultIconType value: The default icon type for the
            stack
        """
        self._art_type = value

        self._cover_paintable.props.icon_type = self._art_type

    @GObject.Property(type=object, default=None)
    def coreobject(self) -> Optional[CoreObject]:
        return self._coreobject

    @coreobject.setter  # type: ignore
    def coreobject(self, coreobject: CoreObject) -> None:
        if coreobject is self._coreobject:
            return

        self._coreobject = coreobject
        self._cover_paintable.props.coreobject = coreobject
        self._cover.props.paintable = self._cover_paintable
