# Copyright (c) 2015 Nil Gradisnik <nil.gradisnik@gmail.com>
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

TRACK_PLAYING = 'track.updateNowPlaying'
TRACK_SCROBBLE = 'track.scrobble'

class LastFm:

    @log
    def __init__(self, app, key, secret):
        """
        Constructor expects application instance, last.fm API key and secret

        In order to scrobble, a track needs to meet certain criteria
        http://www.last.fm/api/scrobbling
            - The track must be longer than 30 seconds.
            - And the track has been played for at least half its duration,
              or for 4 minutes (whichever occurs earlier.)
        """

        self.app = app
        self.player = app.get_active_window().player

        self.api_key = key
        self.api_secret = secret

        self.settings = Gio.Settings.new('org.gnome.Music')

        self.scrobble_timeout_id = 0

        self.player.connect('lastfm-scrobble', self._on_started_playing)

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
        self._check_session_count = 0
        GLib.timeout_add_seconds(5, self._check_session, url_params, signature)

    @log
    def publish(self, method, data, timestamp=None):
        """
        Publish track information to last.fm service.

        method = 'updateNowPlaying' send now playing track
        http://www.last.fm/api/show/track.updateNowPlaying

        method = 'scrobble' scrobble a track
        http://www.last.fm/api/show/track.scrobble
        """

        params = {
            'method': method,
            'api_key': self.api_key,
            'sk': self.settings.get_string('lastfm-session')
        }
        params.update(data)

        if method == TRACK_SCROBBLE:
            params['timestamp'] = timestamp

        # Create signature from parameters
        params['api_sig'] = get_signature(params, self.api_secret)
        
        url = urllib.request.Request(BASE_URL+'?format=json', urllib.parse.urlencode(params).encode('utf8'))
        try:
            response = urllib.request.urlopen(url)
        except urllib.error.HTTPError as e:
            logger.error('Error scrobblig a track: '+e.code)

        data = json.loads(response.read().decode('utf8'))
        if 'error' in data:
            logger.error('Publish '+method+': '+data['message'])

    @log
    def _check_session(self, params, signature):
        """
        Check for session key periodically until response contains no error
        This means that the user has granted access to the application
        Store session key
        """

        self._check_session_count += 1
        if (self._check_session_count > 10):
            logger.error('Authentication timeout checking session key.')
            return False

        try:
            response = urllib.request.urlopen(BASE_URL+'?'+params+'&api_sig='+signature+'&format=json')
        except urllib.error.HTTPError as e:
            logger.error('Authentication error fetching session key: '+e.code)
            return False

        data = json.loads(response.read().decode('utf8'))
        
        if 'error' in data:
            return True

        self.settings.set_string('lastfm-session', data['session']['key'])

    @log
    def _on_started_playing(self, player, data):
        """
        Track started playing signal
        Publish now playing and wait half of duration time to scrobble
        """

        if not (self.settings.get_string('lastfm-session')):
            logger.error('Trying to scrobble when no session key exists.')
            return

        self.publish(TRACK_PLAYING, data)

        timeout = int(player.duration/2)
        timestamp = str(int(datetime.now().timestamp()))

        if (self.scrobble_timeout_id != 0):
            GLib.source_remove(self.scrobble_timeout_id)
        self.scrobble_timeout_id = GLib.timeout_add_seconds(timeout, self._on_scrobble, data, timestamp)

    @log
    def _on_scrobble(self, data, timestamp):
        self.scrobble_timeout_id = 0

        self.publish(TRACK_SCROBBLE, data, timestamp)

        return False

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

    return hashlib.md5(string.encode('utf-8')).hexdigest()
        
def get_url_params(params):
    """
    Construct URL parameters
    """

    string = ''

    for name in params:
        string += name if string is '' else '&'+name
        string += '='+params[name]

    return string
