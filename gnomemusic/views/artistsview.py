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

import logging
from gettext import gettext as _
from gi.repository import Gdk, Gtk

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.views.baseview import BaseView
from gnomemusic.widgets.artistalbumswidget import ArtistAlbumsWidget
from gnomemusic.widgets.sidebarrow import SidebarRow

logger = logging.getLogger(__name__)


class ArtistsView(BaseView):
    """Main view of all available artists

    Consists of a list of artists on the left side and an overview of
    all albums by this artist on the right side.
    """

    def __repr__(self):
        return '<ArtistsView>'

    @log
    def __init__(self, window, player):
        """Initialize

        :param GtkWidget window: The main window
        :param player: The main player object
        """
        self._sidebar = Gtk.ListBox()
        sidebar_container = Gtk.ScrolledWindow()
        sidebar_container.add(self._sidebar)

        super().__init__('artists', _("Artists"), window, sidebar_container)

        self.player = player
        self._artists = {}

        self._window = window
        self._model = window._app._coremodel.get_artists_model()
        self._sidebar.bind_model(self._model, self._create_widget)

        sidebar_container.props.width_request = 220
        sidebar_container.get_style_context().add_class('sidebar')
        self._sidebar.props.selection_mode = Gtk.SelectionMode.SINGLE
        self._sidebar.connect('row-activated', self._on_artist_activated)

        self._ctrl = Gtk.GestureMultiPress().new(self._sidebar)
        self._ctrl.props.propagation_phase = Gtk.PropagationPhase.CAPTURE
        self._ctrl.props.button = Gdk.BUTTON_PRIMARY
        self._ctrl.connect("released", self._on_sidebar_clicked)

        self.show_all()

    def _create_widget(self, coreartist):
        row = SidebarRow(coreartist)
        row.props.text = coreartist.props.artist

        self.bind_property("selection-mode", row, "selection-mode")

        return row

    @log
    def _setup_view(self):
        view_container = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self._box.pack_start(view_container, True, True, 0)

        self._view = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE)
        view_container.add(self._view)

        self._artist_albums_widget = Gtk.Frame(
            shadow_type=Gtk.ShadowType.NONE, hexpand=True)
        self._view.add_named(self._artist_albums_widget, "artist-albums")
        self._view.props.visible_child_name = "artist-albums"

    @log
    def _on_changes_pending(self, data=None):
        if (self._init
                and not self.props.selection_mode):
            self._artists.clear()
            self._offset = 0
            self._populate()
            grilo.changes_pending['Artists'] = False

    @log
    def _on_artist_activated(self, sidebar, row, data=None):
        """Initializes new artist album widgets"""
        if self.props.selection_mode:
            row.props.selected = not row.props.selected
            return

        # Prepare a new artist_albums_widget here
        coreartist = row.props.coreartist

        new_artist_albums_widget = Gtk.Frame(
            shadow_type=Gtk.ShadowType.NONE, hexpand=True)
        self._view.add(new_artist_albums_widget)

        artist_albums = ArtistAlbumsWidget(
            coreartist, self.player, self._window, False)
        new_artist_albums_widget.add(artist_albums)
        new_artist_albums_widget.show()

        # Replace previous widget
        self._artist_albums_widget = new_artist_albums_widget
        self._view.set_visible_child(new_artist_albums_widget)

        return

    @log
    def _populate(self, data=None):
        """Populates the view"""
        pass

    @log
    def _on_sidebar_clicked(self, gesture, n_press, x, y):
        success, state = Gtk.get_current_event_state()
        modifiers = Gtk.accelerator_get_default_mod_mask()
        if ((state & modifiers) == Gdk.ModifierType.CONTROL_MASK
                and not self.props.selection_mode):
            self.props.selection_mode = True

    @log
    def _on_selection_changed(self, widget, value, data=None):
        return

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        super()._on_selection_mode_changed(widget, data)

        self._view.props.sensitive = not self.props.selection_mode
        if self.props.selection_mode:
            self._sidebar.props.selection_mode = Gtk.SelectionMode.NONE
        else:
            self._sidebar.props.selection_mode = Gtk.SelectionMode.SINGLE

    @log
    def _toggle_all_selection(self, selected):
        for row in self._sidebar:
            row.props.selected = selected

    @log
    def select_all(self):
        self._toggle_all_selection(True)

    @log
    def unselect_all(self):
        self._toggle_all_selection(False)
