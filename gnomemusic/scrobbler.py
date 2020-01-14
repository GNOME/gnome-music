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

from enum import IntEnum
from hashlib import md5
import logging

import gi
gi.require_versions({"Goa": "1.0", "GoaBackend": "1.0", "Soup": "2.4"})
from gi.repository import Gio, GLib, Goa, GoaBackend, GObject, Soup

from gnomemusic import log
import gnomemusic.utils as utils


logger = logging.getLogger(__name__)


class GoaLastFM(GObject.GObject):
    """Last.fm account handling through GOA
    """

    class State(IntEnum):
        """GoaLastFM account State"""

        NOT_ENABLED = 0
        NOT_CONFIGURED = 1
        DISABLED = 2
        ENABLED = 3

    def __repr__(self):
        return '<GoaLastFM>'

    @log
    def __init__(self):
        super().__init__()

        self._client = None
        self._state = GoaLastFM.State.NOT_ENABLED
        self._reset_attributes()
        GoaBackend.Provider.get_all(self._get_all_providers_cb, None)

    def _reset_attributes(self):
        self._account = None
        self._authentication = None
        self._music_disabled_id = None

    def _get_all_providers_cb(self, source, result, data):
        try:
            retrieved, providers = GoaBackend.Provider.get_all_finish(result)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(
                Goa.Error(error.code), error.message))
            return

        if retrieved is False:
            logger.warning("Unable to get the list of GoaProvider.")
            return

        for provider in providers:
            if provider.get_provider_name() == "Last.fm":
                self._state = GoaLastFM.State.NOT_CONFIGURED
                Goa.Client.new(None, self._new_client_callback)
                self.notify("state")
                break

    @log
    def _new_client_callback(self, source, result):
        try:
            self._client = source.new_finish(result)
        except GLib.Error as error:
            logger.warning("Error: {}, {}".format(
                Goa.Error(error.code), error.message))
            return

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

    @log
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

    @log
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
            logger.warning(
                "Error: Unable to retrieve last.fm session key", e.message)
            return None

    def configure(self):
        if self.props.state == GoaLastFM.State.NOT_ENABLED:
            logger.warning("Error, cannot configure a Last.fm account.")
            return

        Gio.bus_get(Gio.BusType.SESSION, None, self._get_connection_db, None)

    def _get_connection_db(self, source, res, user_data=None):
        try:
            connection = Gio.bus_get_finish(res)
        except GLib.Error as e:
            logger.warning(
                "Error: Unable to get the DBus connection:", e.message)
            return

        Gio.DBusProxy.new(
            connection, Gio.DBusProxyFlags.NONE, None,
            "org.gnome.ControlCenter", "/org/gnome/ControlCenter",
            "org.gtk.Actions", None, self._get_control_center_proxy_cb, None)

    def _get_control_center_proxy_cb(self, source, res, user_data=None):
        try:
            settings_proxy = Gio.DBusProxy.new_finish(res)
        except GLib.Error as e:
            logger.warning(
                "Error: Unable to get a proxy:", e.message)
            return

        if self._state == GoaLastFM.State.NOT_CONFIGURED:
            params = [GLib.Variant("s", "add"), GLib.Variant("s", "lastfm")]
        else:
            params = [GLib.Variant("s", self._account.props.id)]

        args = GLib.Variant("(sav)", ("online-accounts", params))
        variant = GLib.Variant("(sava{sv})", ("launch-panel", [args], {}))
        settings_proxy.call(
            "Activate", variant, Gio.DBusCallFlags.NONE, -1, None,
            self._on_control_center_activated)

    def _on_control_center_activated(self, proxy, res, user_data=None):
        try:
            proxy.call_finish(res)
        except GLib.Error as e:
            logger.warning(
                "Error: Failed to activate control-center: {}".format(
                    e.message))


class LastFmScrobbler(GObject.GObject):
    """Scrobble songs to Last.fm"""

    def __repr__(self):
        return '<LastFmScrobbler>'

    @log
    def __init__(self, application):
        """Intialize LastFm Scrobbler

        :param Application application: Application object
        """
        super().__init__()

        self._settings = application.props.settings
        self._report = self._settings.get_boolean("lastfm-report")

        self._scrobbled = False
        self._account_state = GoaLastFM.State.NOT_ENABLED

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

    @GObject.Property(type=int, default=GoaLastFM.State.NOT_ENABLED)
    def account_state(self):
        """Get the Last.fm account state

        :returns: state of the Last.fm account
        :rtype: GoaLastFM.State
        """
        return self._account_state

    @account_state.setter
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

    @can_scrobble.setter
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

    @scrobbled.setter
    def scrobbled(self, scrobbled):
        self._scrobbled = scrobbled

    @log
    def _lastfm_api_call(self, media, time_stamp, request_type_key):
        """Internal method called by self.scrobble"""
        api_key = self._goa_lastfm.client_id
        sk = self._goa_lastfm.session_key
        if sk is None:
            logger.warning(
                "Error: Unable to perform last.fm api call", request_type_key)
            return
        secret = self._goa_lastfm.secret

        artist = utils.get_artist_name(media)
        title = utils.get_media_title(media)

        request_type = {
            "update now playing": "track.updateNowPlaying",
            "scrobble": "track.scrobble"
        }

        # The album is optional. So only provide it when it is
        # available.
        album = media.get_album()

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

        msg = Soup.form_request_new_from_hash(
            "POST", "https://ws.audioscrobbler.com/2.0/", request_dict)
        self._soup_session.queue_message(
            msg, self._lastfm_api_callback, request_type_key)

    @log
    def _lastfm_api_callback(self, session, msg, request_type_key):
        """Internall callback method called by queue_message"""
        status_code = msg.props.status_code
        if status_code != 200:
            logger.warning("Failed to {} track {} : {}".format(
                request_type_key, status_code, msg.props.reason_phrase))
            logger.warning(msg.props.response_body.data)
        elif (status_code == 200
                and request_type_key == "scrobble"):
            self._scrobble_cache.clear()

    @log
    def scrobble(self, coresong, time_stamp):
        """Scrobble a song to Last.fm.

        If not connected to Last.fm nothing happens

        :param coresong: CoreSong to scrobble
        :param time_stamp: song loaded time (epoch time)
        """
        self.scrobbled = True

        if not self.props.can_scrobble:
            return

        media = coresong.props.media
        self._lastfm_api_call(media, time_stamp, "scrobble")

    @log
    def now_playing(self, coresong):
        """Set now playing song to Last.fm

        If not connected to Last.fm nothing happens

        :param coresong: CoreSong to use for now playing
        """
        self.scrobbled = False

        if not self.props.can_scrobble:
            return

        media = coresong.props.media
        self._lastfm_api_call(media, None, "update now playing")
