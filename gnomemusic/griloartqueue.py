# Copyright 2022 The GNOME Music developers
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
from typing import Dict, List, Union
import typing

from gi.repository import GLib, GObject

from gnomemusic.storeart import StoreArt
from gnomemusic.utils import CoreObjectType
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.corealbum import CoreAlbum
    from gnomemusic.coreartist import CoreArtist
    from gnomemusic.coresong import CoreSong
    CoreObject = Union[CoreAlbum, CoreArtist, CoreSong]


class GriloArtQueue(GObject.GObject):
    """Queue for Grilo art lookup

    Grilo remote art lookup is quite taxing when done in parallel. This
    class runs the lookup queries serialized.
    """

    __gtype_name__ = "GriloArtQueue"

    _queue: Dict[CoreObject, CoreObjectType] = {}
    _active_queue: List[CoreObject] = []

    def __init__(self, application: Application) -> None:
        """Initialize GriloArtQueue

        :param Application application: The application instance
        """
        super().__init__()

        self._coregrilo = application.props.coregrilo

        self._timeout_id = 0

    def queue(
            self, coreobject: CoreObject,
            coreobjecttype: CoreObjectType) -> None:
        """Queue Grilo art lookup for the coreobject

        :param coreobject: Core object to retrieve art for
        :param CoreObjectType coreobjecttype: The CoreObjectType
        """
        if coreobject not in [self._queue.keys(), self._active_queue]:
            self._queue[coreobject] = coreobjecttype

        if self._timeout_id == 0:
            self._timeout_id = GLib.timeout_add(100, self._dispatch)

    def _dispatch(self) -> bool:
        if len(self._queue) == 0:
            self._timeout_id = 0
            return GLib.SOURCE_REMOVE

        if len(self._active_queue) > 0:
            return GLib.SOURCE_CONTINUE

        coreobject, coreobjecttype = self._queue.popitem()

        storeart = StoreArt()
        storeart.connect("finished", self._on_async_finished, coreobject)
        if coreobjecttype == CoreObjectType.ARTIST:
            self._coregrilo.get_artist_art(coreobject, storeart)
        elif coreobjecttype == CoreObjectType.ALBUM:
            self._coregrilo.get_album_art(coreobject, storeart)
        elif coreobjecttype == CoreObjectType.SONG:
            self._coregrilo.get_song_art(coreobject, storeart)

        self._active_queue.append(coreobject)

        return GLib.SOURCE_CONTINUE

    def _on_async_finished(
            self, storeart: StoreArt, coreobject: CoreObject) -> None:
        if coreobject in self._active_queue:
            self._active_queue.remove(coreobject)
