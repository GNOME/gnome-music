# Copyright (c) 2018 The GNOME Music Developers
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

from gettext import gettext as _
from gi.repository import Gdk, GLib, GObject, Gtk

from gnomemusic import log
from gnomemusic.gstplayer import Playback

logger = logging.getLogger(__name__)


class SmoothScale(Gtk.Scale):
    """Smooth"""
    __gtype_name__ = 'SmoothScale'

    __gsignals__ = {
        'seek-finished': (
            GObject.SignalFlags.RUN_FIRST, None, (float,)
        ),
        'seconds-tick': (
            GObject.SignalFlags.RUN_FIRST, None, ()
        )
    }

    def __repr__(self):
        return '<SmoothScale>'

    @log
    def __init__(self): #, player):
        super().__init__()

        self._player = None #player
        self._old_progress_scale_value = 0.0
        self.set_increments(300, 600)
        self._seek_timeout = None
        self._previous_state = None

        self.timeout = None
        self._seconds_timeout = 0
        self._seconds_period = 0
        self.played_seconds = 0

        self.connect('button-press-event', self._on_progress_scale_event)
        self.connect('button-release-event', self._on_progress_scale_button_released)
        self.connect('change-value', self._on_progress_scale_seek)
        self._ps_draw = self.connect('draw', self._on_progress_scale_draw)

    @GObject.property
    @log
    def player(self):
        return self._player

    @player.setter
    @log
    def player(self, player):
        self._player = player

        self._player.connect('notify::state', self._on_state_change)

    @log
    def _on_state_change(self, klass, arguments):
        state = self._player.state

        if self._previous_state == state:
            return

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

    def _on_progress_scale_seek_finish(self, value):
        """Prevent stutters when seeking with infinitesimal amounts"""
        self._seek_timeout = None
        round_digits = self.get_property('round-digits')
        if self._old_progress_scale_value != round(value, round_digits):
            self._on_progress_scale_change_value(self)
            self._old_progress_scale_value = round(value, round_digits)

        self.emit('seek-finished', value)
        return False

    def _on_progress_scale_seek(self, scale, scroll_type, value):
        """Smooths out the seeking process

        Called every time progress scale is moved. Only after a seek
        has been stable for 100ms, play the song from its location.
        """
        if self._seek_timeout:
            GLib.source_remove(self._seek_timeout)

        Gtk.Range.do_change_value(scale, scroll_type, value)
        if scroll_type == Gtk.ScrollType.JUMP:
            self._seek_timeout = GLib.timeout_add(
                100, self._on_progress_scale_seek_finish, value)
        else:
            # Scroll with keys, hence no smoothing.
            self._on_progress_scale_seek_finish(value)
            self._update_position_callback()

        return True

    @log
    def _on_progress_scale_button_released(self, scale, data):
        if self._seek_timeout:
            GLib.source_remove(self._seek_timeout)
            self._on_progress_scale_seek_finish(
                self.get_value())

        self._update_position_callback()
        return False

    @log
    def _on_progress_scale_event(self, scale, data):
        self._remove_timeout()
        self._old_progress_scale_value = self.get_value()
        return False

    def _on_progress_scale_draw(self, cr, data):
        self._update_timeout()
        self.disconnect(self._ps_draw)
        return False

    def _update_timeout(self):
        """Update the duration for self.timeout & self._seconds_timeout

        Sets the period of self.timeout to a value small enough to make
        the slider of self._progress_scale move smoothly based on the
        current song duration and progress_scale length.
        self._seconds_timeout is always set to a fixed value, short
        enough to hide irregularities in GLib event timing from the
        user, for updating the _progress_time_label.
        """
        # Do not run until progress_scale has been realized and
        # gstreamer provides a duration.
        duration = self._player.duration
        if (self.get_realized() is False
                or duration is None):
            return

        # Update self.timeout.
        width = self.get_allocated_width()
        padding = self.get_style_context().get_padding(
            Gtk.StateFlags.NORMAL)
        width -= padding.left + padding.right

        timeout_period = min(1000 * duration // width, 1000)

        if self.timeout:
            GLib.source_remove(self.timeout)
        self.timeout = GLib.timeout_add(
            timeout_period, self._update_position_callback)

        # Update self._seconds_timeout.
        if not self._seconds_timeout:
            self._seconds_period = 1000
            self._seconds_timeout = GLib.timeout_add(
                self._seconds_period, self._update_seconds_callback)

    def _remove_timeout(self):
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None
        if self._seconds_timeout:
            GLib.source_remove(self._seconds_timeout)
            self._seconds_timeout = None

    def _progress_scale_zero(self):
        self.set_value(0)
        self._on_progress_value_changed(None)

    @log
    def _on_progress_scale_change_value(self, scroll):
        seconds = scroll.get_value() / 60
        self._player.seek(seconds)
#        try:
            # FIXME mpris
            # self.emit('seeked', seconds * 1000000)
#        except TypeError:
            # See https://bugzilla.gnome.org/show_bug.cgi?id=733095
#            pass

        return True

    @log
    def _update_position_callback(self):
        position = self._player.position
        if position > 0:
            self.set_value(position * 60)
        self._update_timeout()
        return False

    @log
    def _update_seconds_callback(self):
        self.emit('seconds-tick')
        return True

        position = self._player.position
        if position > 0:
            self.played_seconds += self._seconds_period / 1000
            try:
                percentage = self.played_seconds / self.duration
                if (not self._lastfm.scrobbled
                        and percentage > 0.4):
                    current_media = self.get_current_media()
                    if current_media:
                        # FIXME: we should not need to update static
                        # playlists here but removing it may introduce
                        # a bug. So, we keep it for the time being.
                        playlists.update_all_static_playlists()
                        grilo.bump_play_count(current_media)
                        grilo.set_last_played(current_media)
                        self._lastfm.scrobble(current_media, self._time_stamp)

            except Exception as e:
                logger.warn("Error: %s, %s", e.__class__, e)
        return True