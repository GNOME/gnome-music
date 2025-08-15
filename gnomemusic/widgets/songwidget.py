# Copyright © 2018 The GNOME Music developers
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

from enum import IntEnum
from typing import Optional

from gi.repository import Gdk, GObject, Gtk

from gnomemusic import utils
from gnomemusic.coresong import CoreSong
from gnomemusic.utils import SongStateIcon
from gnomemusic.widgets.startoggle import StarToggle  # noqa: F401


@Gtk.Template(resource_path='/org/gnome/Music/ui/SongWidget.ui')
class SongWidget(Gtk.ListBoxRow):
    """The single song widget used in DiscBox

    Contains
     * play icon (depending on state)
     * song number on disc (optional)
     * song title
     * song duration (optional)
     * favorite/star picker (optional)
    """

    __gtype_name__ = 'SongWidget'

    __gsignals__ = {
        "widget-moved": (GObject.SignalFlags.RUN_FIRST, None, (int,))
    }

    coresong = GObject.Property(type=CoreSong, default=None)
    show_song_number = GObject.Property(type=bool, default=True)

    _album_label = Gtk.Template.Child()
    _album_duration_box = Gtk.Template.Child()
    _artist_box = Gtk.Template.Child()
    _artist_label = Gtk.Template.Child()
    _dnd_icon = Gtk.Template.Child()
    _drag_source = Gtk.Template.Child()
    _menu_button = Gtk.Template.Child()
    _number_label = Gtk.Template.Child()
    _title_label = Gtk.Template.Child()
    _duration_label = Gtk.Template.Child()
    _star_toggle = Gtk.Template.Child()
    _play_icon = Gtk.Template.Child()
    _size_group = Gtk.Template.Child()

    class State(IntEnum):
        """The state of the SongWidget
        """
        PLAYED = 0
        PLAYING = 1
        UNPLAYED = 2

    def __init__(self, coresong, can_dnd=False, show_artist_and_album=False):
        """Instanciates a SongWidget

        :param Corsong coresong: song associated with the widget
        :param bool can_dnd: allow drag and drop operations
        :param bool show_artist_and_album: display artist and album
        """
        super().__init__()

        self.props.coresong = coresong
        self._state = SongWidget.State.UNPLAYED

        self.props.coresong.bind_property(
            "track-number", self, "song-number",
            GObject.BindingFlags.SYNC_CREATE)

        self._title_label.set_max_width_chars(50)
        self.props.coresong.bind_property(
            "title", self._title_label, "label",
            GObject.BindingFlags.SYNC_CREATE)
        self.props.coresong.bind_property(
            "title", self._title_label, "tooltip-text",
            GObject.BindingFlags.SYNC_CREATE)

        time = utils.seconds_to_string(self.props.coresong.props.duration)
        self._duration_label.props.label = time

        if show_artist_and_album is True:
            self.props.coresong.bind_property(
                "album", self._album_label, "label",
                GObject.BindingFlags.SYNC_CREATE)
            self._album_label.props.visible = True
            self.props.coresong.bind_property(
                "artist", self._artist_label, "label",
                GObject.BindingFlags.SYNC_CREATE)
            self._artist_box.props.visible = True
        else:
            self._size_group.remove_widget(self._album_duration_box)

        self._play_icon.set_from_icon_name("media-playback-start-symbolic")

        self.bind_property(
            'show-song-number', self._number_label, 'visible',
            GObject.BindingFlags.SYNC_CREATE)
        self.props.coresong.bind_property(
            "favorite", self._star_toggle, "active",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self.props.coresong.bind_property(
            "state", self, "state",
            GObject.BindingFlags.SYNC_CREATE)
        self.props.coresong.connect(
            "notify::validation", self._on_validation_changed)

        self._drag_x = 0.
        self._drag_y = 0.
        self._drag_widget: Optional[Gtk.ListBox] = None
        if can_dnd:
            capture_phase = Gtk.PropagationPhase.CAPTURE
            self._drag_source.props.propagation_phase = capture_phase
            self._dnd_icon.props.visible = True

    @Gtk.Template.Callback()
    def _on_drag_prepare(
        self, drag_source: Gtk.DragSource, x: float,
            y: float) -> Gdk.ContentProvider:
        self._drag_x = x
        self._drag_y = y
        return Gdk.ContentProvider.new_for_value(self)

    @Gtk.Template.Callback()
    def _on_drag_begin(
            self, drag_source: Gtk.DragSource, drag: Gdk.Drag) -> None:
        allocation = self.get_allocation()
        self._drag_widget = Gtk.ListBox()
        self._drag_widget.set_size_request(allocation.width, allocation.height)

        drag_row = SongWidget(self.props.coresong, False, True)
        drag_row.props.show_song_number = self.props.show_song_number
        self._drag_widget.append(drag_row)
        self._drag_widget.drag_highlight_row(drag_row)

        drag_icon = Gtk.DragIcon.get_for_drag(drag)
        drag_icon.props.child = self._drag_widget
        drag.set_hotspot(self._drag_x, self._drag_y)

    @Gtk.Template.Callback()
    def _on_drop(
            self, target: Gtk.DropTarget,
            source_widget: SongWidget, x: float, y: float) -> bool:
        self._drag_widget = None
        self._drag_x = 0.
        self._drag_y = 0.

        source_position = source_widget.get_index()
        target_position = self.get_index()
        if source_position == target_position:
            return False

        self.emit("widget-moved", source_position)
        return True

    @GObject.Property
    def state(self):
        """State of the widget

        :returns: Widget state
        :rtype: SongWidget.State
        """
        return self._state

    @state.setter  # type: ignore
    def state(self, value):
        """Set state of the of widget

        This influences the look of the widgets label and if there is a
        song play indicator being shown.

        :param SongWidget.State value: Widget state
        """
        self._state = value

        style_ctx = self._title_label.get_style_context()

        style_ctx.remove_class('dim-label')
        style_ctx.remove_class('playing-song-label')
        self._play_icon.set_visible(False)

        coresong = self.props.coresong
        if coresong.props.validation == CoreSong.Validation.FAILED:
            self._play_icon.set_visible(True)
            style_ctx.add_class("dim-label")
            return

        if value == SongWidget.State.PLAYED:
            style_ctx.add_class('dim-label')
        elif value == SongWidget.State.PLAYING:
            self._play_icon.set_visible(True)
            style_ctx.add_class('playing-song-label')

    def _on_validation_changed(self, coresong, sate):
        validation_status = coresong.props.validation
        if validation_status == CoreSong.Validation.FAILED:
            self._play_icon.props.icon_name = SongStateIcon.ERROR.value
            self._play_icon.set_visible(True)
        else:
            self._play_icon.props.icon_name = SongStateIcon.PLAYING.value

    @GObject.Property(type=str, default="")
    def song_number(self):
        """Get song number label

        :returns: the song number
        :rtype: str
        """
        return self._number_label.props.label

    @song_number.setter  # type: ignore
    def song_number(self, new_nr):
        """Set song number label from an integer

        :param int new_nr: new song number
        """
        if new_nr == 0:
            new_nr = ""

        self._number_label.props.label = str(new_nr)

    @GObject.Property(type=Gtk.Popover, default=None)
    def menu(self) -> Optional[Gtk.Popover]:
        """Get the song menu.

        If no menu is set, the menu button is not displayed.

        :returns: song menu
        :rtype: Gtk.PopoverMenu
        """
        return self._menu_button.props.popover

    @menu.setter  # type: ignore
    def menu(self, menu: Optional[Gtk.PopoverMenu]) -> None:
        """Set song menu.

        :param Gtk.PopoverMenu menu: new song menu
        """
        self._menu_button.props.popover = menu
        self._menu_button.props.visible = (menu is not None)
