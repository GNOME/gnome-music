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

from gi.repository import GLib, GObject, Gtk

from gnomemusic.gstplayer import Playback


class SmoothScale(Gtk.Scale):
    """Progressbar UI element

    The progressbar Gtk.Scale, extended with smoothing capabilities, so
    the indicator updates every pixel available.
    """
    __gtype_name__ = 'SmoothScale'

    def __init__(self):
        super().__init__()

        self._player = None
        self._old_smooth_scale_value = 0.0

        self._seek_timeout = None
        self._previous_state = None

        self._timeout = None

        ctrl = Gtk.GestureClick()
        ctrl.connect("pressed", self._on_button_pressed)
        ctrl.connect("released", self._on_button_released)
        self.add_controller(ctrl)

        self.connect('change-value', self._on_smooth_scale_seek)

    # FIXME: This is a workaround for not being able to pass the player
    # object via init when using Gtk.Builder.
    @GObject.Property
    def player(self):
        """The Player object used

        :return: player object
        :rtype: Player
        """
        return self._player

    @player.setter  # type: ignore
    def player(self, player):
        """Set the Player object used

        :param Player player: The Player to use
        """
        if (player is None
                or (self._player is not None
                    and self._player != player)):
            return

        self._player = player

        self._player.connect('notify::state', self._on_state_change)
        self._player.connect('notify::duration', self._on_duration_changed)

    def _on_state_change(self, klass, arguments):
        state = self._player.props.state

        self._previous_state = state

        if (state == Playback.STOPPED
                or state == Playback.LOADING):
            self.set_value(0)
            self.props.sensitive = False
        else:
            self.props.sensitive = True

        if state == Playback.PLAYING:
            self._update_position_callback()
        else:
            self._remove_timeout()

        return True

    def _on_duration_changed(self, klass, arguments):
        duration = self._player.props.duration

        if duration != -1.:
            self.set_value(0)
            self.set_range(0.0, duration * 60)
            self.set_increments(300, 600)

    def _on_smooth_scale_seek_finish(self, value):
        """Prevent stutters when seeking with infinitesimal amounts"""
        self._seek_timeout = None
        round_digits = self.props.round_digits
        if self._old_smooth_scale_value != round(value, round_digits):
            self._on_smooth_scale_change_value(self)
            self._old_smooth_scale_value = round(value, round_digits)

        return False

    def _on_smooth_scale_seek(self, scale, scroll_type, value):
        """Smooths out the seeking process

        Called every time progress scale is moved. Only after a seek
        has been stable for 100ms, play the song from its location.
        """
        if self._seek_timeout:
            GLib.source_remove(self._seek_timeout)

        Gtk.Range.do_change_value(scale, scroll_type, value)
        if scroll_type == Gtk.ScrollType.JUMP:
            self._seek_timeout = GLib.timeout_add(
                100, self._on_smooth_scale_seek_finish, value)
        else:
            # Scroll with keys, hence no smoothing.
            self._on_smooth_scale_seek_finish(value)
            self._update_position_callback()

        return True

    def _on_button_released(self, gesture, n_press, x, y):
        if self._seek_timeout:
            GLib.source_remove(self._seek_timeout)
            self._on_smooth_scale_seek_finish(
                self.get_value())

        self._update_position_callback()

        return False

    def _on_button_pressed(self, gesture, n_press, x, y):
        self._remove_timeout()
        self._old_smooth_scale_value = self.get_value()

        return False

    def _update_timeout(self):
        """Update the duration for self._timeout

        Sets the period of self._timeout to a value small enough to make
        the slider SmoothScale move smoothly based on the current song
        duration and scale length.
        """
        duration = abs(self._player.props.duration)

        style_context = self.get_style_context()
        width = self.get_allocated_width()
        padding = style_context.get_padding()
        width = max(width - (padding.left + padding.right), 1)

        timeout_period = min(1000 * duration // width, 200)

        if self._timeout:
            GLib.source_remove(self._timeout)
        self._timeout = GLib.timeout_add(
            timeout_period, self._update_position_callback)

    def _remove_timeout(self):
        if self._timeout:
            GLib.source_remove(self._timeout)
            self._timeout = None

    def _on_smooth_scale_change_value(self, scroll):
        seconds = scroll.get_value() / 60
        self._player.set_position(seconds)

        return True

    def _update_position_callback(self):
        position = self._player.get_position()
        if position > 0:
            self.set_value(position * 60)
        self._update_timeout()

        return False
