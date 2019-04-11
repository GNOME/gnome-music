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
from gi.repository import Gtk, GObject

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
    def __init__(self, application, player):
        """Initialize supend inhibitor

        :param Application application: Application object
        :param Player player: Player object
        """
        super().__init__()

        self._application = application
        self._player = player
        self._inhibit_cookie = 0

        self._player.connect('notify::state', self._on_player_state_changed)

        self._settings = self._application.props.settings
        self._should_inhibit = self._settings.get_boolean('inhibit-suspend')
        self._settings.connect(
            'changed::inhibit-suspend', self._on_inhibit_suspend_changed)

    @log
    def _inhibit_suspend(self):
        if (self._inhibit_cookie == 0
                and self._should_inhibit):
            active_window = self._application.props.active_window

            self._inhibit_cookie = self._application.inhibit(
                active_window, Gtk.ApplicationInhibitFlags.SUSPEND,
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
        self._on_player_state_changed(None, None)

    @log
    def _on_player_state_changed(self, klass, arguments):
        if (self._player.props.state == Playback.PLAYING
                or self._player.props.state == Playback.LOADING):
            self._inhibit_suspend()

        if (self._player.props.state == Playback.PAUSED
                or self._player.props.state == Playback.STOPPED):
            self._uninhibit_suspend()
