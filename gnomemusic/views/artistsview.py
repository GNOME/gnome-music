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

from gettext import gettext as _
from gi.repository import Gdk, Gtk

from gnomemusic.views.baseview import BaseView
from gnomemusic.widgets.artistalbumswidget import ArtistAlbumsWidget
from gnomemusic.widgets.artisttile import ArtistTile


class ArtistsView(BaseView):
    """Main view of all available artists

    Consists of a list of artists on the left side and an overview of
    all albums by this artist on the right side.
    """

    def __init__(self, application):
        """Initialize

        :param GtkApplication application: The application object
        """
        self._sidebar = Gtk.ListBox()
        sidebar_container = Gtk.ScrolledWindow()
        sidebar_container.add(self._sidebar)

        super().__init__(
            'artists', _("Artists"), application, sidebar_container)

        self._application = application
        self._artists = {}

        self._selected_artist = None
        self._loaded_artists = []

        self._window = application.props.window
        self._coremodel = application.props.coremodel
        self._model = self._coremodel.props.artists_sort

        self._model.connect_after(
            "items-changed", self._on_model_items_changed)
        self._sidebar.bind_model(self._model, self._create_widget)

        if self._coremodel.props.artists_available is False:
            self._loaded_id = self._coremodel.connect(
                "notify::artists-available", self._on_artists_available)
        else:
            self._loaded_id = 0
            self._on_artists_available()

        sidebar_container.props.width_request = 220
        sidebar_container.get_style_context().add_class('sidebar')
        self._sidebar.props.selection_mode = Gtk.SelectionMode.SINGLE
        self._sidebar.connect('row-activated', self._on_artist_activated)

        self._ctrl = Gtk.GestureMultiPress().new(self._sidebar)
        self._ctrl.props.propagation_phase = Gtk.PropagationPhase.CAPTURE
        self._ctrl.props.button = Gdk.BUTTON_PRIMARY
        self._ctrl.connect("released", self._on_sidebar_clicked)

        self._loading_id = 0

        self.show_all()

    def _create_widget(self, coreartist):
        row = ArtistTile(coreartist)
        row.props.text = coreartist.props.artist

        self.bind_property("selection-mode", row, "selection-mode")

        return row

    def _on_model_items_changed(self, model, position, removed, added):
        if removed == 0:
            return

        removed_artist = None
        artists = [coreartist.props.artist for coreartist in model]
        for artist in self._loaded_artists:
            if artist not in artists:
                removed_artist = artist
                break

        if removed_artist is None:
            return

        self._loaded_artists.remove(removed_artist)
        if self._view.get_visible_child_name() == removed_artist:
            row_next = (self._sidebar.get_row_at_index(position)
                        or self._sidebar.get_row_at_index(position - 1))
            if row_next:
                self._sidebar.select_row(row_next)
                self._on_artist_activated(self._sidebar, row_next)

        removed_frame = self._view.get_child_by_name(removed_artist)
        self._view.remove(removed_frame)

    def _on_artists_available(self, klass=None, value=None):
        if self._loaded_id > 0:
            self._coremodel.disconnect(self._loaded_id)
            self._loaded_id = 0

        first_row = self._sidebar.get_row_at_index(0)
        if first_row is None:
            return

        self._sidebar.select_row(first_row)
        self._on_artist_activated(self._sidebar, first_row)

    def _setup_view(self):
        self._view_container = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self._box.pack_start(self._view_container, True, True, 0)

        self._view = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE,
            vhomogeneous=False)
        self._view_container.add(self._view)

    def _on_artist_activated(self, sidebar, row, data=None):
        """Initializes new artist album widgets"""
        # On application start the first row of ArtistView is activated
        # to show an intial artist. When this happens while any of the
        # views are in selection mode, this artist will be incorrectly
        # selected.
        # When selecting items check that the current visible view is
        # ArtistsView, to circumvent this issue.
        if (self.props.selection_mode
                and self._window.props.active_view is self):
            row.props.selected = not row.props.selected
            return

        selected_row = self._sidebar.get_selected_row()
        self._selected_artist = selected_row.props.coreartist

        # Prepare a new artist_albums_widget here
        coreartist = row.props.coreartist
        if coreartist.props.artist in self._loaded_artists:
            scroll_vadjustment = self._view_container.props.vadjustment
            scroll_vadjustment.props.value = 0.
            self._view.set_visible_child_name(coreartist.props.artist)
            return

        self._artist_albums = ArtistAlbumsWidget(
            coreartist, self._application, False)
        artist_albums_frame = Gtk.Frame(
            shadow_type=Gtk.ShadowType.NONE, hexpand=True)
        artist_albums_frame.add(self._artist_albums)
        artist_albums_frame.show()

        self._view.add_named(artist_albums_frame, coreartist.props.artist)
        scroll_vadjustment = self._view_container.props.vadjustment
        scroll_vadjustment.props.value = 0.
        self._view.set_visible_child(artist_albums_frame)

        self._loaded_artists.append(coreartist.props.artist)

    def _on_sidebar_clicked(self, gesture, n_press, x, y):
        success, state = Gtk.get_current_event_state()
        modifiers = Gtk.accelerator_get_default_mod_mask()
        if ((state & modifiers) == Gdk.ModifierType.CONTROL_MASK
                and not self.props.selection_mode):
            self.props.selection_mode = True

    def _on_selection_mode_changed(self, widget, data=None):
        if self.get_parent().get_visible_child() != self:
            return

        super()._on_selection_mode_changed(widget, data)

        self._view.props.sensitive = not self.props.selection_mode
        if self.props.selection_mode:
            self._sidebar.props.selection_mode = Gtk.SelectionMode.NONE
        else:
            self._sidebar.props.selection_mode = Gtk.SelectionMode.SINGLE
            selected_row = self._sidebar.get_row_at_index(0)
            if selected_row is None:
                self._selected_artist = None
                return

            for row in self._sidebar:
                if row.props.coreartist == self._selected_artist:
                    selected_row = row
                    break

            self._sidebar.select_row(selected_row)
            self._selected_artist = None

    def _toggle_all_selection(self, selected):

        def toggle_selection(child):
            child.props.selected = selected

        self._sidebar.foreach(toggle_selection)

    def select_all(self):
        self._toggle_all_selection(True)

    def deselect_all(self):
        self._toggle_all_selection(False)
