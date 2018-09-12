# Copyright © 2018 The GNOME Music developers
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
from gi.repository import GLib, Gtk, Gio, GObject

from gnomemusic import log
from gnomemusic.gstplayer import Playback

logger = logging.getLogger(__name__)


class InhibitSuspend(GObject.GObject):
    """InhibitSuspend object

    Contains the logic to postpone automatic system suspend
    until the application has played all the songs in the playlist.
    """

    def __repr__(self):
        return '<InhibitSuspend>'

    @log
    def __init__(self, root_window, player):
        super().__init__()

        self._root_window = root_window
        self._application = root_window.get_application()
        self._player = player
        self._inhibit_cookie = 0

        self._player.connect(
            'playback-status-changed', self._on_playback_status_changed)

        self._settings = Gio.Settings.new('org.gnome.Music')
        self._should_inhibit = self._settings.get_boolean('inhibit-suspend')
        self._settings.connect(
            'changed::inhibit-suspend', self._on_inhibit_suspend_changed)

        self._init_pause_on_suspend()

    @log
    def _inhibit_suspend(self):
        if (self._inhibit_cookie == 0
                and self._should_inhibit):
            self._inhibit_cookie = self._application.inhibit(
                self._root_window, Gtk.ApplicationInhibitFlags.SUSPEND,
                _("Playing music"))

            if self._inhibit_cookie == 0:
                logger.warning("Unable to inhibit automatic system suspend")

    @log
    def _uninhibit_suspend(self):
        if self._inhibit_cookie != 0:
            self._application.uninhibit(self._inhibit_cookie)
            self._inhibit_cookie = 0

    @log
    def _on_inhibit_suspend_changed(self, settings, value):
        self._should_inhibit = value
        self._on_playback_status_changed(None)

    @log
    def _on_playback_status_changed(self, arguments):
        if (self._player.get_playback_status() == Playback.PLAYING
                or self._player.get_playback_status() == Playback.LOADING):
            self._inhibit_suspend()

        if (self._player.get_playback_status() == Playback.PAUSED
                or self._player.get_playback_status() == Playback.STOPPED):
            self._uninhibit_suspend()

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
                "Error: Failed to contact settings daemon:", e.message)
            return

        try:
            # If I set signal to "PrepareForSleep" here, I've got rutime error
            # So I decided to just use basic "g-signal"
            # Needs reviewing. Don't have good understanding of how it works.
            self._suspend_proxy.connect("g-signal", self._stop_playing)
        except GLib.Error as e:
            logger.warning(
                "Error: ", e.message)

    @log
    def _stop_playing(self, proxy, sender, signal, parameters):
        # logind has 8 signals. Check if this is one we need.
        # Also, there's actually 2 signals coming through this:
        # when PrepareForSleep sets to true, and when it sets to false.
        # We don't care about second one, cause music already was paused
        if signal == "PrepareForSleep":
            # Also, do I need to check player state?
            self._player.pause()
