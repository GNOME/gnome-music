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

from gi.repository import GLib, GObject, Gtk

from gnomemusic.albumartcache import Art, DefaultIcon


class CoverStack(Gtk.Stack):
    """Provides a smooth transition between image states

    Uses a Gtk.Stack to provide an in-situ transition between an image
    state. Either between the 'loading' state versus the 'loaded' state
    or in between songs.
    """

    __gtype_name__ = 'CoverStack'

    _default_icon = DefaultIcon()

    def __init__(self, size=Art.Size.MEDIUM):
        """Initialize the CoverStack

        :param Art.Size size: The size of the art used for the cover
        """
        super().__init__()

        self._art = None
        self._handler_id = None
        self._size = None
        self._timeout = None

        self._loading_cover = Gtk.Image()
        self._cover_a = Gtk.Image()
        self._cover_b = Gtk.Image()

        self.add_named(self._loading_cover, "loading")
        self.add_named(self._cover_a, "A")
        self.add_named(self._cover_b, "B")

        self.props.size = size
        self.props.transition_type = Gtk.StackTransitionType.CROSSFADE
        self.props.visible_child_name = "loading"

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
        self._size = value

        icon = self._default_icon.get(
            DefaultIcon.Type.LOADING, self.props.size, self.props.scale_factor)
        self._loading_cover.props.surface = icon

    def update(self, coresong):
        """Update the stack with the given CoreSong

        Update the stack with the art retrieved from the given Coresong.
        :param CoreSong coresong: The CoreSong object
        """
        if self._handler_id and self._art:
            # Remove a possible dangling 'finished' callback if update
            # is called again, but it is still looking for the previous
            # art.
            self._art.disconnect(self._handler_id)
            # Set the loading state only after a delay to make between
            # song transitions smooth if loading time is negligible.
            self._timeout = GLib.timeout_add(100, self._set_loading_child)

        self._active_child = self.props.visible_child_name

        self._art = Art(self.props.size, coresong, self.props.scale_factor)
        self._handler_id = self._art.connect('finished', self._art_retrieved)
        self._art.lookup()

    def _set_loading_child(self):
        self.props.visible_child_name = "loading"
        self._active_child = self.props.visible_child_name
        self._timeout = None

        return GLib.SOURCE_REMOVE

    def _art_retrieved(self, klass):
        if self._timeout:
            GLib.source_remove(self._timeout)
            self._timeout = None

        if self._active_child == "B":
            self._cover_a.props.surface = klass.surface
            self.props.visible_child_name = "A"
        else:
            self._cover_b.props.surface = klass.surface
            self.props.visible_child_name = "B"

        self._active_child = self.props.visible_child_name
        self._art = None

    def _on_destroy(self, widget):
        # If the CoverStack is destroyed while the art is updated,
        # an error can be coccur once the art is retrieved because
        # the CoverStack does not have children anymore.
        if (self._art is not None
                and self._handler_id is not None):
            self._art.disconnect(self._handler_id)
            self._handler_id = None
