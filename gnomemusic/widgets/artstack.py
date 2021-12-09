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

from gi.repository import GObject, Gtk, Handy
if typing.TYPE_CHECKING:
    from cairo import ImageSurface


from gnomemusic.asyncqueue import AsyncQueue
from gnomemusic.artcache import ArtCache
from gnomemusic.defaulticon import DefaultIcon
from gnomemusic.utils import ArtSize
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

    _async_queue = AsyncQueue("ArtStack")

    def __init__(self, size: ArtSize = ArtSize.MEDIUM) -> None:
        """Initialize the ArtStack

        :param ArtSize size: The size of the art used for the cover
        """
        super().__init__()

        self._art_type = DefaultIcon.Type.ALBUM
        self._cache = ArtCache()
        self._coreobject: Optional[CoreObject] = None
        self._handler_id = 0
        self._size = size
        self._thumbnail_id = 0

        self._cover_a = Gtk.Image()
        self._cover_a.props.visible = True
        self._cover_b = Gtk.Image()
        self._cover_b.props.visible = True

        self.add_named(self._cover_a, "A")
        self.add_named(self._cover_b, "B")

        self.props.size = size

        self.connect("destroy", self._on_destroy)
        Handy.StyleManager.get_default().connect(
            "notify::dark", self._on_dark_changed)

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
    def art_type(self) -> DefaultIcon.Type:
        """Type of the stack cover

        :returns: The type of the default icon
        :rtype: DefaultIcon.Type
        """
        return self._art_type

    @art_type.setter  # type: ignore
    def art_type(self, value: DefaultIcon.Type) -> None:
        """Set the stack cover type

        :param DefaultIcon.Type value: The default icon type for the
            stack
        """
        self._art_type = value

        default_icon = DefaultIcon().get(
            self._art_type, self._size, self.props.scale_factor)

        self._swap_thumbnails(default_icon, False)

    @GObject.Property(type=object, default=None)
    def coreobject(self) -> Optional[CoreObject]:
        return self._coreobject

    @coreobject.setter  # type: ignore
    def coreobject(self, coreobject: CoreObject) -> None:
        if self._thumbnail_id != 0:
            self._coreobject.disconnect(self._thumbnail_id)
            self._thumbnail_id = 0

        self._coreobject = coreobject
        self._thumbnail_id = self._coreobject.connect(
            "notify::thumbnail", self._on_thumbnail_changed)

        if self._coreobject.props.thumbnail is not None:
            self._on_thumbnail_changed(self._coreobject, None)

    def _on_dark_changed(
            self, style_manager: Handy.StyleManager,
            pspec: GObject.ParamSpecBoolean) -> None:
        default_icon = DefaultIcon().get(
            self._art_type, self._size, self.props.scale_factor)

        if self._coreobject:
            if self._coreobject.props.thumbnail == "generic":
                self._swap_thumbnails(default_icon, False)
        else:
            self._swap_thumbnails(default_icon, False)

    def _on_thumbnail_changed(
            self, coreobject: CoreObject,
            uri: GObject.ParamSpecString) -> None:
        self._disconnect_cache()

        self._handler_id = self._cache.connect(
            "finished", self._on_cache_result)

        self._async_queue.queue(
            self._cache, coreobject, self._size, self.props.scale_factor)

    def _swap_thumbnails(self, surface: ImageSurface, animate: bool) -> None:
        if self.props.visible_child_name == "B":
            self._cover_a.props.surface = surface
            if animate:
                self.set_visible_child_full(
                    "A", Gtk.StackTransitionType.CROSSFADE)
            else:
                self.props.visible_child_name = "A"
        else:
            self._cover_b.props.surface = surface
            if animate:
                self.set_visible_child_full(
                    "B", Gtk.StackTransitionType.CROSSFADE)
            else:
                self.props.visible_child_name = "B"

    def _on_cache_result(self, cache: ArtCache, surface: ImageSurface) -> None:
        self._swap_thumbnails(surface, True)

    def _on_destroy(self, widget: ArtStack) -> None:
        # If the stack is destroyed while the art is updated, an error
        # can occur once the art is retrieved because the ArtStack does
        # not have children anymore.
        self._disconnect_cache()

    def _disconnect_cache(self) -> None:
        if self._handler_id != 0:
            self._cache.disconnect(self._handler_id)
            self._handler_id = 0
