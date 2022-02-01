# Copyright 2021 The GNOME Music developers
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
from typing import List, Union
import typing

from gi.repository import GObject

if typing.TYPE_CHECKING:
    from gnomemusic.corealbum import CoreAlbum
    from gnomemusic.coreartist import CoreArtist
    from gnomemusic.coresong import CoreSong
    CoreObject = Union[CoreAlbum, CoreArtist, CoreSong]


class PriorityPool(GObject.GObject):
    """Tracks async items that should be prioritized
    """

    _pool: List[int] = []

    def __init__(self) -> None:
        """
        """
        super().__init__()

    def add(self, coreobjects: List[CoreObject], reset: bool = False) -> None:
        ids = [id(coreobject) for coreobject in coreobjects]

        if reset:
            PriorityPool._pool = ids
        else:
            PriorityPool._pool += ids

    @GObject.Property()
    def pool(self) -> List[int]:
        return PriorityPool._pool

    @pool.setter  # type: ignore
    def pool(self, value: List[CoreObject]) -> None:
        self.add(value, True)
