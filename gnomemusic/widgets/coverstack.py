# Copyright © 2018 The GNOME Music developers
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

from gnomemusic import log
from gnomemusic.albumartcache import Art, DefaultIcon


class CoverStack(GObject.GObject):
    """Provides a smooth transition between image states

    Uses a Gtk.Stack to provide an in-situ transition between an image
    state. Either between the 'loading' state versus the 'loaded' state
    or in between songs.
    """

    __gsignals__ = {
        'updated': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    _default_icon = DefaultIcon()

    @log
    def __init__(self, stack, size):
        super().__init__()

        self._size = size
        self._stack = stack
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._scale = self._stack.get_scale_factor()
        self._handler_id = None

        self._loading_icon = self._default_icon.get(
            DefaultIcon.Type.LOADING, self._size, self._scale)

        self._loading_cover = Gtk.Image.new_from_surface(self._loading_icon)

        self._cover_a = Gtk.Image()
        self._cover_b = Gtk.Image()

        self._stack.add_named(self._loading_cover, "loading")
        self._stack.add_named(self._cover_a, "A")
        self._stack.add_named(self._cover_b, "B")

        self._stack.set_visible_child_name("loading")
        self._stack.show_all()

    @log
    def update(self, media):
        """Update the stack with the given media

        Update the stack with the art retrieved from the given media.
        :param Grl.Media media: The media object
        """
        self._active_child = self._stack.get_visible_child_name()

        art = Art(self._size, media, self._scale)
        self._handler_id = art.connect('finished', self._art_retrieved)
        art.lookup()

    @log
    def _art_retrieved(self, klass):
        klass.disconnect(self._handler_id)
        if self._active_child == "B":
            self._cover_a.set_from_surface(klass.surface)
            self._stack.set_visible_child_name("A")
        else:
            self._cover_b.set_from_surface(klass.surface)
            self._stack.set_visible_child_name("B")

        self.emit('updated')
