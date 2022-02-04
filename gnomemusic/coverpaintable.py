import gi
gi.require_versions({"Gdk": "4.0", "Gtk": "4.0", "Gsk": "4.0"})
from gi.repository import Gsk, Gtk, GObject, Graphene, Gdk


class CoverPaintable(GObject.GObject, Gdk.Paintable):

    __gtype_name__ = "CoverPaintable"

    def __init__(self, art_size, texture=None):
        super().__init__()

        self._texture = texture
        self._art_size = art_size

    def do_snapshot(self, snapshot, w, h):
        rect = Graphene.Rect().init(0, 0, w, h)
        rounded_rect = Gsk.RoundedRect()
        rounded_rect.init_from_rect(rect, 9)
        snapshot.push_rounded_clip(rounded_rect)

        if self._texture is not None:
            snapshot.translate(Graphene.Point().init(w / 2, h / 2))
            rect = Graphene.Rect().init(-(w / 2), -(h / 2), w, h)
            snapshot.append_texture(self._texture, rect)

        else:
            snapshot.append_color(
                Gdk.RGBA(1, 1, 1, 1), Graphene.Rect().init(0, 0, w, h))
            snapshot.translate(
                Graphene.Point().init((w / 2) - (w / 6), (h / 2) - (h / 6)))

            theme = Gtk.IconTheme.new()
            icon_pt = theme.lookup_icon(
                "folder-music-symbolic", None, w / 3, 1, 0, 0)

            snapshot.push_opacity(0.7)
            icon_pt.snapshot(snapshot, w / 3, h / 3)
            snapshot.pop()

        snapshot.pop()

    def do_get_flags(self):
        return Gdk.PaintableFlags.SIZE | Gdk.PaintableFlags.CONTENTS

    def do_get_intrinsic_height(self):
        return self._art_size.height

    def do_get_intrinsic_width(self):
        return self._art_size.width
