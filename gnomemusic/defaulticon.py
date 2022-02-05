# Copyright 2021 The GNOME Music developers
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

from typing import Dict, Tuple

from gi.repository import Adw, Gtk, GObject

from gnomemusic.coverpaintable import CoverPaintable
from gnomemusic.utils import ArtSize, DefaultIconType


class DefaultIcon(GObject.GObject):
    """Provides the symbolic fallback icons."""
    _cache: Dict[
        Tuple[DefaultIconType, ArtSize, int, bool], cairo.ImageSurface] = {}

    def __init__(self, widget: Gtk.Widget) -> None:
        """Initialize DefaultIcon

        :param Gtk.Widget widget: The widget of the icon
        """
        super().__init__()

        self._widget = widget

    def _make_default_icon(
            self, icon_type: DefaultIconType, art_size: ArtSize, scale: int,
            dark: bool) -> cairo.ImageSurface:
        paintable = CoverPaintable(art_size, self._widget, icon_type=icon_type)

        return paintable

    def get(self, icon_type: DefaultIconType,
            art_size: ArtSize) -> cairo.ImageSurface:
        """Returns the requested symbolic icon

        Returns a cairo surface of the requested symbolic icon in the
        given size and shape.

        :param DefaultIconType icon_type: The type of icon
        :param ArtSize art_size: The size requested

        :return: The symbolic icon
        :rtype: cairo.ImageSurface
        """
        dark = Adw.StyleManager.get_default().props.dark
        scale = self._widget.props.scale_factor

        if (icon_type, art_size, scale, dark) not in self._cache.keys():
            new_icon = self._make_default_icon(
                icon_type, art_size, scale, dark)
            self._cache[(icon_type, art_size, scale, dark)] = new_icon

        return self._cache[(icon_type, art_size, scale, dark)]
