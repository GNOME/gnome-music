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

from enum import Enum
import logging
from math import pi

import cairo
import gi
gi.require_version("MediaArt", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, GObject, Gtk, MediaArt


logger = logging.getLogger(__name__)


def _make_icon_frame(icon_surface, art_size=None, scale=1, default_icon=False):
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

    matrix = cairo.Matrix()

    line_width = 0.6
    ctx.new_sub_path()
    ctx.arc(w / 2, h / 2, (w / 2) - line_width, 0, 2 * pi)
    ctx.set_source_rgba(0, 0, 0, 0.7)
    ctx.set_line_width(line_width)
    ctx.stroke_preserve()

    if default_icon:
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
        ctx.set_source_rgba(0, 0, 0, 0.3)
        ctx.mask_surface(icon_surface, w / 3, h / 3)
        ctx.fill()
    else:
        matrix.scale(icon_w / (w * scale), icon_h / (h * scale))
        ctx.set_source_surface(icon_surface, 0, 0)

        pattern = ctx.get_source()
        pattern.set_matrix(matrix)
        ctx.fill()

    ctx.arc(w / 2, h / 2, w / 2, 0, 2 * pi)
    ctx.clip()

    return surface


class DefaultIcon(GObject.GObject):
    """Provides the symbolic fallback and loading icons."""

    class Type(Enum):
        LOADING = "content-loading-symbolic"
        ARTIST = "avatar-default-symbolic"

    _cache = {}
    _default_theme = Gtk.IconTheme.get_default()

    def __repr__(self):
        return "<DefaultIcon>"

    def __init__(self):
        super().__init__()

    def _make_default_icon(self, icon_type, art_size, scale):
        icon_info = self._default_theme.lookup_icon_for_scale(
            icon_type.value, art_size.width / 3, scale, 0)
        icon = icon_info.load_surface()

        icon_surface = _make_icon_frame(icon, art_size, scale, True)

        return icon_surface

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


class AlbumArt(GObject.GObject):

    def __init__(self, corealbum, coremodel):
        """Initialize the Album Art retrieval object

        :param CoreAlbum corealbum: The CoreALbum to use
        :param CoreModel coremodel: The CoreModel object
        """
        super().__init__()

        self._corealbum = corealbum
        self._artist = corealbum.props.artist
        self._title = corealbum.props.title

        if self._in_cache():
            return

        coremodel.props.grilo.get_album_art(corealbum)

    def _in_cache(self):
        success, thumb_file = MediaArt.get_file(
            self._artist, self._title, "album")

        # FIXME: Make async.
        if (not success
                or not thumb_file.query_exists()):
            return False

        self._corealbum.props.thumbnail = thumb_file.get_path()

        return True
