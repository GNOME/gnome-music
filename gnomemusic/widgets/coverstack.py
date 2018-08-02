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

from enum import Enum

from gi.repository import GObject, Gtk

from gnomemusic import log
from gnomemusic.albumartcache import Art, DefaultIcon


class CoverStack(Gtk.Stack):
    """Provides a smooth transition between image states

    Uses a Gtk.Stack to provide an in-situ transition between an image
    state. Either between the 'loading' state versus the 'loaded' state
    or in between songs.
    """

    __gtype_name__ = 'CoverStack'

    __gsignals__ = {
        'updated': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    _default_icon = DefaultIcon()

    @log
    def __init__(self, size=Art.Size.MEDIUM):
        super().__init__()

        self._size = None
        self._handler_id = None

        self._loading_cover = Gtk.Image()
        self._cover_a = Gtk.Image()
        self._cover_b = Gtk.Image()

        self.add_named(self._loading_cover, "loading")
        self.add_named(self._cover_a, "A")
        self.add_named(self._cover_b, "B")

        self.props.size = size
        self.props.transition_type = Gtk.StackTransitionType.CROSSFADE
        self.props.visible_child_name = "loading"

        self.show_all()

    @GObject.Property(type=object, flags=GObject.ParamFlags.READWRITE)
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        self._size = value

        icon = self._default_icon.get(
            DefaultIcon.Type.LOADING, self.props.size, self.props.scale_factor)
        self._loading_cover.props.surface = icon

    @log
    def update(self, media):
        """Update the stack with the given media

        Update the stack with the art retrieved from the given media.
        :param Grl.Media media: The media object
        """
        self._active_child = self.props.visible_child_name

        art = Art(self.props.size, media, self.props.scale_factor)
        self._handler_id = art.connect('finished', self._art_retrieved)
        art.lookup()

    @log
    def _art_retrieved(self, klass):
        klass.disconnect(self._handler_id)
        if self._active_child == "B":
            self._cover_a.props.surface = klass.surface
            self.props.visible_child_name = "A"
        else:
            self._cover_b.props.surface  = klass.surface
            self.props.visible_child_name = "B"

        self.emit('updated')
