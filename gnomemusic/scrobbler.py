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
from threading import Thread
import logging
import requests

import gi
gi.require_version('Goa', '1.0')
from gi.repository import GLib, Goa, GObject

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

        self._client = None
        self._account = None
        self._authentication = None
        self._disabled = True

        Goa.Client.new(None, self._new_client_callback)

    @log
    def _new_client_callback(self, source, result):
        try:
            self._client = source.new_finish(result)
        except GLib.Error as error:
            logger.warn("Error: {}, {}".format(
                Goa.Error(error.code), error.message))
            return

        self._client.connect('account-added', self._goa_account_mutation)
        self._client.connect('account-removed', self._goa_account_mutation)
        self._find_lastfm_account()

    @log
    def _goa_account_mutation(self, klass, args):
        self._find_lastfm_account()

    @log
    def _find_lastfm_account(self):
        accounts = self._client.get_accounts()

        for obj in accounts:
            account = obj.get_account()
            if account.props.provider_type == "lastfm":
                self._authentication = obj.get_oauth2_based()
                self._account = account
                self.disabled = self._account.props.music_disabled
                self._account.connect(
                    'notify::music-disabled', self._goa_music_disabled)
                break

    @log
    def _goa_music_disabled(self, klass, args):
        self.disabled = klass.props.music_disabled

    @GObject.Property
    @log
    def disabled(self):
        """Retrieve the disabled status for the Last.fm account

        :returns: The disabled status
        :rtype: bool
        """
        return self._disabled

    @disabled.setter
    @log
    def disabled(self, value):
        """Set the disabled status for the Last.fm account

        :param bool value: status
        """
        self._disabled = value

    @GObject.Property
    @log
    def secret(self):
        """Retrieve the Last.fm client secret"""
        return self._authentication.props.client_secret

    @GObject.Property
    @log
    def client_id(self):
        """Retrieve the Last.fm client id"""
        return self._authentication.props.client_id

    @GObject.Property
    @log
    def session_key(self):
        """Retrieve the Last.fm session key"""
        return self._authentication.call_get_access_token_sync(None)[0]


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

    @GObject.Property(type=bool, default=False)
    def scrobbled(self):
        """Bool indicating current scrobble status"""
        return self._scrobbled

    @scrobbled.setter
    def scrobbled(self, scrobbled):
        self._scrobbled = scrobbled

    @log
    def _scrobble(self, media, time_stamp):
        """Internal method called by self.scrobble"""
        api_key = self._goa_lastfm.client_id
        sk = self._goa_lastfm.session_key
        secret = self._goa_lastfm.secret

        artist = utils.get_artist_name(media)
        title = utils.get_media_title(media)

        # The album is optional. So only provide it when it is
        # available.
        album = media.get_album()

        request_dict = {}
        if album:
            sig = "album[0]{}".format(album)
            request_dict.update({
                "album[0]": album
            })

        sig += ("api_key{}artist[0]{}methodtrack.scrobblesk{}"
                "timestamp[0]{}track[0]{}{}").format(
                    api_key, artist, sk, time_stamp, title, secret)

        api_sig = md5(sig.encode()).hexdigest()
        request_dict.update({
            "api_key": api_key,
            "method": "track.scrobble",
            "artist[0]": artist,
            "track[0]": title,
            "timestamp[0]": time_stamp,
            "sk": sk,
            "api_sig": api_sig
        })

        try:
            r = requests.post(
                "https://ws.audioscrobbler.com/2.0/", request_dict)
            if r.status_code != 200:
                logger.warn(
                    "Failed to scrobble track: %s %s" %
                    (r.status_code, r.reason))
                logger.warn(r.text)
        except Exception as e:
            logger.warn(e)

    @log
    def scrobble(self, media, time_stamp):
        """Scrobble a song to Last.fm.

        If not connected to Last.fm nothing happens
        Creates a new thread to make the request

        :param media: Grilo media item
        :param time_stamp: song loaded time (epoch time)
        """
        self.scrobbled = True

        if self._goa_lastfm.disabled:
            return

        t = Thread(target=self._scrobble, args=(media, time_stamp))
        t.setDaemon(True)
        t.start()

    @log
    def _now_playing(self, media):
        """Internal method called by self.now_playing"""
        api_key = self._goa_lastfm.client_id
        sk = self._goa_lastfm.session_key
        secret = self._goa_lastfm.secret

        artist = utils.get_artist_name(media)
        title = utils.get_media_title(media)

        sig = ("api_key{}artist{}methodtrack.updateNowPlayingsk{}track"
               "{}{}").format(api_key, artist, sk, title, secret)

        api_sig = md5(sig.encode()).hexdigest()
        request_dict = {
            "api_key": api_key,
            "method": "track.updateNowPlaying",
            "artist": artist,
            "track": title,
            "sk": sk,
            "api_sig": api_sig
        }

        try:
            r = requests.post(
                "https://ws.audioscrobbler.com/2.0/", request_dict)
            if r.status_code != 200:
                logger.warn(
                    "Failed to update currently played track: %s %s" %
                    (r.status_code, r.reason))
                logger.warn(r.text)
        except Exception as e:
            logger.warn(e)

    @log
    def now_playing(self, media):
        """Set now playing song to Last.fm

        If not connected to Last.fm nothing happens
        Creates a new thread to make the request

        :param media: Grilo media item
        """
        self.scrobbled = False

        if self._goa_lastfm.disabled:
            return

        t = Thread(target=self._now_playing, args=(media,))
        t.setDaemon(True)
        t.start()
