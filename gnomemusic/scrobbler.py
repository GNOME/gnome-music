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

from hashlib import md5
import logging

import gi
gi.require_version('Goa', '1.0')
gi.require_version('Soup', '2.4')
from gi.repository import GLib, Goa, GObject, Soup

from gnomemusic import log
import gnomemusic.utils as utils

logger = logging.getLogger(__name__)


class GoaLastFM(GObject.GObject):
    """Last.fm account handling through GOA
    """

    def __repr__(self):
        return '<GoaLastFM>'

    @log
    def __init__(self):
        super().__init__()

        self._reset_attributes()
        Goa.Client.new(None, self._new_client_callback)

    def _reset_attributes(self):
        self._client = None
        self._account = None
        self._authentication = None
        self._disabled = True
        self._music_disabled_id = None

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
            self._reset_attributes()

    @log
    def _find_lastfm_account(self):
        accounts = self._client.get_accounts()

        for obj in accounts:
            account = obj.get_account()
            if account.props.provider_type == "lastfm":
                self._authentication = obj.get_oauth2_based()
                self._account = account
                self.disabled = self._account.props.music_disabled
                self._music_disabled_id = self._account.connect(
                    'notify::music-disabled', self._goa_music_disabled)
                break

    @log
    def _goa_music_disabled(self, klass, args):
        self.disabled = klass.props.music_disabled

    @GObject.Property(type=bool, default=True)
    def disabled(self):
        """Retrieve the disabled status for the Last.fm account

        :returns: The disabled status
        :rtype: bool
        """
        return self._disabled

    @disabled.setter
    def disabled(self, value):
        """Set the disabled status for the Last.fm account

        :param bool value: status
        """
        self._disabled = value

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


class LastFmScrobbler(GObject.GObject):
    """Scrobble songs to Last.fm"""

    def __repr__(self):
        return '<LastFmScrobbler>'

    @log
    def __init__(self):
        super().__init__()

        self._scrobbled = False
        self._authentication = None
        self._goa_lastfm = GoaLastFM()
        self._soup_session = Soup.Session.new()
        self.song_list = []

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
        if request_type_key == "scrobble":
            
            if time_stamp is not None:
                self.song_list.append({
                    "artist": artist,
                    "track": title,
                    "album": album,
                    "timestamp": time_stamp
                })
                index = 0
                for data in self.song_list:
                    request_dict.update({
                        "artist[{}]".format(index): data['artist'],
                        "track[{}]".format(index): data['track'],
                        "timestamp[{}]".format(index): str(data['timestamp']),
                    })
                    if album:
                        request_dict.update({
                            "album[{}]".format(index): data['album']
                        })
                    index = index + 1
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
        elif status_code == 200:
            if request_type_key == "scrobble":
                del self.song_list[0:len(self.song_list)]

    @log
    def scrobble(self, coresong, time_stamp):
        """Scrobble a song to Last.fm.

        If not connected to Last.fm nothing happens

        :param coresong: CoreSong to scrobble
        :param time_stamp: song loaded time (epoch time)
        """
        self.scrobbled = True

        if self._goa_lastfm.disabled:
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

        if self._goa_lastfm.disabled:
            return

        media = coresong.props.media
        self._lastfm_api_call(media, None, "update now playing")