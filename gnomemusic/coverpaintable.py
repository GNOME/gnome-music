import gi
gi.require_versions({"Gdk": "4.0", "Gtk": "4.0"})
# from gi.repository import Gsk, Gtk, GObject, Graphene, Gdk
from gi.repository import Gtk, GObject, Graphene, Gdk


class CoverPaintable(GObject.GObject, Gdk.Paintable):

    __gtype_name__ = "CoverPaintable"

    def __init__(self, art_size, texture=None):
        super().__init__()

        self._texture = texture
        self._art_size = art_size

    def do_snapshot(self, snapshot, width, height):
        w = width
        h = height

        if self._texture is not None:
            snapshot.translate(Graphene.Point().init(width / 2, height / 2))

            rect = Graphene.Rect().init(-(w / 2), -(h / 2), w, h)
            rect2 = Graphene.Rect().init(-50, -50, 100, 100)

            # Anything Gsk related seems to be failing, no rounded
            # clips for now. Related: pygobject#471
            #
            # gskrr = Gsk.RoundedRect().init_from_rect(rect2, 10)
            # snapshot.push_rounded_clip(gskrr)

            snapshot.push_clip(rect2)
            snapshot.append_texture(self._texture, rect)
            snapshot.pop()
        else:
            theme = Gtk.IconTheme.new()
            icon_pt = theme.lookup_icon(
                "folder-music-symbolic", None, w, 1, 0, 0)
            icon_pt.snapshot(snapshot, w, h)

    def do_get_flags(self):
        return Gdk.PaintableFlags.SIZE | Gdk.PaintableFlags.CONTENTS

    def do_get_intrinsic_height(self):
        return self._art_size.height

    def do_get_intrinsic_width(self):
        return self._art_size.width
