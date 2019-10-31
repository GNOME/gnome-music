# Copyright 2018 The GNOME Music Developers
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

from gi.repository import GObject, Gtk

from gnomemusic import log


class CellRendererStar(Gtk.CellRendererPixbuf):
    """Starwidget cellrenderer implementation"""

    __gsignals__ = {
        'clicked': (GObject.SignalFlags.RUN_LAST, None, (str,))
    }

    def __repr__(self):
        return '<CellRendererStar>'

    def __init__(self):
        super().__init__()

        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE
        self.props.xpad = 32

        # _, width, height = Gtk.IconSize.lookup(Gtk.IconSize.SMALL_TOOLBAR)

        self._icon_width = 24
        self._icon_height = 24

        self._show_star = 0

    def do_render(self, ctx, widget, bg_area, cell_area, flags):
        style_ctx = widget.get_style_context()
        style_ctx.save()
        style_ctx.add_class('star')

        if self.props.show_star == 1:
            style_ctx.set_state(Gtk.StateFlags.SELECTED)
        else:
            style_ctx.set_state(Gtk.StateFlags.NORMAL)

        y = cell_area.y + ((cell_area.height - self._icon_height) / 2)
        x = cell_area.x + ((cell_area.width - self._icon_width) / 2)

        Gtk.render_background(
            style_ctx, ctx, x, y, self._icon_width, self._icon_height)

        style_ctx.restore()

    def do_get_preferred_width(self, widget):
        width = self._icon_width + self.props.xpad * 2

        return (width, width)

    def do_get_preferred_height(self, widget):
        height = self._icon_height + self.props.ypad * 2

        return (height, height)

    def do_activate(self, event, widget, path, bg_area, cell_area, flags):
        """Activate event for the cellrenderer"""
        self.emit('clicked', path)

    @GObject.Property(type=int, default=0, minimum=0, maximum=2)
    def show_star(self):
        return self._show_star

    @show_star.setter
    def show_star(self, value):
        """Set the show-star value

        :param int value: Possible values: 0 = not selected,
        1 = selected, 2 = do not show.
        """
        self._show_star = value

        if value == 2:
            self.props.visible = False
        else:
            self.props.visible = True


class StarHandlerWidget(object):
    """Handles the treeview column for favorites (stars)."""

    def __repr__(self):
        return '<StarHandlerWidget>'

    @log
    def __init__(self, parent, star_index):
        """Initialize.

        :param parent: The parent widget
        :param int star_index: The column of the stars
        """
        self.star_renderer_click = False
        self._star_index = star_index
        self._parent = parent

    @log
    def add_star_renderers(self, col):
        """Adds the star renderer column

        :param col: GtkTreeViewColumn to use
        """
        star_renderer = CellRendererStar()
        star_renderer.connect("clicked", self._on_star_toggled)

        col.pack_start(star_renderer, False)
        col.add_attribute(star_renderer, 'show_star', self._star_index)

    @log
    def _on_star_toggled(self, widget, path):
        """Called if a star is clicked"""
        model = self._parent._view.props.model
        try:
            _iter = model.get_iter(path)
        except ValueError:
            return

        try:
            if model[_iter][self._star_index] == 2:
                return
        except AttributeError:
            return

        new_value = not model[_iter][self._star_index]
        model[_iter][self._star_index] = new_value
        coresong = model[_iter][7]
        coresong.props.favorite = new_value

        # Use this flag to ignore the upcoming _on_item_activated call
        self.star_renderer_click = True
