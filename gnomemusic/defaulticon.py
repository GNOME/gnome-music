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

from enum import Enum
from math import pi
from typing import Dict, Tuple

import cairo
from gi.repository import Gtk, GObject

from gnomemusic.utils import ArtSize


def make_icon_frame(
        icon_surface, art_size=None, scale=1, default_icon=False,
        round_shape=False):
    """Create an Art frame, square or round.

    :param cairo.Surface icon_surface: The surface to use
    :param art_size: The size of the art
    :param int scale: The scale of the art
    :param bool default_icon: Indicates of this is a default icon
    :param bool round_shape: Square or round indicator

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
        ctx.arc(w - radius, radius, radius - 0.5, -90 * degrees, 0 * degrees)
        ctx.arc(
            w - radius, h - radius, radius - 0.5, 0 * degrees, 90 * degrees)
        ctx.arc(radius, h - radius, radius - 0.5, 90 * degrees, 180 * degrees)
        ctx.arc(radius, radius, radius - 0.5, 180 * degrees, 270 * degrees)

    if default_icon:
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
        ctx.set_source_rgba(0, 0, 0, 0.3)
        ctx.mask_surface(icon_surface, w / 3, h / 3)
        ctx.fill()
    else:
        matrix = cairo.Matrix()
        matrix.scale(icon_w / (w * scale), icon_h / (h * scale))
        ctx.set_source_surface(icon_surface, 0, 0)
        pattern = ctx.get_source()
        pattern.set_matrix(matrix)
        ctx.fill()

    return surface


class DefaultIcon(GObject.GObject):
    """Provides the symbolic fallback icons."""

    class Type(Enum):
        ALBUM = "folder-music-symbolic"
        ARTIST = "avatar-default-symbolic"

    _cache: Dict[
        Tuple["DefaultIcon.Type", ArtSize, int, bool], cairo.Surface] = {}

    _default_theme = Gtk.IconTheme.get_default()

    def __init__(self):
        super().__init__()

    def _make_default_icon(self, icon_type, art_size, scale, round_shape):
        icon_info = self._default_theme.lookup_icon_for_scale(
            icon_type.value, art_size.width / 3, scale, 0)
        icon = icon_info.load_surface()

        icon_surface = make_icon_frame(
            icon, art_size, scale, True, round_shape=round_shape)

        return icon_surface

    def get(self, icon_type, art_size, scale=1):
        """Returns the requested symbolic icon

        Returns a cairo surface of the requested symbolic icon in the
        given size and shape.

        :param enum icon_type: The DefaultIcon.Type of the icon
        :param enum art_size: The ArtSize requested
        :param int scale: The scale

        :return: The symbolic icon
        :rtype: cairo.Surface
        """
        if icon_type == DefaultIcon.Type.ALBUM:
            round_shape = False
        else:
            round_shape = True

        if (icon_type, art_size, scale) not in self._cache.keys():
            new_icon = self._make_default_icon(
                icon_type, art_size, scale, round_shape)
            self._cache[(icon_type, art_size, scale, round_shape)] = new_icon

        return self._cache[(icon_type, art_size, scale, round_shape)]
