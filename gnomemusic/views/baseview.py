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


class BaseView(Gtk.Stack):
    """Base Class for all view classes"""

    selected_items_count = GObject.Property(type=int, default=0, minimum=0)
    selection_mode = GObject.Property(type=bool, default=False)

    def __repr__(self):
        return '<BaseView>'

    @log
    def __init__(self, name, title, application, sidebar=None):
        """Initialize
        :param name: The view name
        :param title: The view title
        :param GtkApplication application: The application object
        :param sidebar: The sidebar object (Default: Gtk.Box)
        """
        super().__init__(transition_type=Gtk.StackTransitionType.CROSSFADE)

        self._grid = Gtk.Grid(orientation=Gtk.Orientation.HORIZONTAL)
        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Setup the main view
        self._setup_view()

        if sidebar:
            self._grid.add(sidebar)

        self._grid.add(self._box)

        self._window = application.props.window
        self._headerbar = self._window._headerbar

        self.name = name
        self.title = title

        self.add(self._grid)

        self._grid.props.visible = True
        self._box.props.visible = True
        self.props.visible = True

        self._selection_mode_id = self.connect(
            "notify::selection-mode", self._on_selection_mode_changed)

        self.bind_property(
            'selection-mode', self._window, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL)

    @log
    def _setup_view(self):
        """Instantiate and set up the view object"""
        pass

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        if (self.get_parent().get_visible_child() == self
                and not self.props.selection_mode):
            self.unselect_all()
