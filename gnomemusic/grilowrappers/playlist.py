# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from typing import Any, Dict, List
import asyncio
import typing

from gi.repository import Gio, GLib, GObject

from gnomemusic.coresong import CoreSong
import gnomemusic.utils as utils
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.trackerwrapper import TrackerWrapper


class Playlist(GObject.GObject):
    """ Base class of all playlists """

    __gtype_name__ = "Playlist"

    count = GObject.Property(type=int, default=0)
    creation_date = GObject.Property(type=GLib.DateTime, default=None)
    icon_name = GObject.Property(type=str, default="music-playlist-symbolic")
    is_smart = GObject.Property(type=bool, default=False)
    pl_id = GObject.Property(type=str, default=None)
    query = GObject.Property(type=str, default=None)
    tag_text = GObject.Property(type=str, default=None)

    def __init__(
            self, cursor_dict: Dict[str, Any], query: str, tag_text: str,
            application: Application, tsparql_wrapper: TrackerWrapper,
            songs_model: GLib.ListStore) -> None:
        super().__init__()
        """Initialize a playlist

       :param Dict[str, Any] cursor_dict: Dict with Tsparql keys
       :param string query: Tracker query that returns the playlist
       :param string tag_text: The non translatable unique identifier
            of the playlist
       :param Application application: The Application instance
       :param TrackerWrapper tsparql_wrapper: The TrackerWrapper instance
       :param GLib.ListStore songs_model: The songs model
        """
        if cursor_dict:
            self.props.pl_id = cursor_dict.get("id")
            self._title = utils.get_title_from_cursor_dict(cursor_dict)
            self.props.count = cursor_dict.get("childCount")
            self.props.creation_date = cursor_dict.get("creationDate")
        else:
            self._title = None

        self.props.query = query
        self.props.tag_text = tag_text
        self._application = application
        self._model = None
        self._coremodel = application.props.coremodel
        self._log = application.props.log
        self._songs_model = songs_model
        self._tsparql = tsparql_wrapper.props.local_db
        self._tsparql_wrapper = tsparql_wrapper
        self._notificationmanager = application.props.notificationmanager

        self._add_song_stmt = self._tsparql.load_statement_from_gresource(
            "/org/gnome/Music/queries/playlist_add_song.rq")
        self._delete_song_stmt = self._tsparql.load_statement_from_gresource(
            "/org/gnome/Music/queries/playlist_delete_song.rq")
        self._pl_del_entry_stmt = self._tsparql.load_statement_from_gresource(
            "/org/gnome/Music/queries/playlist_query_delete_entry.rq")
        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/playlist_query_songs.rq")
        self._pl_songs_stmt = self._tsparql.query_statement(prep_stmt)
        self._rename_title_stmt = self._tsparql.load_statement_from_gresource(
            "/org/gnome/Music/queries/playlist_rename_title.rq")
        self._reorder_stmt = self._tsparql.load_statement_from_gresource(
            "/org/gnome/Music/queries/playlist_reorder_songs.rq")

        self._songs_todelete: List[CoreSong] = []

    def _prepare_statement(self, resource_path: str) -> str:
        """Helper to insert bus name and location filter in query"""
        gbytes = Gio.resources_lookup_data(
            resource_path, Gio.ResourceLookupFlags.NONE)
        query_str = gbytes.get_data().decode("utf-8")
        query_str = query_str.replace(
            "{bus_name}", self._tsparql_wrapper.props.miner_fs_busname)
        query_str = query_str.replace(
            "{location_filter}", self._tsparql_wrapper.location_filter())

        return query_str

    @GObject.Property(type=Gio.ListStore, default=None)
    def model(self):
        if self._model is None:
            self._model = Gio.ListStore()
            asyncio.create_task(self._populate_model())

        return self._model

    @model.setter  # type: ignore
    def model(self, value):
        self._model = value

    async def _populate_model(self):
        async with self._notificationmanager:
            self._pl_songs_stmt.bind_string("playlist", self.props.pl_id)
            try:
                cursor = await self._pl_songs_stmt.execute_async()
            except GLib.Error as error:
                self._log.warning(
                    f"Failure populating playlist model {self.props.pl_id}:"
                    f" {error.domain}, {error.message}")
                return

            try:
                has_next = await cursor.next_async()
            except GLib.Error as error:
                cursor.close()
                self._log.warning(
                    f"Cursor iteration error: {error.domain}, {error.message}")
                return
            while has_next:
                cursor_dict = utils.dict_from_cursor(cursor)
                coresong = CoreSong(self._application, cursor_dict)
                self._bind_to_main_song(coresong)
                if coresong not in self._songs_todelete:
                    self._model.append(coresong)

                try:
                    has_next = await cursor.next_async()
                except GLib.Error as error:
                    cursor.close()
                    self._log.warning(
                        f"Cursor iteration error: {error.domain}, "
                        f"{error.message}")
                    return
            else:
                cursor.close()
                self.props.count = self._model.get_n_items()

    def _bind_to_main_song(self, coresong):
        def equal_func(
                coresong_compared: CoreSong,
                coresong_provided: CoreSong) -> bool:
            return coresong_compared == coresong_provided

        success, position = self._songs_model.find_with_equal_func(
            coresong, equal_func)
        main_coresong = self._songs_model[position]

        # It is not necessary to bind all the CoreSong properties:
        # validation: short-lived playability check for local songs
        bidirectional_properties = [
            "album", "album_disc_number", "artist", "duration", "id",
            "play_count", "title", "track_number", "url", "favorite"]

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
        asyncio.create_task(self._set_title(new_name))

    async def _set_title(self, new_name: str) -> None:
        async with self._notificationmanager:
            self._rename_title_stmt.bind_string("playlist", self.props.pl_id)
            self._rename_title_stmt.bind_string("title", new_name)
            try:
                self._rename_title_stmt.update_async()
            except GLib.Error as error:
                self._log.warning(
                    f"Unable to rename playlist from {self._title} to "
                    f"{new_name}: {error.domain}, {error.message}")
            else:
                self._title = new_name
                self.notify("title")

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
        asyncio.create_task(self._finish_song_deletion(coresong, position))

    async def _finish_song_deletion(
            self, coresong: CoreSong, position: int) -> None:
        self._pl_del_entry_stmt.bind_string("playlist_id", self.props.pl_id)
        self._pl_del_entry_stmt.bind_string("position", str(position + 1))
        try:
            cursor = await self._pl_del_entry_stmt.execute_async()
        except GLib.Error as error:
            cursor.close()
            self._log.warning(
                f"No entry to delete: {error.domain}, {error.message}")
            return

        try:
            has_next = await cursor.next_async()
        except GLib.Error as error:
            cursor.close()
            self._log.warning(
                f"Cursor iteration error: {error.domain}, {error.message}")
            return
        while has_next:
            cursor_dict = utils.dict_from_cursor(cursor)
            self._delete_song_stmt.bind_string("entry", cursor_dict.get("id"))
            self._delete_song_stmt.bind_string("playlist", self.props.pl_id)
            try:
                await self._delete_song_stmt.update_async()
            except GLib.Error as error:
                cursor.close()
                self._songs_todelete.remove(coresong)
                self._log.warning(
                    f"Unable to remove song from playlist {self.props.title}:"
                    f" {error.domain} {error.message}")
                return

            try:
                has_next = await cursor.next_async()
            except GLib.Error as error:
                cursor.close()
                self._log.warning(
                    f"Cursor iteration error: {error.domain}, {error.message}")
                return
        else:
            self._songs_todelete.remove(coresong)
            cursor.close()

    def add_songs(self, coresongs: List[CoreSong]) -> None:
        """Adds songs to the playlist

        :param list coresongs: list of Coresong
        """
        asyncio.create_task(self._add_songs(coresongs))

    async def _add_songs(self, coresongs: List[CoreSong]) -> None:
        self._add_song_stmt.bind_string("playlist", self.props.pl_id)
        for coresong in coresongs:
            self._add_song_stmt.bind_string("uri", coresong.props.url)
            try:
                await self._add_song_stmt.update_async()
            except GLib.Error as error:
                self._log.warning(
                    f"Unable to add a song to playlist {self.props.title}:"
                    f" {error.domain}, {error.message}")
            else:
                if self._model is None:
                    continue

                coresong_copy = CoreSong(
                    self._application, coresong.props.cursor_dict)
                self._bind_to_main_song(coresong_copy)
                self._model.append(coresong_copy)
                self.props.count = self._model.get_n_items()

    def reorder(self, previous_position: int, new_position: int) -> None:
        """Changes the order of a songs in the playlist.

        :param int previous_position: previous song position
        :param int new_position: new song position
        """
        asyncio.create_task(self._reorder(previous_position, new_position))

    async def _reorder(
            self, previous_position: int, new_position: int) -> None:
        if not self._model:
            return

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

        batch = self._tsparql.create_batch()
        for old, new in change_list:
            batch.add_statement(
                self._reorder_stmt, ["id", "new_position", "old_position"],
                [self.props.pl_id, float(new), float(old)])

        try:
            await batch.execute_async()
        except GLib.Error as error:
            self._log.warning(
                f"Unable to reorder songs for {self.props.pl_id}:"
                f" {error.domain}, {error.message}")
