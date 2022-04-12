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
from enum import IntEnum
from typing import Dict, Optional, Tuple, Union
import time
import typing

from gi.repository import GObject, Gdk

from gnomemusic.asyncqueue import AsyncQueue
from gnomemusic.mediaartloader import MediaArtLoader
if typing.TYPE_CHECKING:
    from gnomemusic.corealbum import CoreAlbum
    from gnomemusic.coreartist import CoreArtist
    from gnomemusic.coresong import CoreSong

if typing.TYPE_CHECKING:
    CoreObject = Union[CoreAlbum, CoreArtist, CoreSong]


class TextureCache(GObject.GObject):
    """Retrieval and cache for artwork textures
    """

    class LoadingState(IntEnum):
        """The loading status of the URI

        AVAILABLE: The texture is currently cached
        UNAVAILABLE: No texture is available for the URI
        CLEARED: The texture was available, has been cleared and
            should be available on lookup
        """
        AVAILABLE = 0
        UNAVAILABLE = 1
        CLEARED = 2

    __gtype_name__ = "TextureCache"

    __gsignals__ = {
        "texture": (GObject.SignalFlags.RUN_FIRST, None, (object, ))
    }

    _async_queue = AsyncQueue("TextureCache")

    _textures: Dict[str, Tuple[
        TextureCache.LoadingState, float, Optional[Gdk.Texture]]] = {}

    def __init__(self) -> None:
        """Initialize Texturecache
        """
        super().__init__()

        self._art_loader: MediaArtLoader
        self._art_loading_id = 0

    def clear_pending_lookup_callback(self) -> None:
        """Disconnect ongoing lookup callback
        """
        if self._art_loading_id != 0:
            self._art_loader.disconnect(self._art_loading_id)
            self._art_loading_id = 0

    def lookup(self, uri: str) -> None:
        """Look up a texture for the given MediaArt uri

        :param str uri: The MediaArt uri
        """
        self.clear_pending_lookup_callback()

        if uri in TextureCache._textures.keys():
            state, _, texture = TextureCache._textures[uri]
            if state in [
                    TextureCache.LoadingState.AVAILABLE,
                    TextureCache.LoadingState.UNAVAILABLE]:
                self.emit("texture", texture)
                TextureCache._textures[uri] = (state, time.time(), texture)
                return

        self._art_loader = MediaArtLoader()
        self._art_loading_id = self._art_loader.connect(
            "finished", self._on_art_loading_finished, uri)
        self._async_queue.queue(self._art_loader, uri)

    def _on_art_loading_finished(
            self, art_loader: MediaArtLoader, texture: Gdk.Texture,
            uri: str) -> None:
        if texture:
            state = TextureCache.LoadingState.AVAILABLE
        else:
            state = TextureCache.LoadingState.UNAVAILABLE

        TextureCache._textures[uri] = (state, time.time(), texture)

        self.emit("texture", texture)
