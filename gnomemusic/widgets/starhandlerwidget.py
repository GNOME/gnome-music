# Copyright (c) 2016 The GNOME Music Developers
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

from gi.repository import Gdk, GObject, Gtk

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists, StaticPlaylists

playlists = Playlists.get_default()


class CellRendererClickablePixbuf(Gtk.CellRendererPixbuf):
    """Starwidget cellrenderer implementation"""

    __gsignals__ = {
        'clicked': (GObject.SignalFlags.RUN_LAST,
                    GObject.TYPE_NONE,
                    (GObject.TYPE_STRING,))
    }

    __gproperties__ = {
        'show_star': (GObject.TYPE_INT,
                      'Show star',
                      'show star',
                      0,
                      2,
                      1,
                      GObject.ParamFlags.READWRITE)
    }

    star_icon = 'starred-symbolic'
    non_star_icon = 'non-starred-symbolic'

    def __repr__(self):
        return '<CellRendererClickablePixbuf>'

    def __init__(self):
        super().__init__()

        self.set_property('mode', Gtk.CellRendererMode.ACTIVATABLE)
        self.set_property('xpad', 32)
        self.set_property('icon_name', '')

        self._show_star = 0

    def do_activate(self, event, widget, path, background_area, cell_area,
                    flags):
        """Activate event for the cellrenderer"""
        self._show_star = 0
        self.emit('clicked', path)

    def do_get_property(self, property):
        """PyGI property getters"""
        if property.name == 'show-star':
            return self._show_star

    def do_set_property(self, property, value):
        """PyGI property setters"""
        if property.name == 'show-star':
            if self._show_star == 1:
                self.set_property('icon_name', self.star_icon)
            elif self._show_star == 0:
                self.set_property('icon_name', self.non_star_icon)
            else:
                self.set_property('icon_name', '')
            self._show_star = value


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
    def add_star_renderers(self, list_widget, cols, hidden=False):
        """Adds the star renderer column

        :param list_widget: The widget to add the favorites column
        :param cols: List of the widgets GtkTreeViewColumns
        :param hidden: Visible state of the column
        """
        star_renderer = CellRendererClickablePixbuf()
        star_renderer.connect("clicked", self._on_star_toggled)
        list_widget.add_renderer(star_renderer, lambda *args: None, None)

        cols[0].clear_attributes(star_renderer)
        cols[0].add_attribute(star_renderer, 'show_star', self._star_index)

    @log
    def _on_star_toggled(self, widget, path):
        """Called if a star is clicked"""
        try:
            _iter = self._parent.model.get_iter(path)
        except TypeError:
            return

        try:
            if self._parent.model[_iter][9] == 2:
                return
        except AttributeError:
            return

        new_value = not self._parent.model[_iter][self._star_index]
        self._parent.model[_iter][self._star_index] = new_value
        song_item = self._parent.model[_iter][5]
        grilo.toggle_favorite(song_item)
        playlists.update_static_playlist(StaticPlaylists.Favorites)

        # Use this flag to ignore the upcoming _on_item_activated call
        self.star_renderer_click = True
