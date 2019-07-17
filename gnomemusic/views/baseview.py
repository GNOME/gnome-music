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

    _now_playing_icon_name = 'media-playback-start-symbolic'
    _error_icon_name = 'dialog-error-symbolic'

    selected_items_count = GObject.Property(type=int, default=0, minimum=0)
    selection_mode = GObject.Property(type=bool, default=False)

    def __repr__(self):
        return '<BaseView>'

    @log
    def __init__(self, name, title, window, sidebar=None):
        """Initialize
        :param name: The view name
        :param title: The view title
        :param GtkWidget window: The main window
        :param sidebar: The sidebar object (Default: Gtk.Box)
        """

        super().__init__(transition_type=Gtk.StackTransitionType.CROSSFADE)

        self._grid = Gtk.Grid(orientation=Gtk.Orientation.HORIZONTAL)
        self._offset = 0
        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Setup the main view
        self._setup_view()

        if sidebar:
            self._grid.add(sidebar)

        self._grid.add(self._box)

        self._window = window
        self._headerbar = window._headerbar

        self.name = name
        self.title = title

        self.add(self._grid)
        self.show_all()
        # self._view.hide()

        self._init = False
        self._selection_mode_id = self.connect(
            "notify::selection-mode", self._on_selection_mode_changed)

        self.bind_property(
            'selection-mode', self._window, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL)

        if not self._init:
            self._on_grilo_ready()

    @log
    def _setup_view(self):
        """Instantiate and set up the view object"""
        pass

    @log
    def _on_grilo_ready(self, data=None):
        if (self._headerbar.props.stack.props.visible_child == self
                and not self._init):
            self._populate()

        self._headerbar.props.stack.connect(
            'notify::visible-child', self._on_headerbar_visible)

    @log
    def _on_headerbar_visible(self, widget, param):
        if (self == widget.get_visible_child()
                and not self._init):
            self._populate()

    @log
    def _populate(self, data=None):
        pass

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        if not self.props.selection_mode:
            self.unselect_all()

    @log
    def _on_item_activated(self, widget, id, path):
        pass

    @log
    def get_selected_songs(self, callback):
        callback([])
