# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
# Copyright (c) 2013 Guillaume Quintard <guillaume.quintard@gmail.com>
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
gi.require_version('Grl', '0.2')
from gi.repository import GLib, GObject
from gnomemusic.query import Query
from gnomemusic import log, TrackerWrapper
import logging
import os
os.environ['GRL_PLUGIN_RANKS'] = 'local-metadata:3,filesystem:2,tracker:1,lastfm-albumart:0'
from gi.repository import Grl
logger = logging.getLogger(__name__)


class Grilo(GObject.GObject):

    __gsignals__ = {
        'ready': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'changes-pending': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'new-source-added': (GObject.SignalFlags.RUN_FIRST, None, (Grl.Source, ))
    }

    METADATA_KEYS = [
        Grl.METADATA_KEY_ID, Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_ARTIST, Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_DURATION,
        Grl.METADATA_KEY_CREATION_DATE,
        Grl.METADATA_KEY_URL,
        Grl.METADATA_KEY_LYRICS,
        Grl.METADATA_KEY_THUMBNAIL]

    METADATA_THUMBNAIL_KEYS = [
        Grl.METADATA_KEY_ID,
        Grl.METADATA_KEY_THUMBNAIL,
    ]

    CHANGED_MEDIA_MAX_ITEMS = 500
    CHANGED_MEDIA_SIGNAL_TIMEOUT = 2000

    @log
    def __init__(self):
        GObject.GObject.__init__(self)
        self.playlist_path = GLib.build_filenamev([GLib.get_user_data_dir(),
                                                  "gnome-music", "playlists"])
        if not (GLib.file_test(self.playlist_path, GLib.FileTest.IS_DIR)):
            GLib.mkdir_with_parents(self.playlist_path, int("0755", 8))
        self.options = Grl.OperationOptions()
        self.options.set_flags(Grl.ResolutionFlags.FAST_ONLY |
                               Grl.ResolutionFlags.IDLE_RELAY)

        self.full_options = Grl.OperationOptions()
        self.full_options.set_flags(Grl.ResolutionFlags.FULL |
                                    Grl.ResolutionFlags.IDLE_RELAY)

        self.sources = {}
        self.blacklist = ['grl-filesystem', 'grl-bookmarks', 'grl-metadata-store', 'grl-podcasts']
        self.tracker = None
        self.changed_media_ids = []
        self.pending_event_id = 0
        self.changes_pending = {'Albums': False, 'Artists': False, 'Songs': False}

        self.registry = Grl.Registry.get_default()

        self.sparqltracker = TrackerWrapper().tracker

    @log
    def _find_sources(self):
        self.registry.connect('source_added', self._on_source_added)
        self.registry.connect('source_removed', self._on_source_removed)

        try:
            self.registry.load_all_plugins()
        except GLib.GError:
            logger.error('Failed to load plugins.')
        if self.tracker is not None:
            logger.debug("tracker found")
            self.tracker.notify_change_start()
            self.notification_handler = self.tracker.connect(
                'content-changed', self._on_content_changed)

    @log
    def _on_content_changed(self, mediaSource, changedMedias, changeType, locationUnknown):
        try:
            with self.tracker.handler_block(self.notification_handler):
                for media in changedMedias:
                    media_id = media.get_id()
                    if changeType == Grl.SourceChangeType.ADDED:
                        # Check that this media is an audio file
                        query = "select DISTINCT rdf:type nie:mimeType(?urn) as mime-type" +\
                                " { ?urn rdf:type nie:InformationElement . FILTER (tracker:id(?urn) = %s) }" % media_id
                        mimeType = grilo.tracker.query_sync(query, [Grl.METADATA_KEY_MIME], grilo.options)[0].get_mime()
                        if mimeType and mimeType.startswith("audio"):
                            self.changed_media_ids.append(media_id)
                    if changeType == Grl.SourceChangeType.REMOVED:
                        # There is no way to check that removed item is a media
                        # so always do the refresh
                        # todo: remove one single url
                        try:
                            self.changed_media_ids.append(media.get_id())
                        except Exception as e:
                            logger.warn("Skipping %s", media)

                if self.changed_media_ids == []:
                    return
                self.changed_media_ids = list(set(self.changed_media_ids))
                logger.debug("Changed medias: %s", self.changed_media_ids)

                if len(self.changed_media_ids) >= self.CHANGED_MEDIA_MAX_ITEMS:
                    self.emit_change_signal()
                elif self.changed_media_ids != []:
                    if self.pending_event_id > 0:
                        GLib.Source.remove(self.pending_event_id)
                        self.pending_event_id = 0
                    self.pending_event_id = GLib.timeout_add(self.CHANGED_MEDIA_SIGNAL_TIMEOUT, self.emit_change_signal)
        except Exception as e:
            logger.warn("Exception in _on_content_changed: %s", e)

    @log
    def emit_change_signal(self):
        self.changed_media_ids = []
        self.pending_event_id = 0
        self.changes_pending['Albums'] = True
        self.changes_pending['Artists'] = True
        self.changes_pending['Songs'] = True
        self.emit('changes-pending')
        return False

    @log
    def _on_source_added(self, pluginRegistry, mediaSource):
        id = mediaSource.get_id()
        logger.debug("new grilo source %s was added", id)
        try:
            ops = mediaSource.supported_operations()

            if id == 'grl-tracker-source':
                if ops & Grl.SupportedOps.SEARCH:
                    logger.debug("found searchable tracker source")
                    self.sources[id] = mediaSource
                    self.tracker = mediaSource
                    self.search_source = mediaSource

                    if self.tracker is not None:
                        self.emit('ready')

            elif (id.startswith('grl-upnp')):
                logger.debug("found upnp source %s", id)
                self.sources[id] = mediaSource
                self.emit('new-source-added', mediaSource)

            elif (id not in self.blacklist) and (ops & Grl.SupportedOps.SEARCH) and \
                 (mediaSource.get_supported_media() & Grl.MediaType.AUDIO):
                logger.debug("source %s is searchable", id)
                self.sources[id] = mediaSource
                self.emit('new-source-added', mediaSource)

        except Exception as e:
            logger.debug("Source %s: exception %s", id, e)

    @log
    def _on_source_removed(self, pluginRegistry, mediaSource):
        pass

    @log
    def populate_artists(self, offset, callback, count=-1):
        self.populate_items(Query.all_artists(), offset, callback, count)

    @log
    def populate_albums(self, offset, callback, count=-1):
        self.populate_items(Query.all_albums(), offset, callback, count)

    @log
    def populate_songs(self, offset, callback, count=-1):
        self.populate_items(Query.all_songs(), offset, callback, count)

    @log
    def populate_playlists(self, offset, callback, count=-1):
        self.populate_items(Query.all_playlists(), offset, callback, count)

    @log
    def populate_album_songs(self, album, callback, count=-1):
        if album.get_source() == 'grl-tracker-source':
            self.populate_items(Query.album_songs(album.get_id()), 0, callback, count)
        else:
            source = self.sources[album.get_source()]
            length = len(album.tracks)
            for i, track in enumerate(album.tracks):
                callback(source, None, track, length - (i + 1), None)
            callback(source, None, None, 0, None)

    @log
    def populate_playlist_songs(self, playlist, callback, count=-1):
        self.populate_items(Query.playlist_songs(playlist.get_id()), 0, callback, count)

    @log
    def populate_custom_query(self, query, callback, count=-1, data=None):
        self.populate_items(query, 0, callback, count, data)

    @log
    def populate_items(self, query, offset, callback, count=-1, data=None):
        options = self.options.copy()
        options.set_skip(offset)
        if count != -1:
            options.set_count(count)

        def _callback(source, param, item, remaining, data, error):
            callback(source, param, item, remaining, data)
        self.tracker.query(query, self.METADATA_KEYS, options, _callback, data)

    @log
    def toggle_favorite(self, song_item):
        # TODO: change "bool(song_item.get_lyrics())" --> song_item.get_favourite() once query works properly
        # TODO: when .set/get_favourite work, set_favourite outside loop: item.set_favourite(!item.get_favourite())
        if bool(song_item.get_lyrics()):  # is favorite
            self.sparqltracker.update(Query.remove_favorite(song_item.get_url()), GLib.PRIORITY_DEFAULT, None)
            song_item.set_lyrics("")
        else:  # not favorite
            self.sparqltracker.update(Query.add_favorite(song_item.get_url()), GLib.PRIORITY_DEFAULT, None)
            song_item.set_lyrics("i'm truthy")

    @log
    def search(self, q, callback, data=None):
        options = self.options.copy()
        self._search_callback_counter = 0

        @log
        def _search_callback(source, param, item, remaining, data, error):
            callback(source, param, item, remaining, data)
            self._search_callback_counter += 1

        @log
        def _multiple_search_callback(source, param, item, remaining, data, error):
            callback(source, param, item, remaining, data)

        if self.search_source:
            if self.search_source.get_id().startswith('grl-upnp'):
                options.set_type_filter(Grl.TypeFilter.AUDIO)
            self.search_source.search(q, self.METADATA_KEYS, options,
                                      _search_callback, data)
        else:
            Grl.multiple_search([self.sources[key] for key in self.sources
                                 if key != 'grl-tracker-source'],
                                q, self.METADATA_KEYS, options,
                                _multiple_search_callback, data)

    @log
    def get_album_art_for_item(self, item, callback, data=None):
        item_id = item.get_id()

        query = None
        if isinstance(item, Grl.MediaAudio):
            query = Query.get_album_for_song_id(item_id)
        else:
            query = Query.get_album_for_album_id(item_id)

        options = self.full_options.copy()
        options.set_count(1)

        self.search_source.query(query, self.METADATA_THUMBNAIL_KEYS, options, callback, data)

    @log
    def get_playlist_with_id(self, playlist_id, callback):
        options = self.options.copy()
        query = Query.get_playlist_with_id(playlist_id)

        self.tracker.query(query, self.METADATA_KEYS, options, callback, None)

    @log
    def get_playlist_song_with_id(self, playlist_id, entry_id, callback):
        options = self.options.copy()
        query = Query.get_playlist_song_with_id(playlist_id, entry_id)

        self.tracker.query(query, self.METADATA_KEYS, options, callback, None)


Grl.init(None)

grilo = Grilo()
