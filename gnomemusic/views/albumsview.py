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

from __future__ import annotations
import typing

from gettext import gettext as _
from gi.repository import GLib, GObject, Gtk

from gnomemusic.widgets.headerbar import HeaderBar
from gnomemusic.widgets.albumcover import AlbumCover
from gnomemusic.widgets.albumwidget import AlbumWidget
if typing.TYPE_CHECKING:
    from gnomemusic.corealbum import CoreAlbum


@Gtk.Template(resource_path="/org/gnome/Music/ui/AlbumsView.ui")
class AlbumsView(Gtk.Stack):
    """Gridlike view of all albums

    Album activation switches to AlbumWidget.
    """

    __gtype_name__ = "AlbumsView"

    icon_name = GObject.Property(
        type=str, default="media-optical-cd-audio-symbolic",
        flags=GObject.ParamFlags.READABLE)
    search_mode_active = GObject.Property(type=bool, default=False)
    selection_mode = GObject.Property(type=bool, default=False)
    title = GObject.Property(
        type=str, default=_("Albums"), flags=GObject.ParamFlags.READABLE)

    _album_scrolled_window = Gtk.Template.Child()
    _scrolled_window = Gtk.Template.Child()
    _gridview = Gtk.Template.Child()

    def __init__(self, application):
        """Initialize AlbumsView

        :param application: The Application object
        """
        super().__init__(transition_type=Gtk.StackTransitionType.CROSSFADE)

        self.props.name = "albums"

        self._application = application
        self._window = application.props.window
        self._headerbar = self._window._headerbar

        list_item_factory = Gtk.SignalListItemFactory()
        list_item_factory.connect("setup", self._setup_list_item)
        list_item_factory.connect("bind", self._bind_list_item)

        self._gridview.props.factory = list_item_factory

        self._selection_model = Gtk.MultiSelection.new(
            self._application.props.coremodel.props.albums_sort)
        self._gridview.props.model = self._selection_model

        self._gridview.connect("activate", self._on_album_activated)

        self.bind_property(
            "selection-mode", self._gridview, "single-click-activate",
            GObject.BindingFlags.SYNC_CREATE |
                GObject.BindingFlags.INVERT_BOOLEAN)
        self.bind_property(
            "selection-mode", self._gridview, "enable-rubberband",
            GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "selection-mode", self._window, "selection-mode",
            GObject.BindingFlags.DEFAULT)

        self._window.connect(
            "notify::selection-mode", self._on_selection_mode_changed)

        self._album_widget = AlbumWidget(self._application)
        self._album_widget.bind_property(
            "selection-mode", self, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL)

        self._album_scrolled_window.set_child(self._album_widget)

        # self.connect(
        #     "notify::search-mode-active", self._on_search_mode_changed)

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
                and self.get_visible_child_name() == "widget"):
            self._set_album_headerbar(self._album_widget.props.corealbum)

    def _back_button_clicked(self, widget, data=None):
        self._headerbar.state = HeaderBar.State.MAIN
        self.props.visible_child = self._scrolled_window

    def _on_album_activated(self, widget, position):
        corealbum = widget.props.model[position]

        self._album_widget.props.corealbum = corealbum
        self._set_album_headerbar(corealbum)
        self.props.visible_child = self._album_scrolled_window

    def _on_child_activated(self, widget, child, user_data=None):
        corealbum = child.props.corealbum
        if self.props.selection_mode:
            return

        # Update and display the album widget if not in selection mode
        self._album_widget.props.corealbum = corealbum

        self._set_album_headerbar(corealbum)
        self.set_visible_child_name("widget")

    def _set_album_headerbar(self, corealbum: CoreAlbum) -> None:
        self._headerbar.props.state = HeaderBar.State.CHILD
        self._headerbar.set_label_title(
            corealbum.props.title, corealbum.props.artist)

    def _toggle_all_selection(self, selected):
        """Selects or deselects all items.
        """
        with self._application.props.coreselection.freeze_notify():
            if self.get_visible_child_name() == "widget":
                if selected is True:
                    self._album_widget.select_all()
                else:
                    self._album_widget.deselect_all()
            else:
                if selected:
                    self._selection_model.select_all()
                else:
                    self._selection_model.unselect_all()

    def select_all(self):
        self._toggle_all_selection(True)

    def deselect_all(self):
        self._toggle_all_selection(False)

    def _setup_list_item(self, factory, listitem):
        builder = Gtk.Builder.new_from_resource(
            "/org/gnome/Music/ui/AlbumCoverListItem.ui")
        listitem.set_child(builder.get_object("_album_cover"))

        self.bind_property(
            "selection-mode", listitem, "selectable",
            GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "selection-mode", listitem, "activatable",
            GObject.BindingFlags.SYNC_CREATE |
                GObject.BindingFlags.INVERT_BOOLEAN)

    def _bind_list_item(self, factory, listitem):
        widget = listitem.get_child()

        art_stack = widget.get_first_child().get_first_child()
        check = art_stack.get_next_sibling()
        album_label = widget.get_first_child().get_next_sibling()
        artist_label = album_label.get_next_sibling()

        listitem.props.item.bind_property(
            "corealbum", art_stack, "coreobject",
            GObject.BindingFlags.SYNC_CREATE)
        listitem.props.item.bind_property(
            "title", album_label, "label",
            GObject.BindingFlags.SYNC_CREATE)
        listitem.props.item.bind_property(
            "artist", artist_label, "label",
            GObject.BindingFlags.SYNC_CREATE)

        listitem.bind_property(
            "selected", listitem.props.item, "selected",
            GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "selection-mode", check, "visible",
            GObject.BindingFlags.SYNC_CREATE)
        check.bind_property(
            "active", listitem.props.item, "selected",
            GObject.BindingFlags.SYNC_CREATE
                | GObject.BindingFlags.BIDIRECTIONAL)

        def on_activated(widget, value):
            if check.props.active:
                self._selection_model.select_item(
                    listitem.get_position(), False)
            else:
                self._selection_model.unselect_item(
                    listitem.get_position())

        check.connect("notify::active", on_activated)
