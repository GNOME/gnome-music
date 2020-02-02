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

import gi
gi.require_version('Goa', '1.0')
gi.require_version('Soup', '2.4')
from gi.repository import GLib, Goa, GObject, Soup

from gnomemusic.musiclogger import MusicLogger
import gnomemusic.utils as utils


class GoaLastFM(GObject.GObject):
    """Last.fm account handling through GOA
    """

    class State(IntEnum):
        """GoaLastFM account State"""

        NOT_CONFIGURED = 0
        DISABLED = 1
        ENABLED = 2

    def __init__(self):
        super().__init__()

        self._log = MusicLogger()

        self._client = None
        self._reset_attributes()
        Goa.Client.new(None, self._new_client_callback)

    def _reset_attributes(self):
        self._account = None
        self._authentication = None
        self._state = GoaLastFM.State.NOT_CONFIGURED
        self._music_disabled_id = None
        self.notify("state")

    def _new_client_callback(self, source, result):
        try:
            self._client = source.new_finish(result)
        except GLib.Error as error:
            self._log.warning("Error: {}, {}".format(
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
            self._reset_attributes()

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
                "Error: Unable to retrieve last.fm session key", e.message)
            return None


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
        self._account_state = GoaLastFM.State.NOT_CONFIGURED

        self._goa_lastfm = GoaLastFM()
        self._goa_lastfm.bind_property(
            "state", self, "account-state", GObject.BindingFlags.SYNC_CREATE)

        self._soup_session = Soup.Session.new()
        self._scrobble_cache = []

    @GObject.Property(type=int, default=GoaLastFM.State.NOT_CONFIGURED)
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

    def _lastfm_api_call(self, media, time_stamp, request_type_key):
        """Internal method called by self.scrobble"""
        api_key = self._goa_lastfm.client_id
        sk = self._goa_lastfm.session_key
        if sk is None:
            self._log.warning(
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

    def _lastfm_api_callback(self, session, msg, request_type_key):
        """Internall callback method called by queue_message"""
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
        self.scrobbled = True

        if not self.props.can_scrobble:
            return

        media = coresong.props.media
        self._lastfm_api_call(media, time_stamp, "scrobble")

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
