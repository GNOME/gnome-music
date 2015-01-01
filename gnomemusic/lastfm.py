# Copyright (c) 2013 Nil Gradisnik <nil.gradisnik@gmail.com>
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

from gi.repository import GLib, Gio
from datetime import datetime

import subprocess
import json
import hashlib
import urllib.request

from gnomemusic import log
import logging
logger = logging.getLogger(__name__)

BASE_URL = 'http://ws.audioscrobbler.com/2.0/'
AUTH_URL = 'http://www.last.fm/api/auth/'

class LastFm:

    @log
    def __init__(self, key, secret):
        """
        Constructor expects API key and secret
        """

        self.api_key = key
        self.api_secret = secret

        self.settings = Gio.Settings.new('org.gnome.Music')

    @log
    def authenticate(self):
        """
        Authenticate last.fm desktop application flow
        http://www.last.fm/api/desktopauth
        """

        try:
            response = urllib.request.urlopen(BASE_URL+'?method=auth.getToken&api_key='+self.api_key+'&format=json')
        except urllib.error.HTTPError as e:
            logger.error('Error fetching token: '+e.code)
            return

        data = json.loads(response.read().decode('utf8'))
        token = data['token']

        # Open last.fm authentication page in system default web browser
        # TODO: calling 'xdg-open' subprocess. if there's a better way to do this, fix it
        subprocess.Popen(['xdg-open', AUTH_URL+'?api_key='+self.api_key+'&token='+token])
        
        params = {
            'method': 'auth.getSession',
            'api_key': self.api_key,
            'token': token
        }

        signature = get_signature(params, self.api_secret)
        url_params = get_url_params(params)

        # Start checking for session key
        GLib.timeout_add_seconds(5, self._check_session, url_params, signature)

    @log
    def nowPlaying(self, track, artist, album=None):
        """
        Send now playing track
        http://www.last.fm/api/show/track.updateNowPlaying
        """

        self._track('track.updateNowPlaying', track, artist, album)

    @log
    def scrobble(self, track, artist, album=None):
        """
        Scrobble a track
        http://www.last.fm/api/show/track.scrobble
        """

        self._track('track.scrobble', track, artist, album)

    @log
    def _track(self, method, track, artist, album):
        """
        Post track information to last.fm web service
        """

        params = {
            'method': method,
            'api_key': self.api_key,
            'sk': self.settings.get_string('lastfm-session')
        }
        params['track'] = track
        params['artist'] = artist

        if album:
            params['album'] = album
        if method == 'track.scrobble':
            params['timestamp'] = str(int(datetime.utcnow().timestamp()))

        # Create signature from parameters
        params['api_sig'] = get_signature(params, self.api_secret)
        
        url = urllib.request.Request(BASE_URL+'?format=json', urllib.parse.urlencode(params).encode('utf8'))
        try:
            response = urllib.request.urlopen(url)
        except urllib.error.HTTPError as e:
            logger.error('Error scrobblig a track: '+e.code)

    @log
    def _check_session(self, params, signature):
        """
        Check for session key periodically until response contains no error
        This means that the user has granted access to the application
        Store session key
        """

        try:
            response = urllib.request.urlopen(BASE_URL+'?'+params+'&api_sig='+signature+'&format=json')
        except urllib.error.HTTPError as e:
            logger.error('Error fetching session key: '+e.code)
            return False

        data = json.loads(response.read().decode('utf8'))
        
        if 'error' in data:
            return True

        self.settings.set_string('lastfm-session', data['session']['key'])

def get_signature(params, secret):
    """
    Create an MD5 hash signature from parameters sorted alphabetically
    """

    keys = list(params.keys())
    keys.sort()

    string = ''

    for name in keys:
        string += name
        string += params[name]
    
    string += secret

    return hashlib.md5(str(string).encode('utf-8')).hexdigest()
        
def get_url_params(params):
    """
    Construct URL parameters
    """

    string = ''

    for name in params:
        string += name if string is '' else '&'+name
        string += '='+params[name]

    return string
