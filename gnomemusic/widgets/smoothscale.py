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

import logging

from gi.repository import GLib, GObject, Gtk

from gnomemusic import log
from gnomemusic.gstplayer import Playback

logger = logging.getLogger(__name__)


class SmoothScale(Gtk.Scale):
    """Progressbar UI element

    The progressbar Gtk.Scale, extended with smoothing capabilities, so
    the indicator updates every pixel available.
    This class interacts directly with the GstPlayer class.
    """
    __gtype_name__ = 'SmoothScale'

    __gsignals__ = {
        'seek-finished': (
            GObject.SignalFlags.RUN_FIRST, None, (float,)
        ),
    }

    def __repr__(self):
        return '<SmoothScale>'

    @log
    def __init__(self):
        super().__init__()

        self._player = None
        self._old_smooth_scale_value = 0.0

        self._seek_timeout = None
        self._previous_state = None

        self._timeout = None

        self.connect('button-press-event', self._on_smooth_scale_event)
        self.connect(
            'button-release-event', self._on_smooth_scale_button_released)
        self.connect('change-value', self._on_smooth_scale_seek)

    # FIXME: This is a workaround for not being able to pass the player
    # object via init when using Gtk.Builder.
    @GObject.Property
    @log
    def player(self):
        """The GstPlayer object used

        :return: player object
        :rtype: GstPlayer
        """
        return self._player

    @player.setter
    @log
    def player(self, player):
        """Set the GstPlayer object used

        :param Player player: The GstPlayer to use
        """
        self._player = player

        self._player.connect('notify::state', self._on_state_change)
        self._player.connect('notify::duration', self._on_duration_changed)

    @log
    def _on_state_change(self, klass, arguments):
        state = self._player.state

        self._previous_state = state

        if state == Playback.STOPPED:
            self.set_value(0)
            self.set_sensitive(False)
        else:
            self.set_sensitive(True)

        if state == Playback.PLAYING:
            self._update_timeout()
        else:
            self._remove_timeout()

        return True

    @log
    def _on_duration_changed(self, klass, arguments):
        duration = self._player.duration

        if duration is not None:
            self.set_range(0.0, duration * 60)
            self.set_increments(300, 600)

    @log
    def _on_smooth_scale_seek_finish(self, value):
        """Prevent stutters when seeking with infinitesimal amounts"""
        self._seek_timeout = None
        round_digits = self.get_property('round-digits')
        if self._old_smooth_scale_value != round(value, round_digits):
            self._on_smooth_scale_change_value(self)
            self._old_smooth_scale_value = round(value, round_digits)

        self.emit('seek-finished', value)
        return False

    @log
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

    @log
    def _on_smooth_scale_button_released(self, scale, data):
        if self._seek_timeout:
            GLib.source_remove(self._seek_timeout)
            self._on_smooth_scale_seek_finish(
                self.get_value())

        self._update_position_callback()
        return False

    @log
    def _on_smooth_scale_event(self, scale, data):
        self._remove_timeout()
        self._old_smooth_scale_value = self.get_value()
        return False

    @log
    def _update_timeout(self):
        """Update the duration for self._timeout

        Sets the period of self._timeout to a value small enough to make
        the slider SmoothScale move smoothly based on the current song
        duration and scale length.
        """
        # Do not run until SmoothScale has been realized and GStreamer
        # provides a duration.
        duration = self._player.duration
        if (self.get_realized() is False
                or duration is None):
            return

        # Update self._timeout.
        width = self.get_allocated_width()
        padding = self.get_style_context().get_padding(
            Gtk.StateFlags.NORMAL)
        width -= padding.left + padding.right

        timeout_period = min(1000 * duration // width, 1000)

        if self._timeout:
            GLib.source_remove(self._timeout)
        self._timeout = GLib.timeout_add(
            timeout_period, self._update_position_callback)

    @log
    def _remove_timeout(self):
        if self._timeout:
            GLib.source_remove(self._timeout)
            self._timeout = None

    @log
    def _on_smooth_scale_change_value(self, scroll):
        seconds = scroll.get_value() / 60
        self._player.seek(seconds)

        return True

    @log
    def _update_position_callback(self):
        position = self._player.position
        if position > 0:
            self.set_value(position * 60)
        self._update_timeout()

        return False
