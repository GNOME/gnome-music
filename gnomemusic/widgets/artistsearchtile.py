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

from gnomemusic.coreartist import CoreArtist
from gnomemusic.coverpaintable import CoverPaintable
from gnomemusic.utils import ArtSize, DefaultIconType
from gnomemusic.widgets.twolinetip import TwoLineTip


@Gtk.Template(resource_path="/org/gnome/Music/ui/ArtistSearchTile.ui")
class ArtistSearchTile(Gtk.FlowBoxChild):
    """Artist search tile

    Contains artist art and name
    """

    __gtype_name__ = "ArtistSearchTile"

    _artist_label = Gtk.Template.Child()
    _cover_image = Gtk.Template.Child()

    coreartist = GObject.Property(
        type=CoreArtist, default=None, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, coreartist):
        """Initialize the ArtistSearchTile

        :param CoreArtist coreartist: The coreartist to use
        """
        super().__init__()

        self.props.coreartist = coreartist

        self._cover_image.set_size_request(
            ArtSize.MEDIUM.width, ArtSize.MEDIUM.height)
        self._cover_image.props.pixel_size = ArtSize.MEDIUM.height
        self._cover_image.props.paintable = CoverPaintable(
            self, ArtSize.MEDIUM, DefaultIconType.ARTIST)

        self._cover_image.props.paintable.props.coreobject = coreartist

        self._tooltip = TwoLineTip()
        self._tooltip.props.subtitle_visible = False

        artist = self.props.coreartist.props.artist
        self._artist_label.props.label = artist
        self._tooltip.props.title = artist

    @Gtk.Template.Callback()
    def _on_tooltip_query(self, widget, x, y, kb, tooltip, data=None):
        tooltip.set_custom(self._tooltip)
        return True
