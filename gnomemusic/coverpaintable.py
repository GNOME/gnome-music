from math import pi

import gi
gi.require_versions({"Gdk": "4.0", "Gtk": "4.0"})
from gi.repository import Gtk, GObject, Graphene, Gdk

# from gnomemusic.albumartcache import Art


class CoverPaintable(GObject.GObject, Gdk.Paintable):

    __gtype_name__ = "CoverPaintable"

    def __init__(self, art_size):
        super().__init__()

        self._art_size = art_size
        print("CoverPaintable")

    def do_snapshot(self, snapshot, width, height):
        width = self._art_size.width
        height = self._art_size.height
        w = width
        h = height

        border = 3
        degrees = pi / 180
        radius = 3

        theme = Gtk.IconTheme.get_default()

        # pixbuf = theme.load_icon("content-loading-symbolic", w, 0)
        icon_pt = theme.lookup_icon(
            "content-loading-symbolic", None, w, 1, 0, 0)
        texture = Gdk.Texture.new_from_file(icon_pt.get_file())
        rect = Graphene.Rect().init(0, 0, width, height)
        snapshot.append_texture(texture, rect)

        size = min(width, height)

        cr = snapshot.append_cairo(Graphene.Rect().init(
            (width - size) / 2.0, (height - size) / 2.0, size, size))

        # draw outline
        cr.new_sub_path()
        cr.arc(w - radius, radius, radius - 0.5, -90 * degrees, 0 * degrees)
        cr.arc(w - radius, h - radius, radius - 0.5, 0 * degrees, 90 * degrees)
        cr.arc(radius, h - radius, radius - 0.5, 90 * degrees, 180 * degrees)
        cr.arc(radius, radius, radius - 0.5, 180 * degrees, 270 * degrees)
        cr.close_path()
        cr.set_line_width(0.6)
        cr.set_source_rgba(0, 0, 0, 0.7)
        cr.stroke_preserve()

        cr.set_source_rgb(1, 1, 1)
        cr.fill()
        cr.set_source_rgba(0, 0, 0, 0.3)
        # ctx.mask_surface(icon_surface, w / 3, h / 3)
        cr.fill()
        # Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
        color = Gdk.RGBA(red=0.9, green=0.75, blue=0.75, alpha=.5)
        color.red = 0.9
        color.alpha = 1.0
        rect = Graphene.Rect().init(0, 0, width, height)

        # pixbuf = theme.load_icon("content-loading-symbolic", w,# 0)
        icon_pt = theme.lookup_icon(
            "content-loading-symbolic", None, w, 1, 0, 0)
        texture = Gdk.Texture.new_from_file(icon_pt.get_file())
        rect = Graphene.Rect().init(
            0 + border, 0 + border, width - border, height - border)
        snapshot.append_texture(texture, rect)
        # snapshot.append_color(color, rect)

        # size = min(width, height)

        # cr = snapshot.append_cairo(Graphene.Rect().init(
        #     (width - size) / 2.0, (height - size) / 2.0, size, size))

        # cr.translate(width / 2.0, height / 2.0)
        # cr.scale(size, size)
        # cr.rotate(0.0)

        # PI = 3.14159
        # cr.arc(0, 0, 0.1, -PI, PI)
        # cr.fill()

        # cr.set_line_width(0.3)
        # cr.set_dash([0.3 * PI / 3], 1.0)
        # cr.arc(0, 0, 0.3, -PI, PI)
        # cr.stroke()

    def do_get_flags(self):
        return Gdk.PaintableFlags.SIZE | Gdk.PaintableFlags.CONTENTS

    def do_get_intrinsic_height(self):
        return self._art_size.height

    def do_get_intrinsic_width(self):
        return self._art_size.width
