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

import gi

from hashlib import md5
import logging
import requests
from threading import Thread

from gnomemusic import log
import gnomemusic.utils as utils


logger = logging.getLogger(__name__)


class LastFmScrobbler():
    """Scrobble songs to Last.fm"""

    def __repr__(self):
        return '<LastFmScrobbler>'

    @log
    def __init__(self):
        self._authentication = None
        self._connect()

    def _connect(self):
        """Connect to Last.fm using gnome-online-accounts"""
        try:
            gi.require_version('Goa', '1.0')
            from gi.repository import Goa
            client = Goa.Client.new_sync(None)
            accounts = client.get_accounts()

            for obj in accounts:
                account = obj.get_account()
                if account.props.provider_name == "Last.fm":
                    self._authentication = obj.get_oauth2_based()
                    return
        except Exception as e:
            logger.info("Error reading Last.fm credentials: %s" % str(e))

    @log
    def _scrobble(self, media, time_stamp):
        """Internal method called by self.scrobble"""
        if self._authentication is None:
            return

        api_key = self._authentication.props.client_id
        sk = self._authentication.call_get_access_token_sync(None)[0]
        secret = self._authentication.props.client_secret

        artist = utils.get_artist_name(media)
        title = utils.get_media_title(media)

        sig = ("api_key{}artist[0]{}methodtrack.scrobblesk{}timestamp[0]"
               "{}track[0]{}{}").format(
                   api_key, artist, sk, time_stamp, title, secret)

        api_sig = md5(sig.encode()).hexdigest()
        request_dict = {
            "api_key": api_key,
            "method": "track.scrobble",
            "artist[0]": artist,
            "track[0]": title,
            "timestamp[0]": time_stamp,
            "sk": sk,
            "api_sig": api_sig
        }

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
        if self._authentication is None:
            return

        t = Thread(target=self._scrobble, args=(media, time_stamp))
        t.setDaemon(True)
        t.start()

    @log
    def _now_playing(self, media):
        """Internal method called by self.now_playing"""
        api_key = self._authentication.props.client_id
        sk = self._authentication.call_get_access_token_sync(None)[0]
        secret = self._authentication.props.client_secret

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
        if self._authentication is None:
            return

        t = Thread(target=self._now_playing, args=(media,))
        t.setDaemon(True)
        t.start()
