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

from enum import IntEnum

import gi
from gi.repository import Gdk, GObject, Gtk

from gnomemusic import utils
from gnomemusic.coresong import CoreSong
from gnomemusic.utils import SongStateIcon
from gnomemusic.widgets.starimage import StarImage  # noqa: F401


@Gtk.Template(resource_path='/org/gnome/Music/ui/SongWidget.ui')
class SongWidget(Gtk.EventBox):
    """The single song widget used in DiscListBox

    Contains
     * play icon (depending on state)
     * selection check box (optional)
     * song number on disc (optional)
     * song title
     * song duration (optional)
     * favorite/star picker (optional)
    """

    __gtype_name__ = 'SongWidget'

    __gsignals__ = {
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        "widget-moved": (GObject.SignalFlags.RUN_FIRST, None, (int,))
    }

    coresong = GObject.Property(type=CoreSong, default=None)
    select_click = GObject.Property(type=bool, default=False)
    selected = GObject.Property(type=bool, default=False)
    show_duration = GObject.Property(type=bool, default=True)
    show_favorite = GObject.Property(type=bool, default=True)
    show_song_number = GObject.Property(type=bool, default=True)

    _album_label = Gtk.Template.Child()
    _album_duration_box = Gtk.Template.Child()
    _artist_box = Gtk.Template.Child()
    _artist_label = Gtk.Template.Child()
    _dnd_eventbox = Gtk.Template.Child()
    _select_button = Gtk.Template.Child()
    _number_label = Gtk.Template.Child()
    _title_label = Gtk.Template.Child()
    _duration_label = Gtk.Template.Child()
    _star_eventbox = Gtk.Template.Child()
    _star_image = Gtk.Template.Child()
    _star_stack = Gtk.Template.Child()
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
        self._selection_mode = False
        self._state = SongWidget.State.UNPLAYED

        song_number = self.props.coresong.props.track_number
        if song_number == 0:
            song_number = ""
        self._number_label.set_text(str(song_number))

        title = self.props.coresong.props.title
        self._title_label.set_max_width_chars(50)
        self._title_label.set_text(title)
        self._title_label.props.tooltip_text = title

        time = utils.seconds_to_string(self.props.coresong.props.duration)
        self._duration_label.props.label = time

        if show_artist_and_album is True:
            album = self.props.coresong.props.album
            self._album_label.props.label = album
            self._album_label.props.visible = True
            artist = self.props.coresong.props.artist
            self._artist_label.props.label = artist
            self._artist_box.props.visible = True
        else:
            self._size_group.remove_widget(self._album_duration_box)

        self._select_button.set_visible(False)

        self._play_icon.set_from_icon_name(
            'media-playback-start-symbolic', Gtk.IconSize.SMALL_TOOLBAR)

        self.props.coresong.bind_property(
            'selected', self._select_button, 'active',
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            'show-duration', self._duration_label, 'visible',
            GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            'show-favorite', self._star_eventbox, 'visible',
            GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            'show-song-number', self._number_label, 'visible',
            GObject.BindingFlags.SYNC_CREATE)
        self.props.coresong.bind_property(
            "favorite", self._star_image, "favorite",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self.props.coresong.bind_property(
            "state", self, "state",
            GObject.BindingFlags.SYNC_CREATE)
        self.props.coresong.connect(
            "notify::validation", self._on_validation_changed)

        if not self.props.coresong.props.is_tracker:
            self._star_stack.props.visible_child_name = "empty"

        if can_dnd is True:
            self._dnd_eventbox.props.visible = True
            self._drag_widget = None
            entries = [
                Gtk.TargetEntry.new(
                    "GTK_EVENT_BOX", Gtk.TargetFlags.SAME_APP, 0)
            ]
            self._dnd_eventbox.drag_source_set(
                Gdk.ModifierType.BUTTON1_MASK, entries,
                Gdk.DragAction.MOVE)
            self.drag_dest_set(
                Gtk.DestDefaults.ALL, entries, Gdk.DragAction.MOVE)

    @Gtk.Template.Callback()
    def _on_selection_changed(self, klass, value):
        self.emit('selection-changed')

    @Gtk.Template.Callback()
    def _on_drag_begin(self, klass, context):
        gdk_window = self.get_window()
        _, x, y, _ = gdk_window.get_device_position(context.get_device())
        allocation = self.get_allocation()

        self._drag_widget = Gtk.ListBox()
        self._drag_widget.set_size_request(allocation.width, allocation.height)

        drag_row = SongWidget(self.props.coresong)
        self._drag_widget.add(drag_row)
        self._drag_widget.drag_highlight_row(drag_row.get_parent())
        self._drag_widget.props.visible = True
        Gtk.drag_set_icon_widget(context, self._drag_widget, x, y)

    @Gtk.Template.Callback()
    def _on_drag_end(self, klass, context):
        self._drag_widget = None

    @Gtk.Template.Callback()
    def _on_drag_data_get(self, klass, context, selection_data, info, time_):
        row_position = self.get_parent().get_index()
        selection_data.set(
            Gdk.Atom.intern("row_position", False), 0,
            bytes(str(row_position), encoding="UTF8"))

    @Gtk.Template.Callback()
    def _on_drag_data_received(
            self, klass, context, x, y, selection_data, info, time_):
        source_position = int(str(selection_data.get_data(), "UTF-8"))
        target_position = self.get_parent().get_index()
        if source_position == target_position:
            return

        self.emit("widget-moved", source_position)

    @Gtk.Template.Callback()
    def _on_select_button_toggled(self, widget):
        # This property is used to ignore the second click event
        # (one event in SongWidget and the other one in select_button).
        self.props.select_click = not self.props.select_click

    @Gtk.Template.Callback()
    def _on_star_toggle(self, widget, event):
        (_, button) = event.get_button()
        if button != Gdk.BUTTON_PRIMARY:
            return False

        favorite = not self._star_image.favorite
        self._star_image.props.favorite = favorite

        return True

    @Gtk.Template.Callback()
    def _on_star_hover(self, widget, event):
        self._star_image.props.hover = True

    @Gtk.Template.Callback()
    def _on_star_unhover(self, widget, event):
        self._star_image.props.hover = False

    @GObject.Property(type=bool, default=False)
    def selection_mode(self):
        """Selection mode

        :returns: Selection mode
        :rtype: bool
        """
        return self._selection_mode

    @selection_mode.setter
    def selection_mode(self, value):
        """Set the selection mode

        :param bool value: Selection mode
        """
        if (not self.props.coresong.props.is_tracker
                and value):
            self.props.sensitive = False
            return

        self.props.sensitive = True

        self._selection_mode = value
        self._select_button.set_visible(value)

        if not value:
            self.props.selected = False

    @GObject.Property
    def state(self):
        """State of the widget

        :returns: Widget state
        :rtype: SongWidget.State
        """
        return self._state

    @state.setter
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
