# Copyright 2018 The GNOME Music developers
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

from gi.repository import GObject, Grl

logger = logging.getLogger(__name__)


class GrlMusicbrainzWrapper(GObject.GObject):

    _acoustid_api_key = 'Nb8SVVtH1C'

    _needed_sources = [
        'grl-chromaprint',
        'grl-acoustid'
    ]

    ACOUSTID_METADATA_KEYS = [
        Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_MB_ARTIST_ID,
        Grl.METADATA_KEY_ALBUM_DISC_NUMBER,
        Grl.METADATA_KEY_ARTIST,
        Grl.METADATA_KEY_PUBLICATION_DATE,
        Grl.METADATA_KEY_MB_RELEASE_ID,
        Grl.METADATA_KEY_MB_RELEASE_GROUP_ID,
        Grl.METADATA_KEY_MB_RECORDING_ID,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_TRACK_NUMBER
    ]

    def __repr__(self):
        return '<GrlMusicbrainzWrapper>'

    def __init__(self, grilo):
        super().__init__()

        self._grilo = grilo
        self._grilo.connect('new-resolve-source-found', self._add_new_source)
        self._grilo.connect('new-query-source-found', self._add_new_source)

        config = Grl.Config.new('grl-lua-factory', 'grl-acoustid')
        config.set_api_key(self._acoustid_api_key)
        self._grilo._registry.add_config(config)

        self._fingerprint_key = Grl.METADATA_KEY_INVALID
        self._sources = {}

    def _add_new_source(self, klass, source):
        source_id = source.get_id()
        print("Add new source called with id", source_id)
        if source_id in self._needed_sources:
            self._sources[source_id] = source

        if source_id == 'grl-chromaprint':
            self._fingerprint_key = self._grilo._registry.lookup_metadata_key(
                'chromaprint')
            if self._fingerprint_key == Grl.METADATA_KEY_INVALID:
                logger.warning("Error, cannot retrieve fingerprint key")

    @GObject.Property(type=bool, default=False)
    def chromaprint_available(self):
        return ('grl-chromaprint' in self._sources.keys()
                and self._fingerprint_key != Grl.METADATA_KEY_INVALID)

    @GObject.Property(type=bool, default=False)
    def acoustid_available(self):
        return 'grl-acoustid' in self._sources.keys()

    @GObject.Property(type=bool, default=False)
    def available(self):
        return (self.props.chromaprint_available
                and self.props.acoustid_available)

    def _acoustid_resolved(self, source, op_id, media,
                           count, callback, error=None):
        if error:
            logger.warning("Error {}: {}".format(error.domain, error.message))
            return callback(None, 0)

        return callback(media, count)

    def _get_tags_from_acoustid(self, media, callback):
        if not self.acoustid_available:
            callback(None)
            return

        options = Grl.OperationOptions()
        options.set_resolution_flags(Grl.ResolutionFlags.NORMAL)

        query = 'duration=' + str(media.get_duration())
        query += '&fingerprint=' + media.get_string(self._fingerprint_key)

        self._sources['grl-acoustid'].query(
            query, self.ACOUSTID_METADATA_KEYS, options,
            self._acoustid_resolved, callback)

    def _chromaprint_resolved(
            self, source, op_id, media, callback, error=None):
        if error:
            logger.warning("Error {}: {}".format(error.domain, error.message))
            callback(None)
            return

        callback(media)

    def _get_song_chromaprint(self, media, callback):
        if self._fingerprint_key == Grl.METADATA_KEY_INVALID:
            callback(None)
            return

        chromaprint = media.get_string(self._fingerprint_key)
        if chromaprint is not None:
            callback(media)
            return

        if not self.props.chromaprint_available:
            callback(None)

        options = Grl.OperationOptions()
        options.set_resolution_flags(Grl.ResolutionFlags.FAST_ONLY
                                          | Grl.ResolutionFlags.IDLE_RELAY)

        keys = [self._fingerprint_key, Grl.METADATA_KEY_DURATION]
        self._sources['grl-chromaprint'].resolve(
            media, keys, options, self._chromaprint_resolved,
            callback)

    def get_song_tags(self, media, callback):
        def _fingerprint_finished(media):
            if not media:
                callback(None)
                return
            self._grilo.writeback(media, self._fingerprint_key)
            self._grilo.writeback(media, Grl.METADATA_KEY_DURATION)
            self._get_tags_from_acoustid(media, callback)

        self._get_song_chromaprint(media, _fingerprint_finished)
