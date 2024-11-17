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
from collections.abc import Callable
from typing import Optional

import time

from gettext import gettext as _

import gi
gi.require_versions({"Grl": "0.3", "Tracker": "3.0"})
from gi.repository import Gio, Grl, Gtk, GLib, GObject, Tracker

from gnomemusic.coresong import CoreSong
import gnomemusic.utils as utils


class GrlTrackerPlaylists(GObject.GObject):

    __gtype_name__ = "GrlTrackerPlaylists"

    def __init__(self, source, application, tracker_wrapper, songs_hash):
        """Initialize GrlTrackerPlaylists.

        :param Grl.TrackerSource source: The Tracker source to wrap
        :param Application application: Application instance
        :param TrackerWrapper tracker_wrapper: The TrackerWrapper
                                               instance
        :param dict songs_hash: The songs hash table
        """
        super().__init__()

        self._application = application
        self._coremodel = application.props.coremodel
        self._log = application.props.log
        self._source = source
        self._model = self._coremodel.props.playlists
        self._model_filter = self._coremodel.props.playlists_filter
        self._user_model_filter = self._coremodel.props.user_playlists_filter
        self._pls_todelete = []
        self._songs_hash = songs_hash
        self._tracker = tracker_wrapper.props.local_db
        self._tracker_wrapper = tracker_wrapper
        self._notificationmanager = application.props.notificationmanager
        self._window = application.props.window

        user_playlists_filter = Gtk.CustomFilter()
        user_playlists_filter.set_filter_func(self._user_playlists_filter)
        self._user_model_filter.set_filter(user_playlists_filter)

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self._pl_create_stmt = self._tracker.load_statement_from_gresource(
            "/org/gnome/Music/queries/playlist_create.rq")
        self._pl_delete_stmt = self._tracker.load_statement_from_gresource(
            "/org/gnome/Music/queries/playlist_delete.rq")
        self._pl_query_all_stmt = self._tracker.load_statement_from_gresource(
            "/org/gnome/Music/queries/playlist_query_all.rq")

        self._initial_playlists_fill()

    def _initial_playlists_fill(self):
        args = {
            "source": self._source,
            "application": self._application,
            "tracker_wrapper": self._tracker_wrapper,
            "songs_hash": self._songs_hash
        }

        smart_playlists = {
            "MostPlayed": MostPlayed(**args),
            "NeverPlayed": NeverPlayed(**args),
            "RecentlyPlayed": RecentlyPlayed(**args),
            "RecentlyAdded": RecentlyAdded(**args),
            "Favorites": Favorites(**args),
            "InsufficientTagged": InsufficientTagged(**args),
            "AllSongs": AllSongs(**args),
        }

        for playlist in smart_playlists.values():
            self._model.append(playlist)

        def _cursor_next_async(
                cursor: Tracker.SparqlCursor, result: Gio.AsyncResult) -> None:
            try:
                has_next = cursor.next_finish(result)
            except GLib.Error as error:
                cursor.close()
                self._log.warning(f"Cursor iteration error: {error.message}")
                return

            if not has_next:
                cursor.close()
                return

            media = utils.create_grilo_media_from_cursor(
                cursor, Grl.MediaType.CONTAINER)
            self._add_user_playlist(media)

            cursor.next_async(None, _cursor_next_async)

        def _execute_async(
                stmt: Tracker.SparqlStatment, result: Gio.AsyncResult) -> None:
            try:
                cursor = stmt.execute_finish(result)
            except GLib.Error as error:
                cursor.close()
                self._log.warning(f"Playlist add cursor fail: {error.message}")
                return

            cursor.next_async(None, _cursor_next_async)

        self._pl_query_all_stmt.execute_async(None, _execute_async)

    def _add_user_playlist(
            self, media: Grl.Media,
            callback: Optional[Callable] = None) -> None:
        playlist = Playlist(
            media=media, source=self._source, application=self._application,
            tracker_wrapper=self._tracker_wrapper, songs_hash=self._songs_hash)
        self._model.append(playlist)

        if callback is not None:
            callback(playlist)

    def _playlists_filter(self, playlist):
        return playlist not in self._pls_todelete

    def _user_playlists_filter(self, playlist):
        return (playlist not in self._pls_todelete
                and playlist.props.is_smart is False)

    def stage_playlist_deletion(self, playlist):
        """Adds playlist to the list of playlists to delete

        :param Playlist playlist: playlist
        """
        self._pls_todelete.append(playlist)
        playlists_filter = Gtk.CustomFilter()
        playlists_filter.set_filter_func(self._playlists_filter)
        self._model_filter.set_filter(playlists_filter)

    def finish_playlist_deletion(
            self, playlist: Playlist, deleted: bool) -> None:
        """Removes playlist from the list of playlists to delete

        :param Playlist playlist: playlist
        :param bool deleted: indicates if the playlist has been deleted
        """
        playlists_filter = Gtk.CustomFilter()
        playlists_filter.set_filter_func(self._playlists_filter)
        user_playlists_filter = Gtk.CustomFilter()
        user_playlists_filter.set_filter_func(self._playlists_filter)

        self._pls_todelete.remove(playlist)
        if deleted is False:
            self._model_filter.set_filter(playlists_filter)
            self._user_model_filter.set_filter(user_playlists_filter)
            return

        def _delete_cb(
                stmt: Tracker.SparqlStatement,
                result: Gio.AsyncResult) -> None:
            try:
                stmt.update_finish(result)
            except GLib.Error as error:
                self._log.warning(
                    f"Unable to delete playlist {playlist.props.title}:"
                    f" {error.message}")
            else:
                for idx, playlist_model in enumerate(self._model):
                    if playlist_model is playlist:
                        self._model.remove(idx)
                        break

            playlists_filter = Gtk.CustomFilter()
            playlists_filter.set_filter_func(self._playlists_filter)
            self._model_filter.set_filter(playlists_filter)
            self._notificationmanager.pop_loading()

        self._notificationmanager.push_loading()

        self._pl_delete_stmt.bind_string("playlist", playlist.props.pl_id)
        self._pl_delete_stmt.update_async(None, _delete_cb)

    def create_playlist(self, playlist_title: str, callback: Callable) -> None:
        """Creates a new user playlist.

        :param str playlist_title: playlist title
        :param callback: function to perform once the playlist is created
        """
        def _cursor_next_async(
                cursor: Tracker.SparqlCursor, result: Gio.AsyncResult) -> None:
            try:
                has_next = cursor.next_finish(result)
            except GLib.Error as error:
                cursor.close()
                self._log.warning(f"Cursor iteration error: {error.message}")
                return

            if not has_next:
                cursor.close()
                return

            media = utils.create_grilo_media_from_cursor(
                cursor, Grl.MediaType.CONTAINER)
            self._add_user_playlist(media, callback)

            cursor.next_async(None, _cursor_next_async)

        def _execute_async(
                stmt: Tracker.SparqlStatment, result: Gio.AsyncResult) -> None:
            try:
                cursor = stmt.execute_finish(result)
            except GLib.Error as error:
                cursor.close()
                self._log.warning(f"Playlist create error: {error.message}")
                return

            cursor.next_async(None, _cursor_next_async)

        def _create_cb(
                stmt: Tracker.SparqlStatement, result: Gio.AsyncResult,
                pl_urn: str) -> None:
            try:
                stmt.update_finish(result)
            except GLib.Error as error:
                self._log.warning(
                    f"Unable to create playlist {playlist_title}:"
                    f" {error.message}")
                if callback is not None:
                    callback(None)

                return

            self._pl_query_stmt = self._tracker.load_statement_from_gresource(
                "/org/gnome/Music/queries/playlist_query_playlist.rq")
            self._pl_query_stmt.bind_string("playlist", pl_urn)
            self._pl_query_stmt.execute_async(None, _execute_async)

        pl_urn = f"urn:gnomemusic:playlist:{playlist_title}"
        self._pl_create_stmt.bind_string("title", playlist_title)
        self._pl_create_stmt.bind_string("playlist", pl_urn)
        self._pl_create_stmt.update_async(None, _create_cb, pl_urn)

    def check_smart_playlist_change(self):
        """Check if smart playlists need to be updated.

        A smart playlist needs to be updated in two cases:
        * it is being played (active_playlist)
        * it is visible in PlaylistsView
        """
        active_core_object = self._coremodel.props.active_core_object
        if (isinstance(active_core_object, Playlist)
                and active_core_object.props.is_smart):
            active_core_object.update()
        else:
            self._coremodel.emit("smart-playlist-change")


class Playlist(GObject.GObject):
    """ Base class of all playlists """

    __gtype_name__ = "Playlist"

    __gsignals__ = {
        "playlist-loaded": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    count = GObject.Property(type=int, default=0)
    creation_date = GObject.Property(type=GLib.DateTime, default=None)
    icon_name = GObject.Property(type=str, default="music-playlist-symbolic")
    is_smart = GObject.Property(type=bool, default=False)
    pl_id = GObject.Property(type=str, default=None)
    query = GObject.Property(type=str, default=None)
    tag_text = GObject.Property(type=str, default=None)

    def __init__(
            self, media=None, query=None, tag_text=None, source=None,
            application=None, tracker_wrapper=None, songs_hash=None):
        super().__init__()
        """Initialize a playlist

       :param Grl.Media media: A media object
       :param string query: Tracker query that returns the playlist
       :param string tag_text: The non translatable unique identifier
            of the playlist
       :param Grl.Source source: The Grilo Tracker source object
       :param Application application: The Application instance
       :param TrackerWrapper tracker_wrapper: The TrackerWrapper instance
       :param dict songs_hash: The songs hash table
        """
        if media:
            self.props.pl_id = media.get_id()
            self._title = utils.get_media_title(media)
            self.props.count = media.get_childcount()
            self.props.creation_date = media.get_creation_date()
        else:
            self._title = None

        self.props.query = query
        self.props.tag_text = tag_text
        self._application = application
        self._model = None
        self._source = source
        self._coremodel = application.props.coremodel
        self._log = application.props.log
        self._songs_hash = songs_hash
        self._tracker = tracker_wrapper.props.local_db
        self._tracker_wrapper = tracker_wrapper
        self._notificationmanager = application.props.notificationmanager

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self._add_song_stmt = self._tracker.load_statement_from_gresource(
            "/org/gnome/Music/queries/playlist_add_song.rq")
        self._delete_song_stmt = self._tracker.load_statement_from_gresource(
            "/org/gnome/Music/queries/playlist_delete_song.rq")
        self._pl_del_entry_stmt = self._tracker.load_statement_from_gresource(
            "/org/gnome/Music/queries/playlist_query_delete_entry.rq")
        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/playlist_query_songs.rq")
        self._pl_songs_stmt = self._tracker.query_statement(prep_stmt)
        self._rename_title_stmt = self._tracker.load_statement_from_gresource(
            "/org/gnome/Music/queries/playlist_rename_title.rq")
        self._reorder_stmt = self._tracker.load_statement_from_gresource(
            "/org/gnome/Music/queries/playlist_reorder_songs.rq")

        self._songs_todelete = []

    def _prepare_statement(self, resource_path: str) -> str:
        """Helper to insert bus name and location filter in query"""
        gbytes = Gio.resources_lookup_data(
            resource_path, Gio.ResourceLookupFlags.NONE)
        query_str = gbytes.get_data().decode("utf-8")
        query_str = query_str.replace(
            "{bus_name}", self._tracker_wrapper.props.miner_fs_busname)
        query_str = query_str.replace(
            "{location_filter}", self._tracker_wrapper.location_filter())

        return query_str

    @GObject.Property(type=Gio.ListStore, default=None)
    def model(self):
        if self._model is None:
            self._model = Gio.ListStore()

            self._populate_model()

        return self._model

    @model.setter  # type: ignore
    def model(self, value):
        self._model = value

    def _populate_model(self):
        self._notificationmanager.push_loading()

        def _cursor_next_async(
                cursor: Tracker.SparqlCursor, result: Gio.AsyncResult) -> None:
            try:
                has_next = cursor.next_finish(result)
            except GLib.Error as error:
                self._log.warning(
                    f"Cursor next for {self._title} failed: {error.message}")
                return

            if not has_next:
                cursor.close()

                self.props.count = self._model.get_n_items()
                self.emit("playlist-loaded")
                self._notificationmanager.pop_loading()
                return

            media = utils.create_grilo_media_from_cursor(
                cursor, Grl.MediaType.AUDIO)
            coresong = CoreSong(self._application, media)
            self._bind_to_main_song(coresong)
            if coresong not in self._songs_todelete:
                self._model.append(coresong)

            cursor.next_async(None, _cursor_next_async)

        def _on_songs_queried(
                stmt: Tracker.SparlStatement, result: Gio.AsyncResult) -> None:
            try:
                cursor = stmt.execute_finish(result)
            except GLib.Error as error:
                self._log.warning(
                    f"Statement error: {error.message}")
                return

            cursor.next_async(None, _cursor_next_async)

        self._pl_songs_stmt.bind_string("playlist", self.props.pl_id)
        self._pl_songs_stmt.execute_async(None, _on_songs_queried)

    def _bind_to_main_song(self, coresong):
        main_coresong = self._songs_hash[coresong.props.media.get_id()]

        # It is not necessary to bind all the CoreSong properties:
        # selected property is linked to a view
        # validation is a short-lived playability check for local songs
        bidirectional_properties = [
            "album", "album_disc_number", "artist", "duration", "media",
            "grlid", "play_count", "title", "track_number", "url", "favorite"]

        for prop in bidirectional_properties:
            main_coresong.bind_property(
                prop, coresong, prop,
                GObject.BindingFlags.BIDIRECTIONAL
                | GObject.BindingFlags.SYNC_CREATE)

        # There is no need for the "state" property to be bidirectional
        coresong.bind_property(
            prop, main_coresong, "state", GObject.BindingFlags.DEFAULT)

    @GObject.Property(type=str, default=None)
    def title(self):
        """Playlist title

        :returns: playlist title
        :rtype: str
        """
        return self._title

    @title.setter  # type: ignore
    def title(self, new_name: str) -> None:
        """Rename a playlist

        :param str new_name: new playlist name
        """
        self._notificationmanager.push_loading()

        def _update_title_cb(
                stmt: Tracker.SparqlStatement,
                result: Gio.AsyncResult) -> None:
            try:
                stmt.update_finish(result)
            except GLib.Error as error:
                self._log.warning(
                    f"Unable to rename playlist from {self._title} to"
                    f" {new_name}: {error.message}")
            else:
                self._title = new_name
                self.notify("title")
            finally:
                self._notificationmanager.pop_loading()

        self._rename_title_stmt.bind_string("playlist", self.props.pl_id)
        self._rename_title_stmt.bind_string("title", new_name)
        self._rename_title_stmt.update_async(None, _update_title_cb)

    def stage_song_deletion(self, coresong, index):
        """Adds a song to the list of songs to delete

        :param CoreSong coresong: song to delete
        :param int position: Song position in the playlist
        """
        self._songs_todelete.append(coresong)
        self._model.remove(index)
        self.props.count -= 1

    def undo_pending_song_deletion(self, coresong, position):
        """Removes song from the list of songs to delete

        :param CoreSong coresong: song to delete
        :param int position: Song position in the playlist
        """
        self._songs_todelete.remove(coresong)
        self._model.insert(position, coresong)
        self.props.count += 1

    def finish_song_deletion(self, coresong: CoreSong, position: int) -> None:
        """Removes a song from the playlist

        :param CoreSong coresong: song to remove
        :param int position: Song position in the playlist, starts from
        zero
        """
        def _update_async(
                stmt: Tracker.SparqlStatment, result: Gio.AsyncResult) -> None:
            try:
                stmt.update_finish(result)
            except GLib.Error as e:
                self._log.warning(
                    f"Unable to remove song from playlist {self.props.title}:"
                    f" {e.message}")

        def _cursor_next_async(
                cursor: Tracker.SparqlCursor, result: Gio.AsyncResult) -> None:
            try:
                has_next = cursor.next_finish(result)
            except GLib.Error as error:
                cursor.close()
                self._log.warning(f"Unable to iterate cursor: {error.message}")
                return

            if not has_next:
                cursor.close()
                self._songs_todelete.remove(coresong)
                return

            media = utils.create_grilo_media_from_cursor(
                cursor, Grl.MediaType.AUDIO)
            self._delete_song_stmt.bind_string("entry", media.get_id())
            self._delete_song_stmt.bind_string("playlist", self.props.pl_id)
            self._delete_song_stmt.update_async(None, _update_async)

            cursor.next_async(None, _cursor_next_async)

        def _entry_retrieved(
                stmt: Tracker.SparqlStatement,
                result: Gio.AsyncResult) -> None:
            try:
                cursor = stmt.execute_finish(result)
            except GLib.Error as error:
                cursor.close()
                self._log.warning(f"No entry to delete: {error.message}")
                return

            cursor.next_async(None, _cursor_next_async)

        self._pl_del_entry_stmt.bind_string("playlist_id", self.props.pl_id)
        self._pl_del_entry_stmt.bind_string("position", str(position + 1))
        self._pl_del_entry_stmt.execute_async(None, _entry_retrieved)

    def add_songs(self, coresongs):
        """Adds songs to the playlist

        :param list coresongs: list of Coresong
        """
        def _update_cb(
                stmt: Tracker.SparqlStatement,
                result: Gio.AsyncResult) -> None:
            try:
                stmt.update_finish(result)
            except GLib.Error as error:
                self._log.warning(
                    f"Unable to add a song to playlist {self.props.title}:"
                    f" {error.message}")
            else:
                if self._model is None:
                    return

                media = coresong.props.media
                coresong_copy = CoreSong(self._application, media)
                self._bind_to_main_song(coresong_copy)
                self._model.append(coresong_copy)
                self.props.count = self._model.get_n_items()

        self._add_song_stmt.bind_string("playlist", self.props.pl_id)
        for coresong in coresongs:
            self._add_song_stmt.bind_string(
                "uri", coresong.props.media.get_url())
            self._add_song_stmt.update_async(None, _update_cb)

    def reorder(self, previous_position: int, new_position: int) -> None:
        """Changes the order of a songs in the playlist.

        :param int previous_position: previous song position
        :param int new_position: new song position
        """
        def _batch_execute_cb(
                batch: Tracker.Batch, result: Gio.AsyncResult) -> None:
            try:
                batch.execute_finish(result)
            except GLib.Error as error:
                self._log.warning(f"Unable to reorder songs: {error.message}")

        coresong = self._model.get_item(previous_position)
        self._model.remove(previous_position)
        self._model.insert(new_position, coresong)

        # Unlike ListModel, MediaList starts counting from 1
        previous_position += 1
        new_position += 1

        # Set the item to be reordered to position 0 (unused in
        # a MediaFileListEntry) and bump or drop the remaining items
        # in between. Then set the initial item from 0 to position.
        change_list = []
        change_list.append((previous_position, 0))
        if previous_position > new_position:
            for position in reversed(range(new_position, previous_position)):
                change_list.append((position, position + 1))
        elif previous_position < new_position:
            for position in range(previous_position, new_position):
                change_list.append((position + 1, position))
        change_list.append((0, new_position))

        batch = self._tracker.create_batch()
        for old, new in change_list:
            batch.add_statement(
                self._reorder_stmt, ["id", "new_position", "old_position"],
                [self.props.pl_id, float(new), float(old)])

        batch.execute_async(None, _batch_execute_cb)


class SmartPlaylist(Playlist):
    """Base class for smart playlists"""

    _METADATA_SMART_PLAYLIST_KEYS = [
        Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_ALBUM_DISC_NUMBER,
        Grl.METADATA_KEY_ARTIST,
        Grl.METADATA_KEY_DURATION,
        Grl.METADATA_KEY_FAVOURITE,
        Grl.METADATA_KEY_ID,
        Grl.METADATA_KEY_PLAY_COUNT,
        Grl.METADATA_KEY_URL,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_TRACK_NUMBER,
    ]

    def __init__(self, **args):
        super().__init__(**args)

        self.props.is_smart = True

    @GObject.Property(type=Gio.ListStore, default=None)
    def model(self):
        if self._model is None:
            self._model = Gio.ListStore.new(CoreSong)

            self._notificationmanager.push_loading()

            def _add_to_model(source, op_id, media, remaining, error):
                if error:
                    self._log.warning("Error: {}".format(error))
                    self._notificationmanager.pop_loading()
                    self.emit("playlist-loaded")
                    return

                if not media:
                    self.props.count = self._model.get_n_items()
                    self._notificationmanager.pop_loading()
                    self.emit("playlist-loaded")
                    return

                coresong = CoreSong(self._application, media)
                self._bind_to_main_song(coresong)
                self._model.append(coresong)

            self._source.query(
                self.props.query, self._METADATA_SMART_PLAYLIST_KEYS,
                self._fast_options, _add_to_model)

        return self._model

    def update(self):
        """Updates playlist model."""
        if self._model is None:
            return

        new_model_medias = []

        def _fill_new_model(source, op_id, media, remaining, error):
            if error:
                return

            if not media:
                self._finish_update(new_model_medias)
                return

            new_model_medias.append(media)

        self._source.query(
            self.props.query, self._METADATA_SMART_PLAYLIST_KEYS,
            self._fast_options, _fill_new_model)

    def _finish_update(self, new_model_medias):
        if not new_model_medias:
            self._model.remove_all()
            self.props.count = 0
            return

        current_models_ids = [coresong.props.media.get_id()
                              for coresong in self._model]
        new_model_ids = [media.get_id() for media in new_model_medias]

        idx_to_delete = []
        for idx, media_id in enumerate(current_models_ids):
            if media_id not in new_model_ids:
                idx_to_delete.insert(0, idx)

        for idx in idx_to_delete:
            self._model.remove(idx)
            self.props.count -= 1

        for idx, media in enumerate(new_model_medias):
            if media.get_id() not in current_models_ids:
                coresong = CoreSong(self._application, media)
                self._bind_to_main_song(coresong)
                self._model.append(coresong)
                self.props.count += 1


class MostPlayed(SmartPlaylist):
    """Most Played smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "MOST_PLAYED"
        # TRANSLATORS: this is a playlist name
        self._title = _("Most Played")
        self.props.icon_name = "audio-speakers-symbolic"
        self.props.query = """
        SELECT
            %(media_type)s AS ?type
            ?song AS ?id
            ?title
            ?url
            ?artist
            ?album
            ?duration
            ?trackNumber
            ?albumDiscNumber
            ?playCount
            ?tag AS ?favorite
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT
                        ?song
                        nie:title(?song) AS ?title
                        nie:isStoredAs(?song) AS ?url
                        nmm:artistName(nmm:artist(?song)) AS ?artist
                        nie:title(nmm:musicAlbum(?song)) AS ?album
                        nfo:duration(?song) AS ?duration
                        nmm:trackNumber(?song) AS ?trackNumber
                        nmm:setNumber(nmm:musicAlbumDisc(?song))
                            AS ?albumDiscNumber
                    WHERE {
                        ?song a nmm:MusicPiece .
                        %(location_filter)s
                    }
                }
            }
            ?song nie:usageCounter ?playCount
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        }
        ORDER BY DESC(?playCount) LIMIT 50
        """.replace('\n', ' ').strip() % {
            "media_type": int(Grl.MediaType.AUDIO),
            "location_filter": self._tracker_wrapper.location_filter(),
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
        }


class NeverPlayed(SmartPlaylist):
    """Never Played smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "NEVER_PLAYED"
        # TRANSLATORS: this is a playlist name
        self._title = _("Never Played")
        self.props.icon_name = "deaf-symbolic"
        self.props.query = """
        SELECT
            %(media_type)s AS ?type
            ?song AS ?id
            ?title
            ?url
            ?artist
            ?album
            ?duration
            ?trackNumber
            ?albumDiscNumber
            nie:usageCounter(?song) AS ?playCount
            ?tag AS ?favorite
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT
                        ?song
                        nie:title(?song) AS ?title
                        nie:isStoredAs(?song) AS ?url
                        nmm:artistName(nmm:artist(?song)) AS ?artist
                        nie:title(nmm:musicAlbum(?song)) AS ?album
                        nfo:duration(?song) AS ?duration
                        nmm:trackNumber(?song) AS ?trackNumber
                        nmm:setNumber(nmm:musicAlbumDisc(?song))
                            AS ?albumDiscNumber
                    WHERE {
                        ?song a nmm:MusicPiece .
                        %(location_filter)s
                    }
                }
            }
            FILTER ( NOT EXISTS { ?song nie:usageCounter ?count .} )
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        } ORDER BY nfo:fileLastAccessed(?song) LIMIT 50
        """.replace('\n', ' ').strip() % {
            "media_type": int(Grl.MediaType.AUDIO),
            "location_filter": self._tracker_wrapper.location_filter(),
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
        }


class RecentlyPlayed(SmartPlaylist):
    """Recently Played smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "RECENTLY_PLAYED"
        # TRANSLATORS: this is a playlist name
        self._title = _("Recently Played")
        self.props.icon_name = "document-open-recent-symbolic"

        sparql_midnight_dateTime_format = "%Y-%m-%dT00:00:00Z"
        days_difference = 7
        seconds_difference = days_difference * 86400
        compare_date = time.strftime(
            sparql_midnight_dateTime_format,
            time.gmtime(time.time() - seconds_difference))
        self.props.query = """
        SELECT
            %(media_type)s AS ?type
            ?song AS ?id
            ?title
            ?url
            ?artist
            ?album
            ?duration
            ?trackNumber
            ?albumDiscNumber
            nie:usageCounter(?song) AS ?playCount
            ?tag AS ?favorite
        WHERE {
            {
                SELECT
                    ?song
                    ?title
                    ?url
                    ?artist
                    ?album
                    ?duration
                    ?trackNumber
                    ?albumDiscNumber
                    ?playCount
                    ?tag
                    ?lastPlayed
                WHERE {
                    SERVICE <dbus:%(miner_fs_busname)s> {
                        GRAPH tracker:Audio {
                            SELECT
                                ?song
                                nie:title(?song) AS ?title
                                nie:isStoredAs(?song) AS ?url
                                nmm:artistName(nmm:artist(?song)) AS ?artist
                                nie:title(nmm:musicAlbum(?song)) AS ?album
                                nfo:duration(?song) AS ?duration
                                nmm:trackNumber(?song) AS ?trackNumber
                                nmm:setNumber(nmm:musicAlbumDisc(?song))
                                    AS ?albumDiscNumber
                            WHERE {
                                ?song a nmm:MusicPiece .
                                %(location_filter)s
                            }
                        }
                    }
                    ?song nie:contentAccessed ?lastPlayed ;
                        nie:usageCounter ?playCount .
                    OPTIONAL { ?song nao:hasTag ?tag .
                               FILTER (?tag = nao:predefined-tag-favorite) }
                } ORDER BY DESC(?lastPlayed) LIMIT 50
            }
            FILTER (?lastPlayed > '%(compare_date)s'^^xsd:dateTime)
        }
        """.replace('\n', ' ').strip() % {
            "media_type": int(Grl.MediaType.AUDIO),
            'compare_date': compare_date,
            "location_filter": self._tracker_wrapper.location_filter(),
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
        }


class RecentlyAdded(SmartPlaylist):
    """Recently Added smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "RECENTLY_ADDED"
        # TRANSLATORS: this is a playlist name
        self._title = _("Recently Added")
        self.props.icon_name = "list-add-symbolic"

        sparql_midnight_dateTime_format = "%Y-%m-%dT00:00:00Z"
        days_difference = 7
        seconds_difference = days_difference * 86400
        compare_date = time.strftime(
            sparql_midnight_dateTime_format,
            time.gmtime(time.time() - seconds_difference))
        self.props.query = """
        SELECT
            %(media_type)s AS ?type
            ?song AS ?id
            ?title
            ?url
            ?artist
            ?album
            ?duration
            ?trackNumber
            ?albumDiscNumber
            nie:usageCounter(?song) AS ?playCount
            ?tag AS ?favorite
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT
                        ?song
                        nie:title(?song) AS ?title
                        nie:isStoredAs(?song) AS ?url
                        nmm:artistName(nmm:artist(?song)) AS ?artist
                        nie:title(nmm:musicAlbum(?song)) AS ?album
                        nfo:duration(?song) AS ?duration
                        nmm:trackNumber(?song) AS ?trackNumber
                        nmm:setNumber(nmm:musicAlbumDisc(?song))
                            AS ?albumDiscNumber
                        ?added
                    WHERE {
                        ?song a nmm:MusicPiece ;
                              nrl:added ?added .
                        %(location_filter)s
                        FILTER ( ?added > '%(compare_date)s'^^xsd:dateTime )
                    }
                }
            }
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        } ORDER BY DESC(nrl:added(?song)) LIMIT 50
        """.replace('\n', ' ').strip() % {
            "media_type": int(Grl.MediaType.AUDIO),
            'compare_date': compare_date,
            "location_filter": self._tracker_wrapper.location_filter(),
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
        }


class Favorites(SmartPlaylist):
    """Favorites smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "FAVORITES"
        # TRANSLATORS: this is a playlist name
        self._title = _("Favorite Songs")
        self.props.icon_name = "starred-symbolic"
        self.props.query = """
            SELECT
                %(media_type)s AS ?type
                ?song AS ?id
                ?title
                ?url
                ?artist
                ?album
                ?duration
                ?trackNumber
                ?albumDiscNumber
                nie:usageCounter(?song) AS ?playCount
                nao:predefined-tag-favorite AS ?favorite
            WHERE {
                SERVICE <dbus:%(miner_fs_busname)s> {
                    GRAPH tracker:Audio {
                        SELECT
                            ?song
                            nie:title(?song) AS ?title
                            nie:isStoredAs(?song) AS ?url
                            nmm:artistName(nmm:artist(?song)) AS ?artist
                            nie:title(nmm:musicAlbum(?song)) AS ?album
                            nfo:duration(?song) AS ?duration
                            nmm:trackNumber(?song) AS ?trackNumber
                            nmm:setNumber(nmm:musicAlbumDisc(?song))
                                AS ?albumDiscNumber
                            nrl:added(?song) AS ?added
                        WHERE {
                            ?song a nmm:MusicPiece .
                            %(location_filter)s
                        }
                    }
                }
                ?song nao:hasTag nao:predefined-tag-favorite .
            } ORDER BY DESC(?added)
        """.replace('\n', ' ').strip() % {
            "media_type": int(Grl.MediaType.AUDIO),
            "location_filter": self._tracker_wrapper.location_filter(),
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
        }


class InsufficientTagged(SmartPlaylist):
    """Lacking tags to be displayed in the artist/album views"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "INSUFFICIENT_TAGGED"
        # TRANSLATORS: this is a playlist name indicating that the
        # files are not tagged enough to be displayed in the albums
        # or artists views.
        self._title = _("Insufficiently Tagged")
        self.props.icon_name = "question-round-symbolic"
        self.props.query = """
        SELECT
            %(media_type)s AS ?type
            ?song AS ?id
            ?title
            ?url
            ?artist
            ?album
            ?duration
            ?trackNumber
            ?albumDiscNumber
            nie:usageCounter(?song) AS ?playCount
            ?tag AS ?favorite
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT
                        ?song
                        nie:title(?song) AS ?title
                        nie:isStoredAs(?song) AS ?url
                        nmm:artistName(nmm:artist(?song)) AS ?artist
                        nie:title(nmm:musicAlbum(?song)) AS ?album
                        nfo:duration(?song) AS ?duration
                        nmm:trackNumber(?song) AS ?trackNumber
                        nmm:setNumber(nmm:musicAlbumDisc(?song))
                            AS ?albumDiscNumber
                    WHERE {
                        {
                            ?song a nmm:MusicPiece .
                            %(location_filter)s
                            FILTER NOT EXISTS {
                                ?song nmm:musicAlbum ?album
                            }
                        } UNION {
                            ?song a nmm:MusicPiece .
                            %(location_filter)s
                            FILTER NOT EXISTS {
                                ?song nmm:artist ?artist
                            }
                        }
                    }
                }
            }
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        }
        """.replace('\n', ' ').strip() % {
            "media_type": int(Grl.MediaType.AUDIO),
            "location_filter": self._tracker_wrapper.location_filter(),
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
        }


class AllSongs(SmartPlaylist):
    """All Songs smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "ALL_SONGS"
        # TRANSLATORS: this is a playlist name
        self._title = _("All Songs")
        self.props.icon_name = "folder-music-symbolic"

        self.props.query = """
        SELECT
            %(media_type)s AS ?type
            ?song AS ?id
            ?title
            ?url
            ?artist
            ?album
            ?duration
            ?trackNumber
            ?albumDiscNumber
            nie:usageCounter(?song) AS ?playCount
            ?tag AS ?favorite
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT
                        ?song
                        nie:title(?song) AS ?title
                        nie:isStoredAs(?song) AS ?url
                        nmm:artistName(nmm:artist(?song)) AS ?artist
                        nie:title(nmm:musicAlbum(?song)) AS ?album
                        nfo:duration(?song) AS ?duration
                        nmm:trackNumber(?song) AS ?trackNumber
                        nmm:setNumber(nmm:musicAlbumDisc(?song))
                            AS ?albumDiscNumber
                    WHERE {
                        ?song a nmm:MusicPiece .
                        %(location_filter)s
                    }
                }
            }
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        } ORDER BY ?artist ?album ?trackNumber
        """.replace('\n', ' ').strip() % {
            "media_type": int(Grl.MediaType.AUDIO),
            "location_filter": self._tracker_wrapper.location_filter(),
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
        }
