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

from __future__ import annotations
from typing import Dict, Optional, Union, cast
from enum import IntEnum
from hashlib import md5

import gi
gi.require_version('Goa', '1.0')
gi.require_version("Soup", "3.0")
from gi.repository import Gio, GLib, Goa, GObject, Soup

from gnomemusic.musiclogger import MusicLogger


class GoaLastFM(GObject.GObject):
    """Last.fm account handling through GOA
    """

    class State(IntEnum):
        """GoaLastFM account State.

        NOT_AVAILABLE: GOA does not handle Last.fm accounts
        NOT_CONFIGURED: GOA handles Last.fm but no user account has
                        been configured
        DISABLED: a user account exists, but it is disabled
        ENABLED: a user account exists and is enabled
        """
        NOT_AVAILABLE = 0
        NOT_CONFIGURED = 1
        DISABLED = 2
        ENABLED = 3

    def __init__(self) -> None:
        """Initialize GoaLastFM
        """
        super().__init__()
        self._log = MusicLogger()

        self._client: Optional[Goa.Client] = None
        self._connection: Optional[Gio.DBusConnection] = None
        self._state = GoaLastFM.State.NOT_AVAILABLE
        self.notify("state")
        self._reset_attributes()
        Goa.Client.new(None, self._new_client_callback)

    def _reset_attributes(self):
        self._account = None
        self._authentication = None
        self._music_disabled_id = None

    def _new_client_callback(self, source, result):
        try:
            self._client = source.new_finish(result)
        except GLib.Error as error:
            self._log.warning("Error: {}, {}".format(
                error.code, error.message))
            return

        manager = self._client.get_manager()

        if manager is None:
            self._log.info("GNOME Online Accounts is unavailable")
            return

        try:
            manager.call_is_supported_provider(
                "lastfm", None, self._lastfm_is_supported_cb)
        except TypeError:
            self._log.warning("Error: Unable to check if last.fm is supported")

    def _lastfm_is_supported_cb(self, proxy, result):
        try:
            lastfm_supported = proxy.call_is_supported_provider_finish(result)
        except GLib.Error as e:
            self._log.warning(
                "Error: Unable to check if last.fm is supported: {}".format(
                    e.message))
            return

        if lastfm_supported is False:
            return

        self._state = GoaLastFM.State.NOT_CONFIGURED
        self.notify("state")
        self._client.connect("account-added", self._goa_account_added)
        self._client.connect("account-removed", self._goa_account_removed)
        self._find_lastfm_account()

    def _goa_account_added(self, client, obj):
        self._find_lastfm_account()

    def _goa_account_removed(self, client, obj):
        account = obj.get_account()
        if account.props.provider_type == "lastfm":
            self._account.disconnect(self._music_disabled_id)
            self._state = GoaLastFM.State.NOT_CONFIGURED
            self._reset_attributes()
            self.notify("state")

    def _find_lastfm_account(self):
        accounts = self._client.get_accounts()

        for obj in accounts:
            account = obj.get_account()
            if account.props.provider_type == "lastfm":
                self._authentication = obj.get_oauth2_based()
                self._account = account
                self._music_disabled_id = self._account.connect(
                    'notify::music-disabled', self._goa_music_disabled)
                self._goa_music_disabled(self._account)
                break

    def _goa_music_disabled(self, klass, args=None):
        if self._account.props.music_disabled is True:
            self._state = GoaLastFM.State.DISABLED
        else:
            self._state = GoaLastFM.State.ENABLED

        self.notify("state")

    @GObject.Property(type=int, default=0, flags=GObject.ParamFlags.READABLE)
    def state(self):
        """Retrieve the state for the Last.fm account

        :returns: The account state
        :rtype: GoaLastFM.State
        """
        return self._state

    def enable_music(self):
        """Enable music suport of the Last.fm account"""
        self._account.props.music_disabled = False

    @GObject.Property(type=str, default="", flags=GObject.ParamFlags.READABLE)
    def identity(self):
        """Get Last.fm account identity

        :returns: Last.fm account identity
        :rtype: str
        """
        return self._account.props.identity

    @GObject.Property
    def secret(self):
        """Retrieve the Last.fm client secret"""
        return self._authentication.props.client_secret

    @GObject.Property
    def client_id(self):
        """Retrieve the Last.fm client id"""
        return self._authentication.props.client_id

    @GObject.Property
    def session_key(self):
        """Retrieve the Last.fm session key"""
        try:
            return self._authentication.call_get_access_token_sync(None)[0]
        except GLib.Error as e:
            self._log.warning(
                "Error: Unable to retrieve last.fm session key: {}".format(
                    e.message))
            return None

    def configure(self) -> None:
        """Open the LastFM GOA Settings panel"""
        if self.props.state == GoaLastFM.State.NOT_AVAILABLE:
            self._log.warning("Error, cannot configure a Last.fm account.")
            return

        Gio.bus_get(Gio.BusType.SESSION, None, self._get_dbus_connection)

    def _get_dbus_connection(
            self, source: None, result: Gio.AsyncResult) -> None:
        try:
            self._connection = Gio.bus_get_finish(result)
        except GLib.Error as e:
            self._log.warning(
                "Error: Unable to get the DBus connection: {}".format(
                    e.message))
            return

        try:
            proxy = Gio.DBusProxy.new_sync(
                self._connection, Gio.DBusProxyFlags.DO_NOT_CONNECT_SIGNALS
                | Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES, None,
                "org.gnome.Settings", "/org/gnome/Settings", "org.gtk.Actions",
                None)
        except GLib.Error as e:
            self._log.warning(f"Unable to create proxy: {e.message}")
        else:
            self._activate_settings(proxy, True)

    def _activate_settings(
            self, settings_proxy: Gio.DBusProxy, try_fallback: bool) -> None:
        if self._state == GoaLastFM.State.NOT_CONFIGURED:
            params = [GLib.Variant("s", "add"), GLib.Variant("s", "lastfm")]
        else:
            params = [GLib.Variant("s", self._account.props.id)]

        args = GLib.Variant("(sav)", ("online-accounts", params))
        variant = GLib.Variant("(sava{sv})", ("launch-panel", [args], {}))
        settings_proxy.call(
            "Activate", variant, Gio.DBusCallFlags.NONE, -1, None,
            self._on_settings_activated, try_fallback)

    def _on_settings_activated(
            self, proxy: Gio.DBusProxy, result: Gio.AsyncResult,
            try_fallback: bool) -> None:
        try:
            proxy.call_finish(result)
        except GLib.Error as e:
            if try_fallback:
                proxy = Gio.DBusProxy.new_sync(
                    self._connection, Gio.DBusProxyFlags.DO_NOT_CONNECT_SIGNALS
                    | Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES, None,
                    "org.gnome.ControlCenter", "/org/gnome/ControlCenter",
                    "org.gtk.Actions", None)
                self._activate_settings(proxy, False)
            else:
                self._log.warning(
                    f"Error: Failed to activate Settings: {e.message}")


class LastFmScrobbler(GObject.GObject):
    """Scrobble songs to Last.fm"""

    def __init__(self, application):
        """Intialize LastFm Scrobbler

        :param Application application: Application object
        """
        super().__init__()

        self._log = application.props.log
        self._settings = application.props.settings
        self._report = self._settings.get_boolean("lastfm-report")

        self._scrobbled = False
        self._account_state = GoaLastFM.State.NOT_AVAILABLE

        self._goa_lastfm = GoaLastFM()
        self._goa_lastfm.bind_property(
            "state", self, "account-state", GObject.BindingFlags.SYNC_CREATE)

        self._soup_session = Soup.Session.new()
        self._scrobble_cache = []

    def configure(self):
        self._goa_lastfm.configure()

    @GObject.Property(type=str, default="", flags=GObject.ParamFlags.READABLE)
    def identity(self):
        """Get Last.fm account identity

        :returns: Last.fm account identity
        :rtype: str
        """
        return self._goa_lastfm.props.identity

    @GObject.Property(type=int, default=GoaLastFM.State.NOT_AVAILABLE)
    def account_state(self):
        """Get the Last.fm account state

        :returns: state of the Last.fm account
        :rtype: GoaLastFM.State
        """
        return self._account_state

    @account_state.setter  # type: ignore
    def account_state(self, value):
        """Set the Last.fm account state

        The account state depends on GoaLast.fm state property.
        :param GoaLastFM.State value: new state
        """
        self._account_state = value
        self.notify("can-scrobble")

    @GObject.Property(type=bool, default=False)
    def can_scrobble(self):
        """Get can scrobble status

        Music is reported to Last.fm if the "lastfm-report" setting is
        True and if a Goa Last.fm account is configured with music
        support enabled.

        :returns: True is music is reported to Last.fm
        :rtype: bool
        """
        return (self.props.account_state == GoaLastFM.State.ENABLED
                and self._report is True)

    @can_scrobble.setter  # type: ignore
    def can_scrobble(self, value):
        """Set the can_scrobble status

        If no account is configured, nothing happens.
        If the new value is True, "lastfm-report" is changed and music
        support in the Last.fm is enabled if necessary.
        If the new value is False, "lastfm-report" is changed but the
        Last.fm account is not changed.
        :param bool value: new value
        """
        if self.props.account_state == GoaLastFM.State.NOT_CONFIGURED:
            return

        if (value is True
                and self.props.account_state == GoaLastFM.State.DISABLED):
            self._goa_lastfm.enable_music()

        self._settings.set_boolean("lastfm-report", value)
        self._report = value

    @GObject.Property(type=bool, default=False)
    def scrobbled(self):
        """Bool indicating current scrobble status"""
        return self._scrobbled

    @scrobbled.setter  # type: ignore
    def scrobbled(self, scrobbled):
        self._scrobbled = scrobbled

    def _lastfm_api_call(self, coresong, time_stamp, request_type_key):
        """Internal method called by self.scrobble"""
        api_key = self._goa_lastfm.client_id
        sk = self._goa_lastfm.session_key
        if sk is None:
            self._log.warning(
                "Error: Unable to perform last.fm api call {}".format(
                    request_type_key))
            return
        secret = self._goa_lastfm.secret

        artist = coresong.props.artist
        title = coresong.props.title

        request_type = {
            "update now playing": "track.updateNowPlaying",
            "scrobble": "track.scrobble"
        }

        # The album is optional. So only provide it when it is
        # available.
        album = coresong.props.album

        request_dict = {}
        if (request_type_key == "scrobble"
                and time_stamp is not None):
            self._scrobble_cache.append({
                "artist": artist,
                "track": title,
                "album": album,
                "timestamp": time_stamp
            })

            for index, data in enumerate(self._scrobble_cache):
                request_dict.update({
                    "artist[{}]".format(index): data['artist'],
                    "track[{}]".format(index): data['track'],
                    "timestamp[{}]".format(index): str(data['timestamp']),
                })
                if album:
                    request_dict.update({
                        "album[{}]".format(index): data['album']
                    })
        else:
            if album:
                request_dict.update({
                    "album": album
                })

            if time_stamp is not None:
                request_dict.update({
                    "timestamp": str(time_stamp)
                })

            request_dict.update({
                "artist": artist,
                "track": title,
            })

        request_dict.update({
            "api_key": api_key,
            "method": request_type[request_type_key],
            "sk": sk,
        })

        sig = ""
        for key in sorted(request_dict):
            sig += key + request_dict[key]

        sig += secret

        api_sig = md5(sig.encode()).hexdigest()
        request_dict.update({
            "api_sig": api_sig
        })

        msg = Soup.Message.new_from_encoded_form(
            "POST", "https://ws.audioscrobbler.com/2.0/",
            Soup.form_encode_hash(request_dict))
        data = {
            "msg": msg,
            "request_type_key": request_type_key,
        }
        self._soup_session.send_async(
            msg, GLib.PRIORITY_DEFAULT, None, self._lastfm_api_callback, data)

    def _lastfm_api_callback(
            self, session: Soup.Session,
            result: Gio.AsyncResult,
            data: Dict[str, Union[str, Soup.Message]]) -> None:
        """Internal callback method called by queue_message"""
        msg = cast(Soup.Message, data["msg"])
        request_type_key = cast(str, data["request_type_key"])

        status_code = msg.props.status_code
        if status_code != 200:
            self._log.debug("Failed to {} track {} : {}".format(
                request_type_key, status_code, msg.props.reason_phrase))
            self._log.debug(msg.props.response_body.data)
        elif (status_code == 200
                and request_type_key == "scrobble"):
            self._scrobble_cache.clear()

    def scrobble(self, coresong, time_stamp):
        """Scrobble a song to Last.fm.

        If not connected to Last.fm nothing happens

        :param coresong: CoreSong to scrobble
        :param time_stamp: song loaded time (epoch time)
        """
        self.props.scrobbled = True

        if not self.props.can_scrobble:
            return

        self._lastfm_api_call(coresong, time_stamp, "scrobble")

    def now_playing(self, coresong):
        """Set now playing song to Last.fm

        If not connected to Last.fm nothing happens

        :param coresong: CoreSong to use for now playing
        """
        self.props.scrobbled = False

        if coresong is None:
            return

        if not self.props.can_scrobble:
            return

        self._lastfm_api_call(coresong, None, "update now playing")
