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

from math import pi
from typing import Dict, Tuple

import cairo
from gi.repository import Adw, Gtk, GObject, Gdk

from gnomemusic.coverpaintable import CoverPaintable
from gnomemusic.utils import ArtSize, DefaultIconType


def make_icon_frame(
        icon_surface, art_size=None, scale=1, default_icon=False,
        round_shape=False, dark=False):
    """Create an Art frame, square or round.

    :param cairo.Surface icon_surface: The surface to use
    :param art_size: The size of the art
    :param int scale: The scale of the art
    :param bool default_icon: Indicates of this is a default icon
    :param bool round_shape: Square or round indicator
    :param bool dark: Theme dark mode

    :return: The framed surface
    :rtype: cairo.Surface
    """
    degrees = pi / 180
    if art_size == ArtSize.SMALL:
        radius = 4.5
    else:
        radius = 9
    icon_w = icon_surface.get_width()
    icon_h = icon_surface.get_height()
    ratio = icon_h / icon_w

    # Scale down the image according to the biggest axis
    if ratio > 1:
        w = int(art_size.width / ratio)
        h = art_size.height
    else:
        w = art_size.width
        h = int(art_size.height * ratio)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w * scale, h * scale)
    surface.set_device_scale(scale, scale)
    ctx = cairo.Context(surface)

    if round_shape:
        ctx.arc(w / 2, h / 2, w / 2, 0, 2 * pi)
    else:
        ctx.arc(w - radius, radius, radius, -90 * degrees, 0 * degrees)
        ctx.arc(
            w - radius, h - radius, radius, 0 * degrees, 90 * degrees)
        ctx.arc(radius, h - radius, radius, 90 * degrees, 180 * degrees)
        ctx.arc(radius, radius, radius, 180 * degrees, 270 * degrees)

    if dark:
        fill_color = Gdk.RGBA(0.28, 0.28, 0.28, 1.0)
        icon_color = Gdk.RGBA(1.0, 1.0, 1.0, 0.5)
    else:
        fill_color = Gdk.RGBA(1.0, 1.0, 1.0, 1.0)
        icon_color = Gdk.RGBA(0.0, 0.0, 0.0, 0.3)

    if default_icon:
        ctx.set_source_rgb(fill_color.red, fill_color.green, fill_color.blue)
        ctx.fill()
        ctx.set_source_rgba(
            icon_color.red, icon_color.green, icon_color.blue,
            icon_color.alpha)
        ctx.mask_surface(icon_surface, w / 3, h / 3)
        ctx.fill()
    else:
        ctx.scale((w * scale) / icon_w, (h * scale) / icon_h)
        ctx.set_source_surface(icon_surface, 0, 0)
        ctx.fill()

    return surface


class DefaultIcon(GObject.GObject):
    """Provides the symbolic fallback icons."""
    _cache: Dict[
        Tuple[DefaultIconType, ArtSize, int, bool], cairo.ImageSurface] = {}

    _default_theme = Gtk.IconTheme.new()

    def __init__(self, widget: Gtk.Widget) -> None:
        """Initialize DefaultIcon

        :param Gtk.Widget widget: The widget of the icon
        """
        super().__init__()

        self._widget = widget

    def _make_default_icon(
            self, icon_type: DefaultIconType, art_size: ArtSize, scale: int,
            dark: bool) -> cairo.ImageSurface:
        # icon_info = self._default_theme.lookup_icon(
        #     icon_type.value, art_size.width / 3, scale, 0, 0)
        # icon = icon_info.load_surface()

        # round_shape = icon_type == DefaultIconType.ARTIST
        # icon_surface = make_icon_frame(
        #     icon, art_size, scale, True, round_shape, dark)
        paintable = CoverPaintable(art_size)

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
