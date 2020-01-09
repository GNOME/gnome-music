# Copyright 2019 The GNOME Music Developers
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

import math

from gettext import gettext as _
from gi.repository import GLib, GObject, Gtk

from gnomemusic.widgets.headerbar import HeaderBar
from gnomemusic.widgets.albumcover import AlbumCover
from gnomemusic.widgets.albumwidget import AlbumWidget


@Gtk.Template(resource_path="/org/gnome/Music/ui/AlbumsView.ui")
class AlbumsView(Gtk.Stack):
    """Gridlike view of all albums

    Album activation switches to AlbumWidget.
    """

    __gtype_name__ = "AlbumsView"

    search_mode_active = GObject.Property(type=bool, default=False)
    selection_mode = GObject.Property(type=bool, default=False)

    _scrolled_window = Gtk.Template.Child()
    _flowbox = Gtk.Template.Child()

    def __repr__(self):
        return '<AlbumsView>'

    def __init__(self, application, player=None):
        """Initialize AlbumsView

        :param application: The Application object
        """
        super().__init__(transition_type=Gtk.StackTransitionType.CROSSFADE)

        # FIXME: Make these properties.
        self.name = "albums"
        self.title = _("Albums")

        self._window = application.props.window
        self._headerbar = self._window._headerbar
        self._adjustment_timeout_id = None
        self._viewport = self._scrolled_window.get_child()
        self._widget_counter = 1

        model = self._window._app.props.coremodel.props.albums_sort
        self._flowbox.bind_model(model, self._create_widget)
        self._flowbox.connect("child-activated", self._on_child_activated)

        self.bind_property(
            "selection-mode", self._window, "selection-mode",
            GObject.BindingFlags.DEFAULT)

        self._window.connect(
            "notify::selection-mode", self._on_selection_mode_changed)

        self._album_widget = AlbumWidget(application.props.player, self)
        self._album_widget.bind_property(
            "selection-mode", self, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL)

        self.add(self._album_widget)

        self.connect(
            "notify::search-mode-active", self._on_search_mode_changed)

        self._scrolled_window.props.vadjustment.connect(
            "value-changed", self._on_vadjustment_changed)
        self._scrolled_window.props.vadjustment.connect(
            "changed", self._on_vadjustment_changed)

        self.show_all()

    def _on_vadjustment_changed(self, adjustment):
        if self._adjustment_timeout_id is not None:
            GLib.source_remove(self._adjustment_timeout_id)
            self._adjustment_timeout_id = None

        self._adjustment_timeout_id = GLib.timeout_add(
            200, self._retrieve_covers, adjustment.props.value,
            priority=GLib.PRIORITY_LOW)

    def _retrieve_covers(self, old_adjustment):
        adjustment = self._scrolled_window.props.vadjustment.props.value

        if old_adjustment != adjustment:
            return GLib.SOURCE_CONTINUE

        first_cover = self._flowbox.get_child_at_index(0)
        if first_cover is None:
            return GLib.SOURCE_REMOVE

        cover_size, _ = first_cover.get_allocated_size()
        if cover_size.width == 0 or cover_size.height == 0:
            return GLib.SOURCE_REMOVE

        viewport_size, _ = self._viewport.get_allocated_size()

        h_space = self._flowbox.get_column_spacing()
        v_space = self._flowbox.get_row_spacing()
        nr_cols = (
            (viewport_size.width + h_space) // (cover_size.width + h_space))

        top_left_cover = self._flowbox.get_child_at_index(
            nr_cols * (adjustment // (cover_size.height + v_space)))

        covers_col = math.ceil(viewport_size.width / cover_size.width)
        covers_row = math.ceil(viewport_size.height / cover_size.height)

        children = self._flowbox.get_children()
        retrieve_list = []
        for i, albumcover in enumerate(children):
            if top_left_cover == albumcover:
                retrieve_covers = covers_row * covers_col
                retrieve_list = children[i:i + retrieve_covers]
                break

        for albumcover in retrieve_list:
            albumcover.retrieve()

        self._adjustment_timeout_id = None

        return GLib.SOURCE_REMOVE

    def _on_selection_mode_changed(self, widget, data=None):
        selection_mode = self._window.props.selection_mode
        if (selection_mode == self.props.selection_mode
                or self.get_parent().get_visible_child() != self):
            return

        self.props.selection_mode = selection_mode
        if not self.props.selection_mode:
            self.deselect_all()

    def _on_search_mode_changed(self, klass, param):
        if (not self.props.search_mode_active
                and self._headerbar.props.stack.props.visible_child == self
                and self.get_visible_child() == self._album_widget):
            self._set_album_headerbar(self._album_widget.props.album)

    def _create_widget(self, corealbum):
        album_widget = AlbumCover(corealbum)

        self.bind_property(
            "selection-mode", album_widget, "selection-mode",
            GObject.BindingFlags.SYNC_CREATE
            | GObject.BindingFlags.BIDIRECTIONAL)

        # NOTE: Adding SYNC_CREATE here will trigger all the nested
        # models to be created. This will slow down initial start,
        # but will improve initial 'selecte all' speed.
        album_widget.bind_property(
            "selected", corealbum, "selected",
            GObject.BindingFlags.BIDIRECTIONAL)

        GLib.timeout_add(
            self._widget_counter * 250, album_widget.retrieve,
            priority=GLib.PRIORITY_LOW)
        self._widget_counter = self._widget_counter + 1

        return album_widget

    def _back_button_clicked(self, widget, data=None):
        self._headerbar.state = HeaderBar.State.MAIN
        self.props.visible_child = self._scrolled_window

    def _on_child_activated(self, widget, child, user_data=None):
        corealbum = child.props.corealbum
        if self.props.selection_mode:
            return

        # Update and display the album widget if not in selection mode
        self._album_widget.update(corealbum)

        self._set_album_headerbar(corealbum)
        self.set_visible_child(self._album_widget)

    def _set_album_headerbar(self, corealbum):
        self._headerbar.props.state = HeaderBar.State.CHILD
        self._headerbar.props.title = corealbum.props.title
        self._headerbar.props.subtitle = corealbum.props.artist

    def _toggle_all_selection(self, selected):
        """
        Selects or deselects all items without sending the notify::active
        signal for performance purposes.
        """
        with self._window._app.props.coreselection.freeze_notify():
            for child in self._flowbox.get_children():
                child.props.selected = selected
                child.props.corealbum.props.selected = selected

    def select_all(self):
        self._toggle_all_selection(True)

    def deselect_all(self):
        self._toggle_all_selection(False)
