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

from enum import Enum
import logging
from math import pi

import cairo
import gi
gi.require_version('MediaArt', '2.0')
from gi.repository import GObject, Gtk, MediaArt

from gnomemusic import log


logger = logging.getLogger(__name__)


@log
def lookup_art_file_from_cache(coresong):
    """Lookup MediaArt cache art of an album or song.

    :param CoreSong coresong: song or album
    :returns: a cache file
    :rtype: Gio.File
    """
    try:
        album = coresong.props.album
    except AttributeError:
        album = coresong.props.title
    artist = coresong.props.artist

    success, thumb_file = MediaArt.get_file(artist, album, "album")
    if (not success
            or not thumb_file.query_exists()):
        return None

    return thumb_file


@log
def _make_icon_frame(icon_surface, art_size=None, scale=1, default_icon=False):
    border = 3
    degrees = pi / 180
    radius = 3

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

    # draw outline
    ctx.new_sub_path()
    ctx.arc(w - radius, radius, radius - 0.5, -90 * degrees, 0 * degrees)
    ctx.arc(w - radius, h - radius, radius - 0.5, 0 * degrees, 90 * degrees)
    ctx.arc(radius, h - radius, radius - 0.5, 90 * degrees, 180 * degrees)
    ctx.arc(radius, radius, radius - 0.5, 180 * degrees, 270 * degrees)
    ctx.close_path()
    ctx.set_line_width(0.6)
    ctx.set_source_rgba(0, 0, 0, 0.7)
    ctx.stroke_preserve()

    matrix = cairo.Matrix()

    if default_icon:
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
        ctx.set_source_rgba(0, 0, 0, 0.3)
        ctx.mask_surface(icon_surface, w / 3, h / 3)
        ctx.fill()
    else:
        matrix.scale(
            icon_w / ((w - border * 2) * scale),
            icon_h / ((h - border * 2) * scale))
        matrix.translate(-border, -border)
        ctx.set_source_surface(icon_surface, 0, 0)

        pattern = ctx.get_source()
        pattern.set_matrix(matrix)
        ctx.fill()

    ctx.rectangle(border, border, w - border * 2, h - border * 2)
    ctx.clip()

    return surface


class DefaultIcon(GObject.GObject):
    """Provides the symbolic fallback and loading icons."""

    class Type(Enum):
        LOADING = 'content-loading-symbolic'
        MUSIC = 'folder-music-symbolic'

    _cache = {}
    _default_theme = Gtk.IconTheme.get_default()

    def __repr__(self):
        return '<DefaultIcon>'

    @log
    def __init__(self):
        super().__init__()

    @log
    def _make_default_icon(self, icon_type, art_size, scale):
        icon_info = self._default_theme.lookup_icon_for_scale(
            icon_type.value, art_size.width / 3, scale, 0)
        icon = icon_info.load_surface()

        icon_surface = _make_icon_frame(icon, art_size, scale, True)

        return icon_surface

    @log
    def get(self, icon_type, art_size, scale=1):
        """Returns the requested symbolic icon

        Returns a cairo surface of the requested symbolic icon in the
        given size.

        :param enum icon_type: The DefaultIcon.Type of the icon
        :param enum art_size: The Art.Size requested

        :return: The symbolic icon
        :rtype: cairo.Surface
        """
        if (icon_type, art_size, scale) not in self._cache.keys():
            new_icon = self._make_default_icon(icon_type, art_size, scale)
            self._cache[(icon_type, art_size, scale)] = new_icon

        return self._cache[(icon_type, art_size, scale)]


class Art(GObject.GObject):

    class Size(Enum):
        """Enum for icon sizes"""
        XSMALL = (34, 34)
        SMALL = (48, 48)
        MEDIUM = (128, 128)
        LARGE = (256, 256)
        XLARGE = (512, 512)

        def __init__(self, width, height):
            """Intialize width and height"""
            self.width = width
            self.height = height
