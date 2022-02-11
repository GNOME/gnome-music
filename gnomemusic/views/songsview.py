# Copyright 2022 The GNOME Music Developers
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
from gi.repository import Adw, GObject, Gtk

from gnomemusic.coresong import CoreSong
from gnomemusic.utils import SongStateIcon
from gnomemusic.widgets.starhandlerwidget import StarHandlerWidget


@Gtk.Template(resource_path="/org/gnome/Music/ui/SongsView.ui")
class SongsView(Gtk.Box):
    """Main view of all songs sorted artistwise

    Consists all songs along with songname, star, length, artist
    and the album name.
    """

    __gtype_name__ = "SongsView"

    icon_name = GObject.Property(
        type=str, default="emblem-music-symbolic",
        flags=GObject.ParamFlags.READABLE)
    title = GObject.Property(
        type=str, default=_("Songs"), flags=GObject.ParamFlags.READABLE)

    _listview = Gtk.Template.Child()

    def __init__(self, application):
        """Initialize

        :param GtkApplication window: The application object
        """
        super().__init__()

        self.props.name = "songs"

        self._coremodel = application.props.coremodel
        self._coreselection = application.props.coreselection
        self._window = application.props.window

        self._playlist_model = self._coremodel.props.playlist_sort
        self._model = self._coremodel.props.songs
        self._selection_model = Gtk.MultiSelection.new(self._model)

        list_item_factory = Gtk.SignalListItemFactory()
        list_item_factory.connect("setup", self._setup_list_item)
        list_item_factory.connect("bind", self._bind_list_item)

        self._listview.props.factory = list_item_factory
        self._listview.props.model = self._selection_model

        self._player = application.props.player
        # self._player.connect('song-changed', self._update_model)

        self._selection_mode = False

        self.bind_property(
            "selection-mode", self._listview, "single-click-activate",
            GObject.BindingFlags.SYNC_CREATE |
                GObject.BindingFlags.INVERT_BOOLEAN)
        self.bind_property(
            "selection-mode", self._listview, "enable-rubberband",
            GObject.BindingFlags.SYNC_CREATE)
        self._window.bind_property(
            "selection-mode", self, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL)

    def _setup_list_item(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        builder = Gtk.Builder.new_from_resource(
            "/org/gnome/Music/ui/SongListItem.ui")
        list_item.props.child = builder.get_object("_song_box")

        self.bind_property(
            "selection-mode", list_item, "selectable",
            GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "selection-mode", list_item, "activatable",
            GObject.BindingFlags.SYNC_CREATE
            | GObject.BindingFlags.INVERT_BOOLEAN)

    def _bind_list_item(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        list_row = list_item.props.child
        coresong = list_item.props.item

        check = list_row.get_first_child()
        info_box = check.get_next_sibling()
        title_label = info_box.get_first_child()
        album_label = title_label.get_next_sibling()
        artist_label = album_label.get_next_sibling()

        coresong.bind_property(
            "title", title_label, "label",
            GObject.BindingFlags.SYNC_CREATE)
        coresong.bind_property(
            "album", album_label, "label",
            GObject.BindingFlags.SYNC_CREATE)
        coresong.bind_property(
            "artist", artist_label, "label",
            GObject.BindingFlags.SYNC_CREATE)

        list_item.bind_property(
            "selected", coresong, "selected",
            GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "selection-mode", check, "visible",
            GObject.BindingFlags.SYNC_CREATE)
        check.bind_property(
            "active", coresong, "selected",
            GObject.BindingFlags.SYNC_CREATE
            | GObject.BindingFlags.BIDIRECTIONAL)

        def on_activated(widget, value):
            if check.props.active:
                self._selection_model.select_item(
                    list_item.get_position(), False)
            else:
                self._selection_model.unselect_item(
                    list_item.get_position())

        # The listitem selected property is read-only.
        # It cannot be bound from the check active property.
        # It is necessary to update the selection model in order
        # to update it.
        check.connect("notify::active", on_activated)

    @GObject.Property(type=bool, default=False)
    def selection_mode(self):
        """selection mode getter

        :returns: If selection mode is active
        :rtype: bool
        """
        return self._selection_mode

    @selection_mode.setter  # type: ignore
    def selection_mode(self, value):
        """selection-mode setter

        :param bool value: Activate selection mode
        """
        if (value == self._selection_mode
                or self.get_parent().get_visible_child() != self):
            return

        self._selection_mode = value
        if self._selection_mode is False:
            self.deselect_all()

    def _toggle_all_selection(self, selected):
        """Selects or deselects all items.
        """
        with self._coreselection.freeze_notify():
            if selected:
                self._selection_model.select_all()
            else:
                self._selection_model.unselect_all()

    def select_all(self):
        self._toggle_all_selection(True)

    def deselect_all(self):
        self._toggle_all_selection(False)
