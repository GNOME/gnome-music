# Copyright (c) 2013 Giovanni Campagna <scampa.giovanni@gmail.com>
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
from gi.repository import GLib, Notify

from gnomemusic import log


class NotificationManager:

    def __repr__(self):
        return '<NotificationManager>'

    @log
    def __init__(self, player):
        self._player = player

        self._notification = Notify.Notification()

        self._notification.set_category('x-gnome.music')
        self._notification.set_hint('action-icons', GLib.Variant('b', True))
        self._notification.set_hint('resident', GLib.Variant('b', True))
        self._notification.set_hint(
            'desktop-entry', GLib.Variant('s', 'gnome-music'))

    @log
    def _set_actions(self, playing):
        self._notification.clear_actions()

        if (Notify.VERSION_MINOR > 7
                or (Notify.VERSION_MINOR == 7 and Notify.VERSION_MICRO > 5)):
            self._notification.add_action(
                'media-skip-backward', _("Previous"), self._go_previous, None)
            if playing:
                self._notification.add_action(
                    'media-playback-pause', _("Pause"), self._pause, None)
            else:
                self._notification.add_action(
                    'media-playback-start', _("Play"), self._play, None)
            self._notification.add_action(
                'media-skip-forward', _("Next"), self._go_next, None)

    @log
    def _go_previous(self, notification, action, data):
        self._player.play_previous()

    @log
    def _go_next(self, notification, action, data):
        self._player.play_next()

    @log
    def _play(self, notification, action, data):
        self._player.play()

    @log
    def _pause(self, notification, action, data):
        self._player.pause()
