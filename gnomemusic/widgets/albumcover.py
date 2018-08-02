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

import gi
gi.require_version('Grl', '0.3')
from gi.repository import Gdk, GLib, GObject, Grl, Gtk

from gnomemusic import log
from gnomemusic import utils
from gnomemusic.albumartcache import Art
from gnomemusic.widgets.coverstack import CoverStack


@Gtk.Template(resource_path='/org/gnome/Music/AlbumCover.ui')
class AlbumCover(Gtk.FlowBoxChild):

    _nr_albums = 0

    __gtype_name__ = 'AlbumCover'

    _stack = Gtk.Template.Child()
    _check = Gtk.Template.Child()
    _title_label = Gtk.Template.Child()
    _artist_label = Gtk.Template.Child()
    _events = Gtk.Template.Child()

    selected = GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READWRITE)
    selection_mode = GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    def __repr__(self):
        return '<DiscBox>'

    @log
    def __init__(self, media):
        super().__init__()

        AlbumCover._nr_albums += 1

        self._media = media

        self._artist_label.props.label = utils.get_artist_name(media)
        self._title_label.props.label = utils.get_media_title(media)

        self.bind_property(
            'selected', self._check, 'active',
            GObject.BindingFlags.BIDIRECTIONAL |
            GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            'selection-mode', self._check, 'visible',
            GObject.BindingFlags.BIDIRECTIONAL)

        self._events.add_events(Gdk.EventMask.TOUCH_MASK)

        self._cover_stack = CoverStack(self._stack, Art.Size.MEDIUM)

        self.show()

        # FIXME: To work around slow updating of the albumsview,
        # load album covers with a fixed delay. This results in a
        # quick first show with a placeholder cover and then a
        # reasonably responsive view while loading the actual
        # covers.
        GLib.timeout_add(
            50 * self._nr_albums, self._cover_stack.update, media,
            priority=GLib.PRIORITY_LOW)

    @GObject.Property(type=Grl.Media, flags=GObject.ParamFlags.READABLE)
    def media(self):
        return self._media

    @Gtk.Template.Callback()
    @log
    def _on_album_event(self, evbox, event, data=None):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        if ((event.state & modifiers) == Gdk.ModifierType.CONTROL_MASK
                and not self.props.selection_mode):
            self.props.selection_mode = True

        if self.props.selection_mode:
            self._check.props.active = not self._check.props.active
