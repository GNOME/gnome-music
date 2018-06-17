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

import gi
gi.require_version("Gd", "1.0")
from gi.repository import Gd, GdkPixbuf, GObject, Gtk

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.widgets.starhandlerwidget import StarHandlerWidget


class BaseView(Gtk.Stack):
    """Base Class for all view classes"""

    _now_playing_icon_name = 'media-playback-start-symbolic'
    _error_icon_name = 'dialog-error-symbolic'
    selection_mode = GObject.Property(type=bool, default=False)

    def __repr__(self):
        return '<BaseView>'

    @log
    def __init__(self, name, title, window, view_type, use_sidebar=False,
                 sidebar=None):
        """Initialize
        :param name: The view name
        :param title: The view title
        :param GtkWidget window: The main window
        :param view_type: The Gtk view type
        :param use_sidebar: Whether to use sidebar
        :param sidebar: The sidebar object (Default: Gtk.Box)
        """

        super().__init__(transition_type=Gtk.StackTransitionType.CROSSFADE)

        self._grid = Gtk.Grid(orientation=Gtk.Orientation.HORIZONTAL)
        self._offset = 0
        self.model = Gtk.ListStore(
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GdkPixbuf.Pixbuf,
            GObject.TYPE_OBJECT,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT,
            GObject.TYPE_STRING,
            GObject.TYPE_INT,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT
        )
        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Setup the main view
        self._setup_view(view_type)

        if use_sidebar:
            self.stack = Gtk.Stack(
                transition_type=Gtk.StackTransitionType.SLIDE_RIGHT,)
            dummy = Gtk.Frame(visible=False)
            self.stack.add_named(dummy, 'dummy')
            if sidebar:
                self.stack.add_named(sidebar, 'sidebar')
            else:
                self.stack.add_named(self._box, 'sidebar')
            self.stack.set_visible_child_name('dummy')
            self._grid.add(self.stack)
        if not use_sidebar or sidebar:
            self._grid.add(self._box)

        self._star_handler = StarHandlerWidget(self, 9)
        self._window = window
        self._header_bar = window.headerbar
        self._selection_toolbar = window.selection_toolbar
        self._header_bar._cancel_button.connect(
            'clicked', self._on_cancel_button_clicked)

        self.name = name
        self.title = title

        self.add(self._grid)
        self.show_all()
        self._view.hide()

        self._init = False
        grilo.connect('ready', self._on_grilo_ready)
        self.connect('notify::selection-mode', self._on_selection_mode_changed)
        grilo.connect('changes-pending', self._on_changes_pending)

        self.bind_property(
            'selection-mode', self._selection_toolbar, 'visible',
            GObject.BindingFlags.SYNC_CREATE)

        self.bind_property(
            'selection-mode', self._header_bar, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL)

    @log
    def _on_changes_pending(self, data=None):
        pass

    @log
    def _setup_view(self, view_type):
        """Instantiate and set up the view object"""
        self._view = Gd.MainView(shadow_type=Gtk.ShadowType.NONE)
        self._view.set_view_type(view_type)

        self._view.click_handler = self._view.connect('item-activated',
                                                      self._on_item_activated)
        self._view.connect('selection-mode-request',
                           self._on_selection_mode_request)

        self._view.bind_property('selection-mode', self, 'selection_mode',
                                 GObject.BindingFlags.BIDIRECTIONAL)

        self._view.connect('view-selection-changed',
                           self._on_view_selection_changed)

        self._box.pack_start(self._view, True, True, 0)

    @log
    def _on_cancel_button_clicked(self, button):
        self.unselect_all()
        self.props.selection_mode = False

    @log
    def _on_grilo_ready(self, data=None):
        if (self._header_bar.props.stack.props.visible_child == self
                and not self._init):
            self._populate()
        self._header_bar.props.stack.connect(
            'notify::visible-child', self._on_headerbar_visible)

    @log
    def _on_headerbar_visible(self, widget, param):
        if (self == widget.get_visible_child()
                and not self._init):
            self._populate()

    @log
    def _on_view_selection_changed(self, widget):
        if not self.selection_mode:
            return
        items = self._view.get_selection()
        self.update_header_from_selection(len(items))

    @log
    def update_header_from_selection(self, n_items):
        """Updates header during item selection."""
        self._selection_toolbar.props.items_selected = n_items
        self._header_bar.props.items_selected = n_items

    @log
    def _populate(self, data=None):
        self.populate()

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        if self.props.selection_mode:
            self.set_player_visible(False)
        else:
            self.set_player_visible(self.player.current_song is not None)
            self.unselect_all()

    @log
    def populate(self):
        pass

    @log
    def _retrieval_finished(self, klass):
        self.model[klass.iter][4] = klass.pixbuf

    @log
    def _add_list_renderers(self):
        pass

    @log
    def _on_item_activated(self, widget, id, path):
        pass

    @log
    def _on_selection_mode_request(self, *args):
        self.props.selection_mode = not self.props.selection_mode

    @log
    def get_selected_songs(self, callback):
        callback([])

    @log
    def _set_selection(self, value, parent=None):
        count = 0
        itr = self.model.iter_children(parent)
        while itr is not None:
            if self.model.iter_has_child(itr):
                count += self._set_selection(value, itr)
            if self.model[itr][5] is not None:
                self.model[itr][6] = value
                count += 1
            itr = self.model.iter_next(itr)
        return count

    @log
    def select_all(self):
        """Select all the available songs."""
        count = self._set_selection(True)

        self._selection_toolbar.props.items_selected = count
        self.update_header_from_selection(count)

    @log
    def unselect_all(self):
        """Unselects all the selected songs."""
        self._set_selection(False)
        self._selection_toolbar.props.items_selected = 0
        self._header_bar.props.items_selected = 0

    @log
    def set_player_visible(self, visible):
        """Set PlayWidget action visibility

        :param bool visible: Set actionbar visibility
        """
        self._window.player_toolbar.set_visible(visible)
