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

from __future__ import annotations
from typing import Optional
import typing
import weakref

import gi
gi.require_version("Grl", "0.3")
from gi.repository import GLib, GObject, Gio, Grl, Gtk

from gnomemusic.grilowrappers.localsearchwrapper import LocalSearchWrapper
from gnomemusic.storeart import StoreArt
from gnomemusic.trackerwrapper import TrackerState, TrackerWrapper
from gnomemusic.utils import CoreObjectType
if typing.TYPE_CHECKING:
    from gnomemusic.corealbum import CoreAlbum
    from gnomemusic.coreartist import CoreArtist
    from gnomemusic.coredisc import CoreDisc
    from gnomemusic.coresong import CoreSong


class CoreGrilo(GObject.GObject):

    _METADATA_THUMBNAIL_KEYS = [
        Grl.METADATA_KEY_ID,
        Grl.METADATA_KEY_THUMBNAIL
    ]

    _blocklist = [
        'grl-bookmarks',
        'grl-filesystem',
        'grl-itunes-podcast',
        "grl-local-metadata",
        'grl-metadata-store',
        'grl-podcasts'
    ]

    _grl_plugin_ranks = ("grl-musicbrainz-coverart:3,"
                         "grl-lastfm-cover:2,"
                         "grl-theaudiodb-cover:1")

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
        self._log = application.props.log
        self._thumbnail_sources = []
        self._thumbnail_sources_timeout = None
        self._wrappers = {}

        self._fast_options: Grl.OperationOptions = Grl.OperationOptions()
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self._tsparql_wrapper = TrackerWrapper(application)
        self._tsparql_wrapper.bind_property(
            "tracker-available", self, "tracker-available",
            GObject.BindingFlags.SYNC_CREATE)

        GLib.setenv("GRL_PLUGIN_RANKS", self._grl_plugin_ranks, True)

        Grl.init(None)

        self._registry = Grl.Registry.get_default()
        config = Grl.Config.new("grl-lua-factory", "grl-theaudiodb-cover")
        config.set_api_key(self._theaudiodb_api_key)
        self._registry.add_config(config)

        self._registry.connect('source-added', self._on_source_added)
        self._registry.connect('source-removed', self._on_source_removed)

        self._registry.load_all_plugins(False)

        tracker_available_state = self._tsparql_wrapper.props.tracker_available
        if tracker_available_state != TrackerState.AVAILABLE:
            self._tsparql_wrapper.connect(
                "notify::tracker-available",
                self._on_tracker_available_changed)
        else:
            self._on_tracker_available_changed(None, None)

        for plugin in self._registry.get_plugins(False):
            plugin_id = plugin.get_id()
            # Activate the Tracker plugin only when TrackerWrapper
            # is available by listening to the tracker-available
            # property, so skip it here.
            if plugin_id != "grl-tracker3":
                try:
                    self._registry.activate_plugin_by_id(plugin_id)
                except GLib.GError:
                    self._log.debug(
                        "Failed to activate {} plugin.".format(plugin_id))

        weakref.finalize(self, Grl.deinit)

    def _on_tracker_available_changed(
            self, trackerwrapper: TrackerWrapper, state: TrackerState) -> None:
        # FIXME:No removal support yet.
        new_state = self._tsparql_wrapper.props.tracker_available
        if new_state == TrackerState.AVAILABLE:
            wrapper = LocalSearchWrapper(
                self._application, self._tsparql_wrapper)
            self._wrappers["gnome-music"] = wrapper

    def _on_source_added(self, registry, source):

        def _trigger_art_update():
            self._thumbnail_sources_timeout = None
            if len(self._thumbnail_sources) > 0:
                self.props.cover_sources = True

            return GLib.SOURCE_REMOVE

        if ("net:plaintext" in source.get_tags()
                or source.props.source_id in self._blocklist):
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

    def _on_source_removed(self, registry, source):
        # FIXME: Handle removing sources.
        self._log.debug("Removed source {}".format(source.props.source_id))

    def get_artist_albums(
            self, coreartist: CoreArtist,
            filter_model: Gtk.FilterListModel) -> None:
        """Get all album by an artist

        :param CoreArtist coreart: An artist to look up
        :param Gtk.FilterListModel filter_model: The model to fill
        """
        source = "gnome-music"
        self._wrappers[source].get_artist_albums(coreartist, filter_model)

    def get_album_discs(
            self, corealbum: CoreAlbum, disc_model: Gio.ListStore) -> None:
        """Get all discs from an album

        :param CoreAlbum corealbum: An album
        :param Gtk.SortListModel disc_model: The model to fill
        """
        source = "gnome-music"
        self._wrappers[source].get_album_discs(corealbum, disc_model)

    def get_album_disc(
            self, coredisc: CoreDisc, model: Gtk.FilterListModel) -> None:
        """Get all songs from an album disc

        :param CoreDisc coredisc: An album disc to look up
        :param Gtk.FilterListModel model: The model to fill
        """
        source = "gnome-music"
        self._wrappers[source].get_album_disc(coredisc, model)

    def writeback_tracker(self, coresong: CoreSong, tag: str) -> None:
        """Use Tracker queries to update tags.

        The tags are associated with a Tracker resource
        (song, album, artist or external resource).

        :param CoreSong coresong: Song to update
        :param str tag: tag to update
        """
        self._tsparql_wrapper.update_tag(coresong, tag)

    def search(self, text: str) -> None:
        """Search for the given string in the wrappers

        If an empty string is provided, the wrapper should
        reset to an empty state.

        :param str text: The search string
        """
        for wrapper in self._wrappers.values():
            wrapper.search(text)

    def get_song_art(self, coresong: CoreSong) -> None:
        """Retrieve song art for the given CoreSong

        :param CoreSong coresong: CoreSong to retrieve art for
        """
        def _on_resolved(
                source: Grl.Source, op_id: int, media: Optional[Grl.Media],
                error: Optional[GLib.Error]) -> None:
            if error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                return

            if media is None:
                return

            StoreArt().start(
                coresong, media.get_thumbnail(), CoreObjectType.SONG)

        for source in self._thumbnail_sources:
            media = Grl.Media.audio_new()
            media.set_album(coresong.props.album)
            media.set_artist(coresong.props.artist)
            media.set_url(coresong.props.url)
            source.resolve(
                media, self._METADATA_THUMBNAIL_KEYS, self._fast_options,
                _on_resolved)

    def get_album_art(self, corealbum: CoreAlbum) -> None:
        """Retrieve album art for the given CoreAlbum

        :param CoreAlbum corealbum: CoreAlbum to retrieve art for
        """
        def _on_resolved(
                source: Grl.Source, op_id: int, media: Optional[Grl.Media],
                error: Optional[GLib.Error]) -> None:
            if error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                return

            if media is None:
                return

            StoreArt().start(
                corealbum, media.get_thumbnail(), CoreObjectType.ALBUM)

        for source in self._thumbnail_sources:
            # The grilo album field is used during resolve
            media = Grl.Media.audio_new()
            media.set_album(corealbum.props.title)
            media.set_artist(corealbum.props.artist)
            media.set_url(corealbum.props.url)
            source.resolve(
                media, self._METADATA_THUMBNAIL_KEYS, self._fast_options,
                _on_resolved)

    def get_artist_art(self, coreartist: CoreArtist) -> None:
        """Retrieve artist art for the given CoreArtist

        :param CoreArtist coreartist: CoreArtist to retrieve art for
        """
        def _on_resolved(
                source: Grl.Source, op_id: int, media: Optional[Grl.Media],
                error: Optional[GLib.Error]) -> None:
            if error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                return

            if media is None:
                return

            StoreArt().start(
                coreartist, media.get_thumbnail(), CoreObjectType.ARTIST)

        for source in self._thumbnail_sources:
            media = Grl.Media.audio_new()
            media.set_artist(coreartist.props.artist)
            source.resolve(
                media, self._METADATA_THUMBNAIL_KEYS, self._fast_options,
                _on_resolved)

    def stage_playlist_deletion(self, playlist):
        """Prepares playlist deletion.

        :param Playlist playlist: playlist
        """
        if "gnome-music" in self._wrappers:
            self._wrappers["gnome-music"].stage_playlist_deletion(
                playlist)

    def finish_playlist_deletion(self, playlist, deleted):
        """Finishes playlist deletion.

        :param Playlist playlist: playlist
        :param bool deleted: indicates if the playlist has been deleted
        """
        if "gnome-music" in self._wrappers:
            self._wrappers["gnome-music"].finish_playlist_deletion(
                playlist, deleted)

    def create_playlist(self, playlist_title, callback):
        """Creates a new user playlist.

        :param str playlist_title: playlist title
        :param callback: function to perform once, the playlist is created
        """
        if "gnome-music" in self._wrappers:
            self._wrappers["gnome-music"].create_playlist(
                playlist_title, callback)
