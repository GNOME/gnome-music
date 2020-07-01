# Copyright 2019 The GNOME Music developers
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

import weakref

import gi
gi.require_version('Grl', '0.3')
from gi.repository import Grl, GLib, GObject

from gnomemusic.grilowrappers.grlacoustidwrapper import GrlAcoustIDWrapper
from gnomemusic.grilowrappers.grlchromaprintwrapper import (
    GrlChromaprintWrapper)
from gnomemusic.grilowrappers.grlsearchwrapper import GrlSearchWrapper
from gnomemusic.grilowrappers.grltrackerwrapper import GrlTrackerWrapper
from gnomemusic.trackerwrapper import TrackerState, TrackerWrapper


class CoreGrilo(GObject.GObject):

    _blacklist = [
        'grl-bookmarks',
        'grl-filesystem',
        'grl-itunes-podcast',
        'grl-metadata-store',
        'grl-podcasts',
        'grl-spotify-cover'
    ]

    _grl_plugin_ranks = ("grl-musicbrainz-coverart:3,"
                         "grl-lastfm-cover:2,"
                         "grl-theaudiodb-cover:1")

    _acoustid_api_key = "Nb8SVVtH1C"
    _theaudiodb_api_key = "195003"

    cover_sources = GObject.Property(type=bool, default=False)
    tracker_available = GObject.Property(type=int)

    def __init__(self, application):
        """Initiate the CoreGrilo object

        :param Application application: The Application instance to use
        """
        super().__init__()

        self._application = application
        self._coremodel = self._application.props.coremodel
        self._coreselection = application.props.coreselection
        self._log = application.props.log
        self._search_wrappers = {}
        self._thumbnail_sources = []
        self._thumbnail_sources_timeout = None
        self._wrappers = {}
        self._mb_wrappers = {}

        application_id = application.get_application_id()
        self._tracker_wrapper = TrackerWrapper(application_id)
        self._tracker_wrapper.bind_property(
            "tracker-available", self, "tracker-available",
            GObject.BindingFlags.SYNC_CREATE)

        self._tracker_wrapper.connect(
            "notify::tracker-available", self._on_tracker_available_changed)

        GLib.setenv("GRL_PLUGIN_RANKS", self._grl_plugin_ranks, True)

        Grl.init(None)

        self._registry = Grl.Registry.get_default()
        config = Grl.Config.new("grl-lua-factory", "grl-theaudiodb-cover")
        config.set_api_key(self._theaudiodb_api_key)
        self._registry.add_config(config)

        config = Grl.Config.new("grl-lua-factory", "grl-acoustid")
        config.set_api_key(self._acoustid_api_key)
        self._registry.add_config(config)

        config = Grl.Config.new("grl-tracker3", "grl-tracker3-source")
        config.set_string(
            "miner-service", self._tracker_wrapper.miner_fs_busname())
        config.set_string(
            "store-path", self._tracker_wrapper.cache_directory())
        self._registry.add_config(config)

        self._registry.connect('source-added', self._on_source_added)
        self._registry.connect('source-removed', self._on_source_removed)

        self._plugins_loaded = False

    def load_plugins(self):
        """Load all the plugins.

        This function can only be called once.
        """
        if self._plugins_loaded:
            self._log.warning("Grilo plugins have already been loaded")

        self._plugins_loaded = True
        self._registry.load_all_plugins(True)

        weakref.finalize(self, Grl.deinit)

    @GObject.Property(
        type=Grl.Registry, default=None, flags=GObject.ParamFlags.READABLE)
    def registry(self):
        """Get Grilo Registry.

        :returns: the Grilo Registry
        :rtype: Grl.Registry
        """
        return self._registry

    def _on_tracker_available_changed(self, klass, value):
        new_state = self._tracker_wrapper.props.tracker_available
        # FIXME:No removal support yet.
        if new_state == TrackerState.AVAILABLE:
            tracker_plugin = self._registry.lookup_plugin("grl-tracker3")
            if tracker_plugin:
                self._registry.unload_plugin("grl-tracker3")
            self._registry.activate_plugin_by_id("grl-tracker3")

    def _on_source_added(self, registry, source):

        def _trigger_art_update():
            self._thumbnail_sources_timeout = None
            if len(self._thumbnail_sources) > 0:
                self.props.cover_sources = True

            return GLib.SOURCE_REMOVE

        if ("net:plaintext" in source.get_tags()
                or source.props.source_id in self._blacklist):
            try:
                registry.unregister_source(source)
            except GLib.GError:
                self._log.warning(
                    "Failed to unregister {}".format(source.props.source_id))
            return

        if Grl.METADATA_KEY_THUMBNAIL in source.supported_keys():
            self._thumbnail_sources.append(source)
            if not self._thumbnail_sources_timeout:
                # Aggregate sources being added, for example when the
                # network comes online.
                self._thumbnail_sources_timeout = GLib.timeout_add_seconds(
                    5, _trigger_art_update)

        new_wrapper = None

        new_state = self._tracker_wrapper.props.tracker_available
        if (source.props.source_id == "grl-tracker3-source"
                and self._tracker_wrapper.location_filter() is not None
                and new_state == TrackerState.AVAILABLE):
            if source.props.source_id not in self._wrappers.keys():
                new_wrapper = GrlTrackerWrapper(
                    source, self._application, self._tracker_wrapper)
                self._wrappers[source.props.source_id] = new_wrapper
                self._log.debug("Adding wrapper {}".format(new_wrapper))
            else:
                grl_tracker_wrapper = self._wrappers[source.props.source_id]
                registry.unregister_source(grl_tracker_wrapper.props.source)
                grl_tracker_wrapper.props.source = source
        elif (source.props.source_id not in self._search_wrappers.keys()
                and source.props.source_id not in self._wrappers.keys()
                and source.props.source_id != "grl-tracker3-source"
                and source.get_supported_media() & Grl.MediaType.AUDIO
                and source.supported_operations() & Grl.SupportedOps.SEARCH
                and "net:internet" not in source.props.source_tags):
            self._search_wrappers[source.props.source_id] = GrlSearchWrapper(
                source, self._application)
            self._log.debug("Adding search source {}".format(source))
        elif (source.props.source_id == "grl-chromaprint"
                and source.props.source_id not in self._mb_wrappers.keys()):
            wrapper = GrlChromaprintWrapper(source, self._application)
            self._mb_wrappers[source.props.source_id] = wrapper
            self._log.debug("Adding wrapper {}".format(wrapper))
        elif (source.props.source_id == "grl-acoustid"
                and source.props.source_id not in self._mb_wrappers.keys()):
            wrapper = GrlAcoustIDWrapper(source, self._application)
            self._mb_wrappers[source.props.source_id] = wrapper
            self._log.debug("Adding wrapper {}".format(wrapper))

    def _on_source_removed(self, registry, source):
        # FIXME: Handle removing sources.
        self._log.debug("Removed source {}".format(source.props.source_id))

        # FIXME: Only removes search sources atm.
        self._search_wrappers.pop(source.props.source_id, None)

    def get_artist_albums(self, artist, filter_model):
        for wrapper in self._wrappers.values():
            wrapper.get_artist_albums(artist, filter_model)

    def get_album_discs(self, media, disc_model):
        for wrapper in self._wrappers.values():
            wrapper.get_album_discs(media, disc_model)

    def populate_album_disc_songs(self, media, discnr, callback):
        for wrapper in self._wrappers.values():
            wrapper.populate_album_disc_songs(media, discnr, callback)

    def writeback(self, media, keys, callback=None):
        """Store the values associated with the keys.

        :param Grl.Media media: A Grilo media item
        :param list keys: A list of Grilo metadata keys
        :param function callback: callback function
        """
        def _store_metadata_cb(source, media, failed_keys, data, error):
            if error is not None:
                self._log.warning(
                    "Error {}: {}".format(error.domain, error.message))
            if failed_keys:
                self._log.warning("Unable to update {}".format(failed_keys))
            if callback:
                callback()

        for wrapper in self._wrappers.values():
            if media.get_source() == wrapper.source.props.source_id:
                wrapper.props.source.store_metadata(
                    media, keys, Grl.WriteFlags.NORMAL, _store_metadata_cb,
                    None)
                break

    def writeback_tracker(self, media, tags):
        """Use Tracker queries to update tags.

        The tags are associated with a Tracker resource
        (song, album, artist or external resource), so they can cannot
        be updated with grilo writeback support.

        :param Grl.Media media: A Grilo media item
        :param deque tags: A list of tags to update
        """
        self._tracker_wrapper.update_tags(media, tags)

    def search(self, text):
        for wrapper in self._wrappers.values():
            wrapper.search(text)
        for wrapper in self._search_wrappers.values():
            wrapper.search(text)

    def get_album_art_for_item(self, coresong, callback):
        # Tracker not (yet) loaded.
        if "grl-tracker3-source" in self._wrappers:
            self._wrappers["grl-tracker3-source"].get_album_art_for_item(
                coresong, callback)

    def get_artist_art(self, coreartist):
        if "grl-tracker3-source" in self._wrappers:
            self._wrappers["grl-tracker3-source"].get_artist_art(coreartist)

    def stage_playlist_deletion(self, playlist):
        """Prepares playlist deletion.

        :param Playlist playlist: playlist
        """
        if "grl-tracker3-source" in self._wrappers:
            self._wrappers["grl-tracker3-source"].stage_playlist_deletion(
                playlist)

    def finish_playlist_deletion(self, playlist, deleted):
        """Finishes playlist deletion.

        :param Playlist playlist: playlist
        :param bool deleted: indicates if the playlist has been deleted
        """
        if "grl-tracker3-source" in self._wrappers:
            self._wrappers["grl-tracker3-source"].finish_playlist_deletion(
                playlist, deleted)

    def create_playlist(self, playlist_title, callback):
        """Creates a new user playlist.

        :param str playlist_title: playlist title
        :param callback: function to perform once, the playlist is created
        """
        if "grl-tracker3-source" in self._wrappers:
            self._wrappers["grl-tracker3-source"].create_playlist(
                playlist_title, callback)

    def get_chromaprint(self, coresong, callback):
        """Retrieve the chromaprint for the given CoreSong

        :param CoreSong coresong: The CoreSong to chromaprint
        :param callback: Metadata retrieval callback
        """
        if "grl-chromaprint" not in self._mb_wrappers:
            callback(None)
            return

        self._mb_wrappers["grl-chromaprint"].get_chromaprint(
            coresong, callback)

    def get_tags(self, coresong, callback):
        """Retrieve Musicbrainz tags for the given CoreSong

        :param CoreSong coresong: The CoreSong to retrieve tags for
        :param callback: Metadata retrieval callback
        """
        if "grl-acoustid" not in self._mb_wrappers:
            callback(None)
            return

        self._mb_wrappers["grl-acoustid"].get_tags(coresong, callback)
