# Copyright 2019 The GNOME Music developers
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

from gnomemusic.albumartcache import Art
from gnomemusic.artcache import ArtCache
from gnomemusic.coreartist import CoreArtist


class ArtStack(Gtk.Stack):
    """Provides a smooth transition between image states

    Uses a Gtk.Stack to provide an in-situ transition between an image
    state. Between the 'loading' and 'default' art state and in between
    songs.
    """

    __gtype_name__ = "ArtStack"

    def __init__(self, size=Art.Size.MEDIUM):
        """Initialize the ArtStack

        :param Art.Size size: The size of the art used for the cover
        """
        super().__init__()

        self._cache = None
        self._handler_id = None
        self._size = None

        self._cover_a = Gtk.Image()
        self._cover_b = Gtk.Image()

        self.add_named(self._cover_a, "A")
        self.add_named(self._cover_b, "B")

        self.props.size = size
        self.props.transition_type = Gtk.StackTransitionType.CROSSFADE
        self.props.visible_child_name = "A"

        self.connect("destroy", self._on_destroy)

        self.show_all()

    @GObject.Property(type=object, flags=GObject.ParamFlags.READWRITE)
    def size(self):
        """Size of the cover

        :returns: The size used
        :rtype: Art.Size
        """
        return self._size

    @size.setter
    def size(self, value):
        """Set the cover size

        :param Art.Size value: The size to use for the cover
        """
        self._cover_a.set_size_request(value.width, value.height)
        self._size = value

    @GObject.Property(type=object, default=None)
    def coreobject(self):
        return self._coreobject

    @coreobject.setter
    def coreobject(self, coreobject):
        self._coreobject = coreobject

        self._coreobject.connect(
            "notify::thumbnail", self._on_thumbnail_changed)

        if self._coreobject.props.thumbnail is not None:
            self._on_thumbnail_changed(self._coreobject, None)

    def _on_thumbnail_changed(self, coreobject, uri):
        self._disconnect_cache()

        self._cache = ArtCache(self.props.size, self.props.scale_factor)
        self._handler_id = self._cache.connect("result", self._on_cache_result)

        self._cache.query(coreobject)

    def _on_cache_result(self, cache, surface):
        if self.props.visible_child_name == "B":
            self._cover_a.props.surface = surface
            self.props.visible_child_name = "A"
        else:
            self._cover_b.props.surface = surface
            self.props.visible_child_name = "B"

    def _on_destroy(self, widget):
        # If the stacm is destroyed while the art is updated, an error
        # can occur once the art is retrieved because the CoverStack
        # does not have children anymore.
        self._disconnect_cache()

    def _disconnect_cache(self):
        if (self._cache is not None
                and self._handler_id is not None):
            self._cache.disconnect(self._handler_id)
            self._handler_id = None
