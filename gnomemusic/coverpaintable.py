# Copyright 2026 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from typing import Optional, Union
import typing

import gi
gi.require_versions({"Gdk": "4.0", "Gtk": "4.0", "Gsk": "4.0"})
from gi.repository import Adw, Gsk, Gtk, GObject, Graphene, Gdk

from gnomemusic.texturecache import TextureCache
from gnomemusic.utils import ArtSize, DefaultIconType
if typing.TYPE_CHECKING:
    from gnomemusic.corealbum import CoreAlbum
    from gnomemusic.coreartist import CoreArtist
    from gnomemusic.coresong import CoreSong

if typing.TYPE_CHECKING:
    CoreObject = Union[CoreAlbum, CoreArtist, CoreSong]


class CoverPaintable(GObject.GObject, Gdk.Paintable):
    """An album/artist cover or placeholder

    Provides the full looks. Rounded corners for albums and round for
    artists.
    """

    __gtype_name__ = "CoverPaintable"

    def __init__(
            self, widget: Gtk.Widget, art_size: ArtSize,
            icon_type: DefaultIconType) -> None:
        """Initiliaze CoverPaintable

        :param Gtk.Widget widget: Widget using the cover
        :param ArtSize art_size: Size of the cover
        :param DefaultIconType icon_type: Type of cover
        """
        super().__init__()

        self._art_size = art_size
        self._coreobject: Optional[CoreObject] = None
        self._icon_theme = Gtk.IconTheme.new().get_for_display(
            widget.get_display())
        self._icon_type = icon_type
        self._style_manager = Adw.StyleManager.get_default()
        self._texture = None
        self._texture_cache = TextureCache()
        self._texture_cache.connect_object("texture", self._on_texture_cache.__func__, self)
        self._thumbnail_id = 0
        self._widget = widget.weak_ref()

        self._style_manager.connect("notify::dark", self._on_dark_changed)

    def do_snapshot(self, snapshot: Gtk.Snapshot, w: float, h: float) -> None:
        if self._texture is not None:
            self._snapshot_texture(self._texture, snapshot, w, h)
        else:
            self._snapshot_fallback_icon(snapshot, w, h)

    def _snapshot_texture(
            self, texture: Gdk.Texture, snapshot: Gtk.Snapshot, w: float,
            h: float) -> None:
        w_s = w
        h_s = h
        ratio = texture.get_height() / texture.get_width()
        # Scale down the image according to the biggest axis
        if ratio > 1:
            w = w / ratio
        else:
            h = h * ratio

        scale_factor = self._widget().props.scale_factor

        snapshot.save()
        snapshot.scale(1.0 / scale_factor, 1.0 / scale_factor)

        rect = Graphene.Rect().init((w_s - w) / 2, (h_s - h) / 2, w, h)
        rect = rect.scale(scale_factor, scale_factor)
        rounded_rect = Gsk.RoundedRect()
        rounded_rect.init_from_rect(rect, self._radius() * scale_factor)
        snapshot.push_rounded_clip(rounded_rect)

        snapshot.append_scaled_texture(
            texture, Gsk.ScalingFilter.TRILINEAR, rect)

        snapshot.pop()
        snapshot.restore()

    def _snapshot_fallback_icon(
            self, snapshot: Gtk.Snapshot, w: float, h: float) -> None:
        rounded_rect = Gsk.RoundedRect()
        rounded_rect.init_from_rect(
            Graphene.Rect().init(0, 0, w, h), self._radius())
        snapshot.push_rounded_clip(rounded_rect)

        i_s = 1 / 3  # Icon scale
        icon_pt = self._icon_theme.lookup_icon(
            self._icon_type.value, None, w * i_s,
            self._widget().props.scale_factor, 0, 0)

        bg_color = Gdk.RGBA()
        bg_color.parse("rgba(95%, 95%, 95%, 1)")
        if self._style_manager.props.dark:
            bg_color.parse("rgba(30%, 30%, 30%, 1)")

        snapshot.append_color(bg_color, Graphene.Rect().init(0, 0, w, h))
        snapshot.translate(
            Graphene.Point().init(
                (w / 2) - (w * (i_s / 2)), (h / 2) - (h * (i_s / 2))))
        snapshot.push_opacity(0.7)
        icon_pt.snapshot(snapshot, w * i_s, h * i_s)
        snapshot.pop()

        snapshot.pop()

    def _radius(self) -> float:
        if self._icon_type == DefaultIconType.ARTIST:
            return 90.0
        elif self._art_size == ArtSize.SMALL:
            return 4.5
        else:
            return 9.0

    def _on_dark_changed(
            self, style_manager: Adw.StyleManager,
            pspec: GObject.ParamSpecBoolean) -> None:
        if self._texture is not None:
            return

        self.invalidate_contents()

    @GObject.Property(type=object, default=None)
    def coreobject(self) -> Optional[CoreObject]:
        """Get the current core object in use

        :returns: The corrent coreobject
        :rtype: Union[CoreAlbum, CoreArtist, CoreSong] or None
        """
        return self._coreobject

    @coreobject.setter  # type: ignore
    def coreobject(self, coreobject: CoreObject) -> None:
        """Update the coreobject used for CoverPaintable

        :param Union[CoreAlbum, CoreArtist, CoreSong] coreobject:
            The coreobject to set
        """
        if coreobject is self._coreobject:
            return

        self._texture_cache.clear_pending_lookup_callback()

        if self._texture:
            self._texture = None
            self.invalidate_contents()

        if self._thumbnail_id != 0:
            self._coreobject.disconnect(self._thumbnail_id)
            self._thumbnail_id = 0

        self._coreobject = coreobject
        self._thumbnail_id = self._coreobject.connect_object(
            "notify::thumbnail", self._on_thumbnail_changed.__func__, self)

        if self._coreobject.props.thumbnail is not None:
            self._on_thumbnail_changed(None)

    def _on_thumbnail_changed(
            self, uri: GObject.ParamSpecString) -> None:
        thumbnail_uri = self._coreobject.props.thumbnail

        if thumbnail_uri == "generic":
            self._texture = None
            self.invalidate_contents()
            return

        self._texture_cache.lookup(thumbnail_uri)

    def _on_texture_cache(
            self, texture: Gdk.Texture) -> None:
        if texture == self._texture:
            return

        self._texture = texture
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
