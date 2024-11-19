# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations

import gi
gi.require_versions({"Grl": "0.3", "Tracker": "3.0"})
from gi.repository import Gio, Grl, GLib, GObject, Tracker

from gnomemusic.coresong import CoreSong
import gnomemusic.utils as utils


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
