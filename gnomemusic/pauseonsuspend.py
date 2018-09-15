# Copyright 2018 The GNOME Music developers
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
import os

from gi.repository import GLib, Gio, GObject

from gnomemusic import log
from gnomemusic.gstplayer import Playback

logger = logging.getLogger(__name__)


class PauseOnSuspend(GObject.GObject):
    """PauseOnSuspend object

    Contains logic to pause music on system suspend
    and inhibit suspend before pause.
    """

    def __repr__(self):
        return '<PauseOnSuspend>'

    @log
    def __init__(self, player):
        super().__init__()

        self._player = player
        self._init_pause_on_suspend()

        self._file_descriptor = -1
        self._previous_status = self._player.get_playback_status()
        self._player.connect(
            'playback-status-changed', self._on_playback_status_changed)

    @log
    def _on_playback_status_changed(self, arguments):
        new_status = self._player.get_playback_status()

        if self._previous_status != new_status:
            if (new_status == Playback.PLAYING
                    and self._file_descriptor == -1):
                self._take_lock()
            if self._previous_status == Playback.PLAYING:
                self._close_lock()

            self._previous_status = new_status

    @log
    def _take_lock(self):
        variant = GLib.Variant(
            "(ssss)",
            (
                "sleep",
                "GNOME Music",
                "GNOME Music needs to pause",
                "delay"
            )
        )

        self._suspend_proxy.call(
            "Inhibit", variant, Gio.DBusCallFlags.NONE,
            -1, None, self._on_inhibit)

    @log
    def _on_inhibit(self, proxy, task, data=None):
        try:
            var = self._suspend_proxy.call_with_unix_fd_list_finish(task)
            self._file_descriptor = var.out_fd_list.get(0)
        except GLib.Error as e:
            logger.warning(
                "Error: Failed to finish proxy call:", e.message)

    @log
    def _close_lock(self):
        if self._file_descriptor >= 0:
            os.close(self._file_descriptor)
            self._file_descriptor = -1

    @log
    def _init_pause_on_suspend(self):
        Gio.DBusProxy.new_for_bus(
            Gio.BusType.SYSTEM,
            Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES, None,
            "org.freedesktop.login1",
            "/org/freedesktop/login1",
            "org.freedesktop.login1.Manager", None,
            self._suspend_proxy_ready)

    @log
    def _suspend_proxy_ready(self, proxy, result, data=None):
        try:
            self._suspend_proxy = proxy.new_finish(result)
        except GLib.Error as e:
            logger.warning(
                "Error: Failed to contact logind daemon:", e.message)
            return
        self._suspend_proxy.connect("g-signal", self._pause_playing)

    @log
    def _pause_playing(self, proxy, sender, signal, parameters):
        if (signal == "PrepareForSleep"
                and self._player.props.playing):
            self._player.pause()
