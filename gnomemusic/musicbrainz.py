# Copyright 2019 The GNOME Music Developers
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

import logging
from collections import Counter

from gi.repository import GObject, Grl

from gnomemusic import log
import gnomemusic.utils as utils

logger = logging.getLogger(__name__)


class MusicBrainzCoverArt(GObject.GObject):

    _sources = {}

    _required_sources = [
        'grl-acoustid',
        'grl-chromaprint',
        'grl-musicbrainz-coverart'
    ]

    _acoustid_api_key = 'Nb8SVVtH1C'
    _acoustid_keys = [
        Grl.METADATA_KEY_MB_ARTIST_ID,
        Grl.METADATA_KEY_ARTIST,
        Grl.METADATA_KEY_MB_ALBUM_ID,
        Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_MB_RECORDING_ID,
        Grl.METADATA_KEY_TITLE
    ]

    _fingerprint_key = Grl.METADATA_KEY_INVALID

    def __repr__(self):
        return '<MusicBrainzCoverArt>'

    def __init__(self, grilo):
        super().__init__()
        self._grilo = grilo
        self._grilo.connect('new-resolve-source-added', self._on_source_added)

        config = Grl.Config.new('grl-lua-factory', 'grl-acoustid')
        config.set_api_key(self._acoustid_api_key)
        self._grilo.registry.add_config(config)

        self._album_songs = {}
        self._queries_queue = utils.LookupQueue(1)
        self._network_queue = utils.LookupQueue(2)

    def _on_source_added(self, plugin_registry, media_source):
        id_ = media_source.get_id()
        if id_ in self._required_sources:
            self._sources[id_] = media_source

        if id_ == 'grl-chromaprint':
            self._fingerprint_key = self._grilo.registry.lookup_metadata_key(
                'chromaprint')

    @GObject.Property(type=bool, default=False)
    def loaded(self):
        return len(self._sources) == 3

    @log
    def _musicbrainz_callback(self, source, operation, media, album_id, error):
        self._network_queue.pop()
        callback = self._album_songs[album_id]['callback']
        self._album_songs.pop(album_id)
        self._queries_queue.pop()

        if error:
            logger.warning(
                "Error {}: {}".format(error.domain, error.message))
            return

        callback(source, None, media, 0, error)

    @log
    def _acoustid_resolved(self, source, operations, media, album_id, error):
        self._network_queue.pop()
        if error:
            logger.warning(
                "Error {}: {}".format(error.domain, error.message))
            for song in self._album_songs[album_id]['songs']:
                if song.get_id() == media.get_id():
                    self._album_songs[album_id]['songs'].remove(song)
                    break
            return

        release_group_key = self._grilo.registry.lookup_metadata_key(
            'mb-release-group-id')
        if release_group_key:
            release_group = media.get_string(release_group_key)
            self._album_songs[album_id]['release-group'].append(release_group)
        else:
            for song in self._album_songs[album_id]['songs']:
                if song.get_id() == media.get_id():
                    self._album_songs[album_id]['songs'].remove(song)
                    break

        nb_releases = len(self._album_songs[album_id]['release-group'])
        nb_songs = len(self._album_songs[album_id]['songs'])
        if nb_songs == 0:
            callback = self._album_songs[album_id]['callback']
            self._album_songs.pop(album_id)
            self._queries_queue.pop()
            callback(source, None, media, 0, "No thumbnail found")
            return
        if nb_releases == nb_songs:
            releases = self._album_songs[album_id]['release-group']
            most_common = Counter(releases).most_common(1)[0]
            new_media = Grl.Media.audio_new()
            new_media.set_string(Grl.METADATA_KEY_MB_ALBUM_ID, "")
            new_media.set_string(release_group_key, most_common[0])
            self._network_search(
                self._sources['grl-musicbrainz-coverart'].resolve, new_media,
                [Grl.METADATA_KEY_THUMBNAIL], self._grilo.options,
                self._musicbrainz_callback, album_id)

    @log
    def _resolve_acoustid(self, source, op_id, media, album_id, error=None):
        self._network_queue.pop()
        if error:
            logger.warning(
                "Error {}: {}".format(error.domain, error.message))
            for song in self._album_songs['songs']:
                if song.get_id() == media.get_id():
                    self._album_songs[album_id]['songs'].remove(song)
                    break
            return

        self._network_search(
            self._sources['grl-acoustid'].resolve, media, self._acoustid_keys,
            self._grilo.options, self._acoustid_resolved, album_id)

    @log
    def _populate_songs(self, source, param, item, remaining, album_id):
        if item:
            self._album_songs[album_id]['songs'].append(item)

        # compute each song chromaprint signature
        if remaining == 0:
            source = self._sources['grl-chromaprint']
            keys = [self._fingerprint_key, Grl.METADATA_KEY_DURATION]

            for item in self._album_songs[album_id]['songs']:
                self._network_search(
                    source.resolve, item, keys, self._grilo.options,
                    self._resolve_acoustid, album_id)

    @log
    def _network_search(self, function, *args):
        if self._network_queue.push(function, args):
            function(*args)

    @log
    def _start_search(self, item, callback):
        album_id = item.get_id()
        self._album_songs[album_id] = {
            'callback': callback,
            'release-group': [],
            'songs': [],
        }
        self._grilo.populate_album_songs(
            item, self._populate_songs, data=album_id)

    @log
    def get_album_art(self, item, callback):
        """Retrieve coverart from musicbrainz api.

        For each song of an album, get its release musicbrainz id (retrieve
        it if necessary). Download the coverart of the most proeminent release
        id.

        :param GrlMedia item: a song from the album
        :param callback: callback function once the thumbnail is retrieved
        """
        if self._queries_queue.push(
                self._start_search, (item, callback)):
            self._start_search(item, callback)
