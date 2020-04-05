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

from gi.repository import Gdk, GObject, Gtk

from gnomemusic.albumartcache import Art
from gnomemusic.coreartist import CoreArtist
from gnomemusic.widgets.artstack import ArtStack  # noqa: F401
from gnomemusic.widgets.twolinetip import TwoLineTip


@Gtk.Template(resource_path="/org/gnome/Music/ui/ArtistSearchTile.ui")
class ArtistSearchTile(Gtk.FlowBoxChild):
    """Artist search tile

    Contains artist art and name
    """

    __gtype_name__ = "ArtistSearchTile"

    _artist_label = Gtk.Template.Child()
    _art_stack = Gtk.Template.Child()
    _check = Gtk.Template.Child()
    _events = Gtk.Template.Child()

    coreartist = GObject.Property(
        type=CoreArtist, default=None, flags=GObject.ParamFlags.READWRITE)
    selected = GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READWRITE)
    selection_mode = GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, coreartist):
        """Initialize the ArtistSearchTile

        :param CoreArtist coreartist: The coreartist to use
        """
        super().__init__()

        self.props.coreartist = coreartist

        self._art_stack.props.size = Art.Size.MEDIUM
        self._art_stack.props.coreobject = self.props.coreartist

        self._tooltip = TwoLineTip()
        self._tooltip.props.subtitle_visible = False

        artist = self.props.coreartist.props.artist
        self._artist_label.props.label = artist
        self._tooltip.props.title = artist

        self.bind_property(
            "selected", self._check, "active",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "selected", self.props.coreartist, "selected",
            GObject.BindingFlags.BIDIRECTIONAL)

        self.bind_property(
            "selection-mode", self._check, "visible",
            GObject.BindingFlags.BIDIRECTIONAL)

        self._events.add_events(Gdk.EventMask.TOUCH_MASK)

        self.show()

    @Gtk.Template.Callback()
    def _on_artist_event(self, evbox, event, data=None):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        if ((event.get_state() & modifiers) == Gdk.ModifierType.CONTROL_MASK
                and not self.props.selection_mode):
            self.props.selection_mode = True

        if self.props.selection_mode:
            self.props.selected = not self.props.selected

    @Gtk.Template.Callback()
    def _on_tooltip_query(self, widget, x, y, kb, tooltip, data=None):
        tooltip.set_custom(self._tooltip)
        return True
