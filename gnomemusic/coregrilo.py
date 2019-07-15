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

import gi
gi.require_version('Grl', '0.3')
from gi.repository import Grl, GLib, GObject

# from gnomemusic.grilowrappers.grldleynawrapper import GrlDLeynaWrapper
from gnomemusic.grilowrappers.grlsearchwrapper import GrlSearchWrapper
from gnomemusic.grilowrappers.grltrackerwrapper import GrlTrackerWrapper


class CoreGrilo(GObject.GObject):

    _blacklist = [
        'grl-bookmarks',
        'grl-filesystem',
        'grl-itunes-podcast',
        'grl-metadata-store',
        'grl-podcasts',
        'grl-spotify-cover'
    ]

    _theaudiodb_api_key = "195003"

    cover_sources = GObject.Property(type=bool, default=False)
    tracker_available = GObject.Property(type=bool, default=False)

    def __repr__(self):
        return "<CoreGrilo>"

    def __init__(self, coremodel, coreselection):
        super().__init__()

        self._coremodel = coremodel
        self._coreselection = coreselection
        self._search_wrappers = {}
        self._thumbnail_sources = []
        self._thumbnail_sources_timeout = None
        self._wrappers = {}

        Grl.init(None)

        self._registry = Grl.Registry.get_default()
        config = Grl.Config.new("grl-lua-factory", "grl-theaudiodb-cover")
        config.set_api_key(self._theaudiodb_api_key)
        self._registry.add_config(config)

        self._registry.connect('source-added', self._on_source_added)
        self._registry.connect('source-removed', self._on_source_removed)

        self._registry.load_all_plugins(True)

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
                print("Failed to unregister {}".format(
                    source.props.source_id))
            return

        if Grl.METADATA_KEY_THUMBNAIL in source.supported_keys():
            self._thumbnail_sources.append(source)
            if not self._thumbnail_sources_timeout:
                # Aggregate sources being added, for example when the
                # network comes online.
                self._thumbnail_sources_timeout = GLib.timeout_add_seconds(
                    5, _trigger_art_update)

        new_wrapper = None

        if (source.props.source_id == "grl-tracker-source"
                and source.props.source_id not in self._wrappers.keys()):
            new_wrapper = GrlTrackerWrapper(
                source, self._coremodel, self._coreselection, self)
            self._wrappers[source.props.source_id] = new_wrapper
            self.props.tracker_available = True
        # elif source.props.source_id[:10] == "grl-dleyna":
        #     new_wrapper = GrlDLeynaWrapper(
        #         source, self._coremodel, self._coreselection, self)
        #     self._wrappers.append(new_wrapper)
            print("wrapper", new_wrapper)
        elif (source.props.source_id not in self._search_wrappers.keys()
                and source.get_supported_media() & Grl.MediaType.AUDIO
                and source.supported_operations() & Grl.SupportedOps.SEARCH):
            self._search_wrappers[source.props.source_id] = GrlSearchWrapper(
                source, self._coremodel, self._coreselection, self)
            print("search source", source)

    def _on_source_removed(self, registry, source):
        # FIXME: Handle removing sources.
        print("removed,", source.props.source_id)

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

    def _store_metadata(self, source, media, key):
        """Convenience function to store metadata

        Wrap the metadata store call in a idle_add compatible form.
        :param source: A Grilo source object
        :param media: A Grilo media item
        :param key: A Grilo metadata key
        """
        # FIXME: Doing this async crashes.
        try:
            source.store_metadata_sync(
                media, [key], Grl.WriteFlags.NORMAL)
        except GLib.Error as error:
            # FIXME: Do not print.
            print("Error {}: {}".format(error.domain, error.message))

        return GLib.SOURCE_REMOVE

    def writeback(self, media, key):
        for wrapper in self._wrappers.values():
            if media.get_source() == wrapper.source.props.source_id:
                GLib.idle_add(
                    self._store_metadata, wrapper.props.source, media, key)
                break

    def search(self, text):
        for wrapper in self._wrappers.values():
            wrapper.search(text)
        for wrapper in self._search_wrappers.values():
            wrapper.search(text)

    def get_album_art_for_item(self, coresong, callback):
        # Tracker not (yet) loaded.
        if "grl-tracker-source" not in self._wrappers:
            self._wrappers["grl-tracker-source"].get_album_art_for_item(
                coresong, callback)

    def stage_playlist_deletion(self, playlist):
        """Prepares playlist deletion.

        :param Playlist playlist: playlist
        """
        for wrapper in self._wrappers:
            if wrapper.source.props.source_id == "grl-tracker-source":
                wrapper.stage_playlist_deletion(playlist)
                break

    def finish_playlist_deletion(self, playlist, deleted):
        """Finishes playlist deletion.

        :param Playlist playlist: playlist
        :param bool deleted: indicates if the playlist has been deleted
        """
        for wrapper in self._wrappers:
            if wrapper.source.props.source_id == "grl-tracker-source":
                wrapper.finish_playlist_deletion(playlist, deleted)
                break

    def create_playlist(self, playlist_title, callback):
        """Creates a new user playlist.

        :param str playlist_title: playlist title
        :param callback: function to perform once, the playlist is created
        """
        for wrapper in self._wrappers:
            if wrapper.source.props.source_id == "grl-tracker-source":
                wrapper.create_playlist(playlist_title, callback)
                break
