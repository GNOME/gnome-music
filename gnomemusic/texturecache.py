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

from gi.repository import GLib, GObject, Gdk, Gio

from gnomemusic.musiclogger import MusicLogger
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

    # Music has two main cycling views (AlbumsView and ArtistsView),
    # both have around 200 cycling items each when fully used. For
    # the cache to be useful it needs to be larger than the given
    # numbers combined.
    _MAX_CACHE_SIZE = 800

    _cleanup_id = 0
    _log = MusicLogger()
    _memory_monitor = Gio.MemoryMonitor.dup_default()
    _size = _MAX_CACHE_SIZE
    _textures: Dict[str, Tuple[
        TextureCache.LoadingState, float, Optional[Gdk.Texture]]] = {}

    def __init__(self) -> None:
        """Initialize Texturecache
        """
        super().__init__()

        self._art_loader: MediaArtLoader
        self._art_loading_id = 0

        if TextureCache._cleanup_id == 0:
            TextureCache._cleanup_id = GLib.timeout_add_seconds(
                10, TextureCache._cache_cleanup)
            TextureCache._memory_monitor.connect(
                "low-memory-warning", TextureCache._low_memory_warning)

    def clear_pending_lookup_callback(self) -> None:
        """Disconnect ongoing lookup callback
        """
        if self._art_loading_id != 0:
            self._art_loader.disconnect(self._art_loading_id)
            self._art_loader.cancel()
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
        self._art_loader.start(uri)

    @classmethod
    def _low_memory_warning(
            cls, mm: Gio.MemoryMonitor,
            level: Gio.MemoryMonitorWarningLevel) -> None:
        if level < Gio.MemoryMonitorWarningLevel.LOW:
            TextureCache._size = TextureCache._MAX_CACHE_SIZE
        else:
            # List slicing with 0 gives an empty list in
            # _cache_cleanup.
            TextureCache._size = 1

    @classmethod
    def _cache_cleanup(cls) -> None:
        """Sorts the available cache entries by recency and evicts
        the oldest items to match the maximum cache size.
        """
        sorted_available = {
            k: (state, t, texture)
            for k, (state, t, texture) in sorted(
                TextureCache._textures.items(), key=lambda item: item[1][1])
            if state in [TextureCache.LoadingState.AVAILABLE]}

        sorted_available_l = len(sorted_available)
        if sorted_available_l < TextureCache._size:
            return GLib.SOURCE_CONTINUE

        keys_to_clear = list(sorted_available.keys())[:-TextureCache._size]
        for key in keys_to_clear:
            state, t, texture = TextureCache._textures[key]
            TextureCache._textures[key] = (
                TextureCache.LoadingState.CLEARED, t, None)

        keys_l = len(keys_to_clear)
        TextureCache._log.info(
            f"Cleared {keys_l} items, texture cache contains"
            f" {sorted_available_l-keys_l} available items.")  # noqa: E226

        return GLib.SOURCE_CONTINUE

    def _on_art_loading_finished(
            self, art_loader: MediaArtLoader, texture: Gdk.Texture,
            uri: str) -> None:
        if texture:
            state = TextureCache.LoadingState.AVAILABLE
        else:
            state = TextureCache.LoadingState.UNAVAILABLE

        TextureCache._textures[uri] = (state, time.time(), texture)

        self.emit("texture", texture)
