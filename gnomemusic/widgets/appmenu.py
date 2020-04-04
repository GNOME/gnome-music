# Copyright 2018 The GNOME Music developers
#
# GNOME Music is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
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

from gi.repository import Gtk, Gio

from gnomemusic.scrobbler import GoaLastFM


@Gtk.Template(resource_path="/org/gnome/Music/ui/AppMenu.ui")
class AppMenu(Gtk.PopoverMenu):
    """AppMenu shown from the HeaderBar within the main view"""

    __gtype_name__ = "AppMenu"

    _lastfm_box = Gtk.Template.Child()
    _lastfm_switch = Gtk.Template.Child()
    _coverart_switch = Gtk.Template.Child()

    def __init__(self, application):
        """Initialize the application menu

        :param Application application: Application object
        """
        super().__init__()

        self._lastfm_switcher_id = None

        self._lastfm_configure_action = application.lookup_action(
            "lastfm-configure")

        self._lastfm_scrobbler = application.props.lastfm_scrobbler
        self._lastfm_scrobbler.connect(
            "notify::can-scrobble", self._on_scrobbler_state_changed)
        self._on_scrobbler_state_changed(None, None)
        self._coverart_switch.connect("state-set", self._on_coverart_toggle)

    def _on_scrobbler_state_changed(self, klass, args):
        state = self._lastfm_scrobbler.props.account_state
        if state == GoaLastFM.State.NOT_AVAILABLE:
            self._lastfm_configure_action.props.enabled = False
            return

        self._lastfm_configure_action.props.enabled = True

        if state == GoaLastFM.State.NOT_CONFIGURED:
            self._lastfm_box.props.visible = False
            if self._lastfm_switcher_id is not None:
                self._lastfm_switch.disconnect(self._lastfm_switcher_id)
                self._lastfm_switcher_id = None
            return

        self._lastfm_box.props.visible = True
        if self._lastfm_switcher_id is None:
            self._lastfm_switcher_id = self._lastfm_switch.connect(
                "state-set", self._on_lastfm_switch_active)

        with self._lastfm_switch.handler_block(self._lastfm_switcher_id):
            can_scrobble = self._lastfm_scrobbler.props.can_scrobble
            self._lastfm_switch.props.state = can_scrobble

    def _on_lastfm_switch_active(self, klass, state):
        self._lastfm_scrobbler.props.can_scrobble = state

    def _on_coverart_toggle(self, klass, state):
        Gio.Settings.new('org.gnome.Music').set_boolean('coverart-option',
							state)
