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

from gi.repository import Grl, GLib, GObject
from gnomemusic.query import Query
from gnomemusic import log
import logging
logger = logging.getLogger(__name__)


class Grilo(GObject.GObject):

    __gsignals__ = {
        'ready': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'changes-pending': (GObject.SIGNAL_RUN_FIRST, None, ())
    }

    METADATA_KEYS = [
        Grl.METADATA_KEY_ID, Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_ARTIST, Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_DURATION,
        Grl.METADATA_KEY_CREATION_DATE]

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
        self.options.set_flags(Grl.ResolutionFlags.FULL |
                               Grl.ResolutionFlags.IDLE_RELAY)

        self.sources = {}
        self.tracker = None
        self.changed_media_ids = []
        self.pending_event_id = 0
        self.changes_pending = {'Albums': False, 'Artists': False, 'Songs': False}
        self.registry = Grl.Registry.get_default()

        self.registry = Grl.Registry.get_default()
        self.registry.connect('source_added', self._on_source_added)
        self.registry.connect('source_removed', self._on_source_removed)

        try:
            self.registry.load_all_plugins()
        except GLib.GError:
            logger.error('Failed to load plugins.')
        if self.tracker is not None:
            logger.debug("tracker found")

    @log
    def _on_content_changed(self, mediaSource, changedMedias, changeType, locationUnknown):
        try:
            for media in changedMedias:
                media_id = media.get_id()
                if changeType == Grl.SourceChangeType.ADDED:
                    # Check that this media is an audio file
                    query = "select DISTINCT rdf:type nie:mimeType(?urn) as mime-type" +\
                            " { ?urn rdf:type nie:InformationElement . FILTER (tracker:id(?urn) = %s) }" % media_id
                    mimeType = grilo.tracker.query_sync(query, [Grl.METADATA_KEY_MIME], grilo.options)[0].get_mime()
                    if mimeType.startswith("audio"):
                        self.changed_media_ids.append(media_id)
                if changeType == Grl.SourceChangeType.REMOVED:
                    # There is no way to check that removed item is a media
                    # so always do the refresh
                    # todo: remove one single url
                    self.changed_media_ids.append(media.get_id())

            if len(self.changed_media_ids) >= self.CHANGED_MEDIA_MAX_ITEMS:
                self.emit_change_signal()
            elif self.changed_media_ids != []:
                if self.pending_event_id > 0:
                    GLib.Source.remove(self.pending_event_id)
                    self.pending_event_id = 0
                self.pending_event_id = GLib.timeout_add(self.CHANGED_MEDIA_SIGNAL_TIMEOUT, self.emit_change_signal)
        except Exception as e:
            logger.warn("Exception in _on_content_changed: %s" % e)

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
        logger.debug("new grilo source %s was added" % id)
        try:
            if id == 'grl-tracker-source':
                ops = mediaSource.supported_operations()
                if ops & Grl.SupportedOps.SEARCH:
                    print('Detected new source available: \'%s\' and it supports search' %
                          mediaSource.get_name())

                    self.sources[id] = mediaSource
                    self.tracker = mediaSource

                    if self.tracker is not None:
                        self.emit('ready')
                        self.tracker.notify_change_start()
                        self.tracker.connect('content-changed', self._on_content_changed)
        except Exception as e:
            logger.debug("Source %s: exception %s" % (id, e))

    @log
    def _on_source_removed(self, pluginRegistry, mediaSource):
        pass

    @log
    def populate_artists(self, offset, callback, count=-1):
        self.populate_items(Query.get_artists(), offset, callback, count)

    @log
    def populate_albums(self, offset, callback, count=50):
        self.populate_items(Query.get_all_albums(), offset, callback, count)

    @log
    def populate_songs(self, offset, callback, count=-1):
        self.populate_items(Query.get_songs(), offset, callback, count)

    @log
    def populate_album_songs(self, album_id, callback, count=-1):
        self.populate_items(Query.album_songs(album_id), 0, callback, count)

    @log
    def populate_items(self, query, offset, callback, count=50):
        options = self.options.copy()
        options.set_skip(offset)
        if count != -1:
            options.set_count(count)

        def _callback(source, param, item, count, data, offset):
            callback(source, param, item, count)
        self.tracker.query(query, self.METADATA_KEYS, options, _callback, None)

    @log
    def _search_callback(self):
        pass

    @log
    def search(self, q):
        options = self.options.copy()
        for source in self.sources:
            logger.debug(source.get_name() + ' - ' + q)
            source.search(q, [Grl.METADATA_KEY_ID], 0, 10,
                          options, self._search_callback, source)

    @log
    def get_album_art_for_album_id(self, album_id, _callback):
        options = self.options.copy()
        query = Query.get_album_for_id(album_id)
        self.tracker.query(query, self.METADATA_THUMBNAIL_KEYS, options, _callback, None)

    @log
    def get_media_from_uri(self, uri, callback):
        options = self.options.copy()
        query = Query.get_song_with_url(uri)

        def _callback(source, param, item, count, data, error):
            if not error:
                callback(source, param, item)
                return

        self.tracker.query(query, self.METADATA_KEYS, options, _callback, None)

Grl.init(None)

grilo = Grilo()
