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
from gi.repository import GObject, Gtk

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
        self._sidebar.props.visible = True
        sidebar_container = Gtk.ScrolledWindow()
        sidebar_container.add(self._sidebar)
        sidebar_container.props.visible = True

        super().__init__(
            'artists', _("Artists"), application, sidebar_container)

        self._application = application
        self._artists = {}

        self._selected_artist = None
        self._loaded_artists = []

        # This indicates if the current list has been empty and has
        # had no user interaction since.
        self._untouched_list = True

        self._window = application.props.window
        self._coremodel = application.props.coremodel
        self._model = self._coremodel.props.artists_sort

        self._sidebar.bind_model(self._model, self._create_widget)

        self._model.connect_after(
            "items-changed", self._on_model_items_changed)
        self._on_model_items_changed(self._model, 0, 0, 0)

        sidebar_container.props.width_request = 220
        sidebar_container.get_style_context().add_class('sidebar')
        self._sidebar.props.selection_mode = Gtk.SelectionMode.SINGLE
        self._sidebar.connect('row-activated', self._on_artist_activated)

    def _create_widget(self, coreartist):
        row = ArtistTile(coreartist)
        row.props.text = coreartist.props.artist

        return row

    def _on_model_items_changed(self, model, position, removed, added):
        if model.get_n_items() == 0:
            self._untouched_list = True
            return
        elif self._untouched_list is True:
            first_row = self._sidebar.get_row_at_index(0)
            if first_row is None:
                return

            self._sidebar.select_row(first_row)
            self._on_artist_activated(self._sidebar, first_row, True)
            return

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
                self._on_artist_activated(self._sidebar, row_next, True)

        removed_frame = self._view.get_child_by_name(removed_artist)
        self._view.remove(removed_frame)

    def _setup_view(self):
        self._view_container = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self._box.add(self._view_container)

        self._view = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE,
            vhomogeneous=False)
        self._view_container.add(self._view)

        self._view.props.visible = True
        self._view_container.props.visible = True

    def _on_artist_activated(self, sidebar, row, data=None, untouched=False):
        """Initializes new artist album widgets"""
        # On application start the first row of ArtistView is activated
        # to show an intial artist. When this happens while any of the
        # views are in selection mode, this artist will be incorrectly
        # selected.
        # When selecting items check that the current visible view is
        # ArtistsView, to circumvent this issue.
        if (self.props.selection_mode
                and self._window.props.active_view is self):
            return

        if untouched is False:
            self._untouched_list = False

        selected_row = self._sidebar.get_selected_row()
        self._selected_artist = selected_row.props.coreartist

        # Prepare a new artist_albums_widget here
        coreartist = row.props.coreartist
        if coreartist.props.artist in self._loaded_artists:
            scroll_vadjustment = self._view_container.props.vadjustment
            scroll_vadjustment.props.value = 0.
            self._view.set_visible_child_name(coreartist.props.artist)
            return

        self._artist_albums = ArtistAlbumsWidget(coreartist, self._application)

        self.bind_property(
            "selection-mode", self._artist_albums, "selection-mode",
            GObject.BindingFlags.SYNC_CREATE
            | GObject.BindingFlags.BIDIRECTIONAL)

        artist_albums_frame = Gtk.Frame(
            shadow_type=Gtk.ShadowType.NONE, hexpand=True)
        artist_albums_frame.add(self._artist_albums)
        artist_albums_frame.show()

        self._view.add_named(artist_albums_frame, coreartist.props.artist)
        scroll_vadjustment = self._view_container.props.vadjustment
        scroll_vadjustment.props.value = 0.
        self._view.set_visible_child(artist_albums_frame)

        self._loaded_artists.append(coreartist.props.artist)

    def _on_selection_mode_changed(self, widget, data=None):
        if self.get_parent().get_visible_child() != self:
            return

        super()._on_selection_mode_changed(widget, data)
        self._sidebar.props.sensitive = not self.props.selection_mode

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

    def select_all(self):
        current_frame = self._view.get_visible_child()
        for row in current_frame.get_child():
            row.get_child().select_all()

    def deselect_all(self):
        current_frame = self._view.get_visible_child()
        for row in current_frame.get_child():
            row.get_child().deselect_all()
