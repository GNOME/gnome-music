# Copyright 2022 The GNOME Music developers
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

import gi
gi.require_versions({"Gdk": "4.0", "Gtk": "4.0", "Gsk": "4.0"})
from gi.repository import Rsvg, Gio, Gsk, Gtk, GObject, Graphene, Gdk

from gnomemusic.utils import ArtSize, DefaultIconType


class SVGPaintable(GObject.GObject, Gdk.Paintable):
    """An album/artist cover or placeholder

    Provides the full looks. Rounded corners for albums and round for
    artists.
    """

    __gtype_name__ = "SVGPaintable"

    def __init__(self, resource) -> None:
        """Initiliaze CoverPaintable

        :param ArtSize art_size: Size of the cover
        :param Gtk.Widget widget: Widget using the cover
        :param DefaultIconType icon_type: Type of cover
        :param Gdk.Texture texture: Texture to use or None for
            placeholder
        :param bool dark: Dark mode
        """
        super().__init__()

        self._resource = resource

        io_stream = Gio.resources_open_stream(
            "/org/gnome/Music/icons/welcome-music.svg", Gio.ResourceLookupFlags.NONE)
        print(io_stream)

        self._handle = Rsvg.Handle.new_from_stream_sync(io_stream, None, 0, None)
        self._handle.set_dpi(90)

    def do_snapshot(self, snapshot: Gtk.Snapshot, w: int, h: int) -> None:
        print("snapshot", w, h)
        rsvg_rect = Rsvg.Rectangle()
        rsvg_rect.x = 0
        rsvg_rect.y = 0
        rsvg_rect.width = w
        rsvg_rect.height = h
        print("rsvg", rsvg_rect.width)

        grph_rect = Graphene.Rect().init(0, 0, w, h)
        cr = snapshot.append_cairo(grph_rect)
        # snapshot.append_color(Gdk.RGBA(0.5, 0.5, 0.5, 0.5), grph_rect)
        try:
            print(rsvg_rect)
            self._handle.render_document(cr, rsvg_rect)
            # self._handle.render_cairo(cr)
        except:
            print("error")

    def do_get_flags(self) -> Gdk.PaintableFlags:
        return Gdk.PaintableFlags.CONTENTS

    def do_get_intrinsic_height(self) -> int:
        _, _, h = self._handle.get_intrinsic_size_in_pixels()

        return h

    def do_get_intrinsic_width(self) -> int:
        print(self._handle.get_intrinsic_size_in_pixels())
        _, w, _ = self._handle.get_intrinsic_size_in_pixels()

        return w
