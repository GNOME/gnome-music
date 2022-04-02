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
from gi.repository import Adw, Gsk, Gtk, GObject, Graphene, Gdk

from gnomemusic.utils import ArtSize, DefaultIconType


class CoverPaintable(GObject.GObject, Gdk.Paintable):
    """An album/artist cover or placeholder

    Provides the full looks. Rounded corners for albums and round for
    artists.
    """

    __gtype_name__ = "CoverPaintable"

    def __init__(
            self, art_size: ArtSize, widget: Gtk.Widget,
            icon_type: DefaultIconType = DefaultIconType.ALBUM,
            texture: Gdk.Texture = None) -> None:
        """Initiliaze CoverPaintable

        :param ArtSize art_size: Size of the cover
        :param Gtk.Widget widget: Widget using the cover
        :param DefaultIconType icon_type: Type of cover
        :param Gdk.Texture texture: Texture to use or None for
            placeholder
        """
        super().__init__()

        self._art_size = art_size
        self._icon_theme = Gtk.IconTheme.new().get_for_display(
            widget.get_display())
        self._icon_type = icon_type
        self._style_manager = Adw.StyleManager.get_default()
        self._texture = texture
        self._widget = widget

        self._style_manager.connect("notify::dark", self._on_dark_changed)

    def do_snapshot(self, snapshot: Gtk.Snapshot, w: int, h: int) -> None:
        if self._icon_type == DefaultIconType.ARTIST:
            radius = 90.0
        elif self._art_size == ArtSize.SMALL:
            radius = 4.5
        else:
            radius = 9.0

        w_s = w
        h_s = h
        if self._texture is not None:
            ratio = self._texture.get_height() / self._texture.get_width()
            # Scale down the image according to the biggest axis
            if ratio > 1:
                w = int(w / ratio)
            else:
                h = int(h * ratio)

        rect = Graphene.Rect().init((w_s - w) / 2, (h_s - h) / 2, w, h)
        rounded_rect = Gsk.RoundedRect()
        rounded_rect.init_from_rect(rect, radius)
        snapshot.push_rounded_clip(rounded_rect)

        if self._texture is not None:
            snapshot.append_texture(self._texture, rect)
        else:
            i_s = 1 / 3  # Icon scale
            icon_pt = self._icon_theme.lookup_icon(
                self._icon_type.value, None, w * i_s,
                self._widget.props.scale_factor, 0, 0)

            bg_color = Gdk.RGBA(1, 1, 1, 1)
            if self._style_manager.props.dark:
                bg_color = Gdk.RGBA(0.3, 0.3, 0.3, 1)

            snapshot.append_color(bg_color, Graphene.Rect().init(0, 0, w, h))
            snapshot.translate(
                Graphene.Point().init(
                    (w / 2) - (w * (i_s / 2)), (h / 2) - (h * (i_s / 2))))
            snapshot.push_opacity(0.7)
            icon_pt.snapshot(snapshot, w * i_s, h * i_s)
            snapshot.pop()

        snapshot.pop()

    def _on_dark_changed(
            self, style_manager: Adw.StyleManager,
            pspec: GObject.ParamSpecBoolean) -> None:
        if self._texture is not None:
            return

        self.invalidate_contents()

    @GObject.Property(type=object, flags=GObject.ParamFlags.READWRITE)
    def icon_type(self) -> DefaultIconType:
        """Icon type of the cover

        :returns: The type of the default icon
        :rtype: DefaultIconType
        """
        return self._icon_type

    @icon_type.setter  # type: ignore
    def icon_type(self, value: DefaultIconType) -> None:
        """Set the cover icon type

        :param DefaultIconType value: The default icon type for the
            cover
        """
        self._icon_type = value

        self.invalidate_contents()

    def do_get_flags(self) -> Gdk.PaintableFlags:
        return Gdk.PaintableFlags.SIZE

    def do_get_intrinsic_height(self) -> int:
        return self._art_size.height

    def do_get_intrinsic_width(self) -> int:
        return self._art_size.width
