# Copyright 2020 The GNOME Music Developers
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

from gi.repository import Gtk

from gnomemusic.scrobbler import GoaLastFM


@Gtk.Template(resource_path="/org/gnome/Music/ui/LastfmDialog.ui")
class LastfmDialog(Gtk.Dialog):
    """Dialog to configure a Last.fm account"""

    __gtype_name__ = "LastfmDialog"

    _action_button = Gtk.Template.Child()
    _action_button_gesture = Gtk.Template.Child()
    _action_label = Gtk.Template.Child()
    _status_label = Gtk.Template.Child()

    def __init__(self, parent, lastfm_scrobbler):
        super().__init__()

        self.props.transient_for = parent
        self._lastfm_scrobbler = lastfm_scrobbler
        self._lastfm_scrobbler.connect(
            "notify::account-state", self._on_account_state_changed)
        self._update_view()

    def _on_account_state_changed(self, klass, value):
        self._update_view()

    def _update_view(self):
        account_state = self._lastfm_scrobbler.props.account_state
        if account_state == GoaLastFM.State.NOT_CONFIGURED:
            self._status_label.props.label = _("Music Reporting Not Setup")
            self._action_button.props.label = _("Login")
            self._action_label.props.label = _(
                "Login to your Last.fm account to report your music listening.")  # noqa: E501
            return

        if self._lastfm_scrobbler.can_scrobble is True:
            action = _("Your music listening is reported to Last.fm.")
        else:
            action = _("Your music listening is not reported to Last.fm.")

        identity = self._lastfm_scrobbler.props.identity
        # TRANSLATORS: displays the username of the Last.fm account
        self._status_label.props.label = _("Logged in as {}").format(identity)
        self._action_button.props.label = _("Configure")
        self._action_label.props.label = action

    @Gtk.Template.Callback()
    def _on_action_button_clicked(self, widget, n_press, x, y):
        self._lastfm_scrobbler.configure()
