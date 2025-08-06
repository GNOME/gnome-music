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

from __future__ import annotations
from typing import Optional

from gi.repository import GObject, Gtk

from gnomemusic.coreartist import CoreArtist
from gnomemusic.coverpaintable import CoverPaintable
from gnomemusic.utils import ArtSize, DefaultIconType


@Gtk.Template(resource_path='/org/gnome/Music/ui/ArtistTile.ui')
class ArtistTile(Gtk.Box):
    """Row for sidebars

    Contains a label and an optional checkbox.
    """

    __gtype_name__ = 'ArtistTile'

    __gsignals__ = {
        "clicked": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    _cover_image = Gtk.Template.Child()
    _label = Gtk.Template.Child()

    text = GObject.Property(type=str, default='')

    def __init__(self) -> None:
        """Initialise ArtistTile"""
        super().__init__()

        self._coreartist: Optional[CoreArtist] = None

        self._cover_image.set_size_request(
            ArtSize.XSMALL.width, ArtSize.XSMALL.height)
        self._cover_image.props.pixel_size = ArtSize.XSMALL.height
        self._cover_image.props.paintable = CoverPaintable(
            self, ArtSize.XSMALL, DefaultIconType.ARTIST)

        self.bind_property('text', self._label, 'label')
        self.bind_property('text', self._label, 'tooltip-text')

        ctrl = Gtk.GestureClick()
        ctrl.connect("pressed", self._on_button_pressed)
        self.add_controller(ctrl)

    def _on_button_pressed(
            self, gesture: Gtk.GestureClick, n_press: int, x: float,
            y: float) -> None:
        self.emit("clicked")

    @GObject.Property(
        type=CoreArtist, flags=GObject.ParamFlags.READWRITE, default=None)
    def coreartist(self) -> CoreArtist:
        """CoreArtist to use for ArtistTile

        :returns: The artist object
        :rtype: CoreArtist
        """
        return self._coreartist

    @coreartist.setter  # type: ignore
    def coreartist(self, coreartist: CoreArtist) -> None:
        """CoreArtist setter

        :param CoreArtist coreartist: The coreartist to use
        """
        self._coreartist = coreartist

        self._cover_image.props.paintable.props.coreobject = coreartist
        self.props.text = coreartist.props.artist
