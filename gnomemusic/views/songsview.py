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

from __future__ import annotations
import typing

from gettext import gettext as _
from gi.repository import GObject, Gtk
from typing import Dict, List

from gnomemusic.widgets.songwidgetmenu import SongWidgetMenu
import gnomemusic.utils as utils
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


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

    def __init__(self, application: Application) -> None:
        """Initialize

        :param GtkApplication window: The application object
        """
        super().__init__()

        self.props.name = "songs"

        self._application = application
        self._coremodel = application.props.coremodel
        self._player = application.props.player
        self._window = application.props.window

        self._list_item_bindings: Dict[
            Gtk.ListItem, List[GObject.Binding]] = {}
        self._list_item_star_controllers: Dict[
            Gtk.ListItem, List[GObject.Binding]] = {}

        selection_model = Gtk.MultiSelection.new(self._coremodel.props.songs)

        list_item_factory = Gtk.SignalListItemFactory()
        list_item_factory.connect("setup", self._setup_list_item)
        list_item_factory.connect("bind", self._bind_list_item)
        list_item_factory.connect("unbind", self._unbind_list_item)

        self._listview.props.factory = list_item_factory
        self._listview.props.model = selection_model

        self._listview.connect("activate", self._on_song_activated)

    def _on_song_activated(self, widget, position):
        coresong = widget.props.model[position]

        self._coremodel.props.active_core_object = coresong
        self._player.play(coresong)

    def _setup_list_item(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        builder = Gtk.Builder.new_from_resource(
            "/org/gnome/Music/ui/SongListItem.ui")
        song_box = builder.get_object("_song_box")
        list_item.props.child = song_box

        menu_button = builder.get_object("_menu_button")
        song_menu = SongWidgetMenu(self._application, song_box, None)
        menu_button.props.popover = song_menu

    def _bind_list_item(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        list_row = list_item.props.child
        coresong = list_item.props.item

        info_box = list_row.get_first_child()
        duration_label = info_box.get_next_sibling()
        star_box = duration_label.get_next_sibling()
        star_image = star_box.get_first_child()
        title_label = info_box.get_first_child()
        album_label = title_label.get_next_sibling()
        artist_label = album_label.get_next_sibling()
        menu_button = star_box.get_next_sibling()

        def _on_star_toggle(
                controller: Gtk.GestureClick, n_press: int, x: float,
                y: float) -> None:
            controller.set_state(Gtk.EventSequenceState.CLAIMED)
            coresong.props.favorite = not coresong.props.favorite
            star_image.props.favorite = coresong.props.favorite

        star_click = Gtk.GestureClick()
        star_click.props.button = 1
        star_click.connect("released", _on_star_toggle)
        star_image.add_controller(star_click)

        def _on_star_enter(
                controller: Gtk.EventControllerMotion, x: float,
                y: float) -> None:
            star_image.props.hover = True

        def _on_star_leave(controller: Gtk.EventControllerMotion) -> None:
            star_image.props.hover = False

        star_hover = Gtk.EventControllerMotion()
        star_hover.connect("enter", _on_star_enter)
        star_hover.connect("leave", _on_star_leave)
        star_image.add_controller(star_hover)

        song_menu = menu_button.props.popover
        song_menu.props.coreobject = coresong

        b1 = coresong.bind_property(
            "title", title_label, "label", GObject.BindingFlags.SYNC_CREATE)
        b2 = coresong.bind_property(
            "album", album_label, "label", GObject.BindingFlags.SYNC_CREATE)
        b3 = coresong.bind_property(
            "artist", artist_label, "label", GObject.BindingFlags.SYNC_CREATE)

        b4 = coresong.bind_property(
            "favorite", star_image, "favorite")

        duration_label.props.label = utils.seconds_to_string(
            coresong.props.duration)

        self._list_item_bindings[list_item] = [b1, b2, b3, b4]
        self._list_item_star_controllers[list_item] = [star_click, star_hover]

    def _unbind_list_item(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        bindings = self._list_item_bindings.pop(list_item)
        [binding.unbind() for binding in bindings]

        list_row = list_item.props.child
        info_box = list_row.get_first_child()
        duration_label = info_box.get_next_sibling()
        star_box = duration_label.get_next_sibling()
        star_image = star_box.get_first_child()

        controllers = self._list_item_star_controllers.pop(list_item)
        [star_image.remove_controller(ctrl) for ctrl in controllers]
