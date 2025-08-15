# Copyright 2025 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from typing import Callable, List, Optional, Union
import typing
import asyncio

import gi
gi.require_versions({"Grl": "0.3", "Tsparql": "3.0"})
from gi.repository import Gio, Gtk, GLib, GObject, Tsparql

from gnomemusic.corealbum import CoreAlbum
from gnomemusic.coreartist import CoreArtist
from gnomemusic.coredisc import CoreDisc
from gnomemusic.coresong import CoreSong
from gnomemusic.grilowrappers.localsearchplaylists import LocalSearchPlaylists
from gnomemusic.trackerwrapper import TrackerWrapper
import gnomemusic.utils as utils
if typing.TYPE_CHECKING:
    from gi.repository import TSparql
    from gnomemusic.application import Application
    from gnomemusic.grilowrappers.playlist import Playlist
    CoreObject = Union[CoreAlbum, CoreArtist, CoreSong]


class LocalSearchWrapper(GObject.Object):
    """LocalSearch based data source
    """

    __gtype_name__ = "LocalSearchWrapper"

    _SPLICE_SIZE = 100

    def __init__(
            self, application: Application,
            tsparql_wrapper: TrackerWrapper) -> None:
        """Initialize LocalSearchWrapper

        Set up and fill models with information retrieved through
        LocalSearch.

       :param Application application: The Application instance
       :param TrackerWrapper tsparql_wrapper: The TrackerWrapper instance
        """
        super().__init__()

        self._application = application
        self._log = application.props.log
        self._notificationmanager = application.props.notificationmanager
        self._tsparql = tsparql_wrapper.props.local_db
        self._tsparql_playlists: Optional[LocalSearchPlaylists] = None
        self._tsparql_wrapper = tsparql_wrapper

        self._cancellable = Gio.Cancellable()

        self._albums_model = Gio.ListStore.new(CoreAlbum)
        self._artists_model = Gio.ListStore.new(CoreArtist)
        self._songs_model = Gio.ListStore.new(CoreSong)

        cm = application.props.coremodel
        cm.props.albums_proxy.append(self._albums_model)
        cm.props.artists_proxy.append(self._artists_model)
        cm.props.songs_proxy.append(self._songs_model)

        self._albums_search_model = Gtk.FilterListModel.new(self._albums_model)
        self._albums_search_model.set_filter(Gtk.AnyFilter())
        cm.props.albums_search_proxy.append(self._albums_search_model)

        self._artists_search_model = Gtk.FilterListModel.new(
            self._artists_model)
        self._artists_search_model.set_filter(Gtk.AnyFilter())
        cm.props.artists_search_proxy.append(self._artists_search_model)

        self._songs_search_model = Gtk.FilterListModel.new(self._songs_model)
        self._songs_search_model.set_filter(Gtk.AnyFilter())
        cm.props.songs_search_proxy.append(self._songs_search_model)

        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/albums.rq")
        self._albums_stmt = self._tsparql.query_statement(prep_stmt)

        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/artists.rq")
        self._artists_stmt = self._tsparql.query_statement(prep_stmt)

        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/songs.rq")
        prep_stmt = prep_stmt.replace("song_bind", "BIND(~song AS ?song)")
        self._song_stmt = self._tsparql.query_statement(prep_stmt)

        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/songs.rq")
        prep_stmt = prep_stmt.replace("song_bind", "")
        self._songs_stmt = self._tsparql.query_statement(prep_stmt)

        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/album_discs.rq")
        self._album_discs_stmt = self._tsparql.query_statement(prep_stmt)

        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/album_disc.rq")
        self._album_disc_stmt = self._tsparql.query_statement(prep_stmt)

        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/artist_albums.rq")
        self._artist_albums_stmt = self._tsparql.query_statement(prep_stmt)

        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/search_albums.rq")
        self._search_albums_stmt = self._tsparql.query_statement(prep_stmt)

        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/search_artists.rq")
        self._search_artists_stmt = self._tsparql.query_statement(prep_stmt)

        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/search_songs.rq")
        self._search_songs_stmt = self._tsparql.query_statement(prep_stmt)

        asyncio.create_task(self._init_albums_model())
        asyncio.create_task(self._init_artists_model())
        asyncio.create_task(self._init_songs_model())

        self._notifier = self._tsparql_wrapper.props.miner_fs.create_notifier()
        self._notifier.connect("events", self._on_notifier_event)

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

    async def _init_albums_model(self) -> None:
        async with self._notificationmanager:
            try:
                cursor = await self._albums_stmt.execute_async()
            except GLib.Error as error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                return

            try:
                has_next = await cursor.next_async()
            except GLib.Error as error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                has_next = False
            while has_next:
                cursor_dict = utils.dict_from_cursor(cursor)
                corealbum = CoreAlbum(self._application, cursor_dict)

                self._albums_model.append(corealbum)

                try:
                    has_next = await cursor.next_async()
                except GLib.Error as error:
                    self._log.warning(
                        f"Error: {error.domain}, {error.message}")
                    has_next = False

            cursor.close()

    async def _init_artists_model(self) -> None:
        async with self._notificationmanager:
            try:
                cursor = await self._artists_stmt.execute_async()
            except GLib.Error as error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                return

            try:
                has_next = await cursor.next_async()
            except GLib.Error as error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                has_next = False
            while has_next:
                cursor_dict = utils.dict_from_cursor(cursor)
                coreartist = CoreArtist(self._application, cursor_dict)

                self._artists_model.append(coreartist)

                try:
                    has_next = await cursor.next_async()
                except GLib.Error as error:
                    self._log.warning(
                        f"Error: {error.domain}, {error.message}")
                    has_next = False

        cursor.close()

    async def _init_songs_model(self) -> None:
        async with self._notificationmanager:
            try:
                cursor = await self._songs_stmt.execute_async()
            except GLib.Error as error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                return

            songs: List[CoreSong] = []
            try:
                has_next = await cursor.next_async()
            except GLib.Error as error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                has_next = False
            while has_next:
                cursor_dict = utils.dict_from_cursor(cursor)
                coresong = CoreSong(self._application, cursor_dict)

                songs.append(coresong)
                if len(songs) == self._SPLICE_SIZE:
                    self._songs_model.splice(
                        self._songs_model.get_n_items(), 0, songs)
                    songs.clear()

                try:
                    has_next = await cursor.next_async()
                except GLib.Error as error:
                    self._log.warning(
                        f"Error: {error.domain}, {error.message}")
                    has_next = False

            self._songs_model.splice(
                self._songs_model.get_n_items(), 0, songs)
            cursor.close()

            # Initialize the playlists subwrapper after the initial
            # songs model fill, the playlists expect a filled songs
            # model.
            self._tsparql_playlists = LocalSearchPlaylists(
                self._application, self._tsparql_wrapper, self._songs_model)

    def _find_equal_coreobject_urn(
            self, coreobj_compared: CoreObject,
            coreobj_provided: CoreObject) -> bool:
        return coreobj_compared.props.id == coreobj_provided.props.id

    async def _fileid_event(self, event: Tsparql.NotifierEvent) -> None:
        event_type = event.get_event_type()
        urn = event.get_urn()
        coresong_compare = CoreSong(self._application, {"id": urn})
        if event_type in [
                Tsparql.NotifierEventType.CREATE,
                Tsparql.NotifierEventType.UPDATE]:
            await self._add_song(urn)

            found, position = self._songs_model.find_with_equal_func(
                coresong_compare, self._find_equal_coreobject_urn)
            if found:
                coresong = self._songs_model.get_item(position)
                await self._update_album(coresong)
        elif event_type == Tsparql.NotifierEventType.DELETE:
            found, position = self._songs_model.find_with_equal_func(
                coresong_compare, self._find_equal_coreobject_urn)
            if found:
                coresong = self._songs_model.get_item(position)
                self._songs_model.remove(position)
                await self._update_album(coresong)

        if self._tsparql_playlists is not None:
            self._tsparql_playlists.check_smart_playlist_change()

    def _on_notifier_event(
            self, notifier: TSparql.Notifier, service: str, graph: str,
            events: set[Tsparql.NotifierEvent]) -> None:
        for event in events:
            urn = event.get_urn()
            if urn.startswith("urn:fileid:"):
                asyncio.create_task(self._fileid_event(event))

    async def _update_album(self, coresong: CoreSong) -> None:
        corealbum_compare = CoreAlbum(
            self._application, {"id": coresong.props.album_urn})
        found, position = self._albums_model.find_with_equal_func(
            corealbum_compare, self._find_equal_coreobject_urn)
        if found:
            self._albums_model[position].remove_song_from_album(
                coresong.props.album_disc_number, coresong.props.id)

    async def _add_song(self, urn: str) -> None:
        self._song_stmt.bind_string("song", urn)
        async with self._notificationmanager:
            try:
                cursor = await self._song_stmt.execute_async()
            except GLib.Error as error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                return

            try:
                has_next = await cursor.next_async()
            except GLib.Error as error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                has_next = False

            coresong_compare = CoreSong(self._application, {"id": urn})
            while has_next:
                cursor_dict = utils.dict_from_cursor(cursor)
                coresong = CoreSong(self._application, cursor_dict)

                found, position = self._songs_model.find_with_equal_func(
                    coresong_compare, self._find_equal_coreobject_urn)
                if found:
                    self._songs_model.get_item(position).update(cursor_dict)
                else:
                    self._songs_model.append(coresong)

                try:
                    has_next = await cursor.next_async()
                except GLib.Error as error:
                    self._log.warning(
                        f"Error: {error.domain}, {error.message}")
                    has_next = False

            cursor.close()

    async def _get_album_discs(
            self, corealbum: CoreAlbum, disc_model: Gtk.SortListModel) -> None:
        async with self._notificationmanager:
            self._album_discs_stmt.bind_string("album_id", corealbum.props.id)
            try:
                cursor = await self._album_discs_stmt.execute_async()
            except GLib.Error as error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                return

            try:
                has_next = await cursor.next_async()
            except GLib.Error as error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                has_next = False
            while has_next:
                cursor_dict = utils.dict_from_cursor(cursor)
                disc_nr = utils.get_int_from_cursor_dict(
                    cursor_dict, "albumDiscNumber")
                coredisc = CoreDisc(
                    self._application, corealbum, disc_nr)

                disc_model.append(coredisc)

                try:
                    has_next = await cursor.next_async()
                except GLib.Error as error:
                    self._log.warning(
                        f"Error: {error.domain}, {error.message}")
                    has_next = False

            cursor.close()

    def get_album_discs(
            self, corealbum: CoreAlbum, disc_model: Gtk.SortListModel) -> None:
        """Get all discs of an album

        :param CoreAlbum corealbum: The album
        :param Gtk.SortListModel disc_model: The model to fill
        """
        asyncio.create_task(self._get_album_discs(corealbum, disc_model))

    async def _get_album_disc(
            self, coredisc: CoreDisc, model: Gtk.FilterListModel) -> None:
        async with self._notificationmanager:
            self._album_disc_stmt.bind_string("album_id", coredisc.props.id)
            self._album_disc_stmt.bind_int("disc_nr", coredisc.props.disc_nr)
            try:
                cursor = await self._album_disc_stmt.execute_async()
            except GLib.Error as error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                return

            disc_song_ids = []
            try:
                has_next = await cursor.next_async()
            except GLib.Error as error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                has_next = False
            while has_next:
                cursor_dict = utils.dict_from_cursor(cursor)
                disc_song_ids.append(cursor_dict.get("id"))

                try:
                    has_next = await cursor.next_async()
                except GLib.Error as error:
                    self._log.warning(
                        f"Error: {error.domain}, {error.message}")
                    has_next = False

            cursor.close()

            def _filter_func(coresong: CoreSong) -> bool:
                return coresong.props.id in disc_song_ids

            custom_filter = Gtk.CustomFilter()
            custom_filter.set_filter_func(_filter_func)
            model.set_filter(custom_filter)

    def get_album_disc(
            self, coredisc: CoreDisc, model: Gtk.FilterListModel) -> None:
        """Get all songs of an album disc

        :param CoreDisc coredisc: The album disc to look up
        :param Gtk.FilterListModel model: The model to fill
        """
        asyncio.create_task(self._get_album_disc(coredisc, model))

    async def _get_artist_albums(
            self, coreartist: CoreArtist, model: Gtk.FilterListModel) -> None:
        async with self._notificationmanager:
            self._artist_albums_stmt.bind_string("artist", coreartist.props.id)
            try:
                cursor = await self._artist_albums_stmt.execute_async()
            except GLib.Error as error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                return

            album_ids = []
            try:
                has_next = await cursor.next_async()
            except GLib.Error as error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                has_next = False
            while has_next:
                cursor_dict = utils.dict_from_cursor(cursor)
                album_ids.append(cursor_dict.get("id"))

                try:
                    has_next = await cursor.next_async()
                except GLib.Error as error:
                    self._log.warning(
                        f"Error: {error.domain}, {error.message}")
                    has_next = False

            cursor.close()

        def albums_filter(corealbum: CoreAlbum, albums: List[str]) -> bool:
            return corealbum.props.id in albums

        custom_filter = Gtk.CustomFilter()
        custom_filter.set_filter_func(albums_filter, album_ids)
        model.set_filter(custom_filter)

    def get_artist_albums(
            self, coreartist: CoreArtist, model: Gtk.FilterListModel) -> None:
        """Get all albums by an artist

        :param CoreArtist coreartist: The artist to look up
        :param Gtk.FilterListModel model: The model to fill
        """
        asyncio.create_task(self._get_artist_albums(coreartist, model))

    def search(self, text: str) -> None:
        """Search for the given string in the wrappers

        If an empty string is provided, the wrapper should
        reset to an empty state.

        :param str text: The search string
        """
        self._cancellable.cancel()
        if text == "":
            self._artists_search_model.set_filter(Gtk.AnyFilter())
            self._albums_search_model.set_filter(Gtk.AnyFilter())
            self._songs_search_model.set_filter(Gtk.AnyFilter())
            return

        self._cancellable = Gio.Cancellable.new()
        asyncio.create_task(self._search_generic(
            text, self._cancellable, self._search_artists_stmt,
            self._artists_search_model))
        asyncio.create_task(self._search_generic(
            text, self._cancellable, self._search_albums_stmt,
            self._albums_search_model))
        asyncio.create_task(self._search_generic(
            text, self._cancellable, self._search_songs_stmt,
            self._songs_search_model))

    async def _search_generic(
            self, term: str, cancellable: Gio.Cancellable,
            statement: TSparql.SparqlStatement,
            model: Gtk.FilterListModel) -> None:
        """Search and fill the model with results"""
        async with self._notificationmanager:
            statement.bind_string("name", term)
            try:
                cursor = await statement.execute_async(cancellable)
            except GLib.Error as error:
                if not error.matches(
                        Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                    self._log.warning(
                        f"Error: {error.domain}, {error.message}")
                return

            filter_ids = []
            try:
                has_next = await cursor.next_async(cancellable)
            except GLib.Error as error:
                if not error.matches(
                        Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                    self._log.warning(
                        f"Error: {error.domain}, {error.message}")
                has_next = False
            while has_next:
                cursor_dict = utils.dict_from_cursor(cursor)
                filter_ids.append(cursor_dict.get("id"))

                try:
                    has_next = await cursor.next_async(cancellable)
                except GLib.Error as error:
                    if not error.matches(
                            Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                        self._log.warning(
                            f"Error: {error.domain}, {error.message}")
                    filter_ids = []
                    has_next = False

            cursor.close()

            def filter_func(coreobject: CoreObject) -> bool:
                return coreobject.props.id in filter_ids

            if len(filter_ids) == 0:
                custom_filter = Gtk.AnyFilter()
            else:
                custom_filter = Gtk.CustomFilter()
                custom_filter.set_filter_func(filter_func)

            model.set_filter(custom_filter)
            # If a search does not change the number of items found,
            # SearchView will not update without a signal.
            model.emit("items-changed", 0, 0, 0)

    def stage_playlist_deletion(self, playlist: Optional[Playlist]) -> None:
        """Prepares playlist deletion.

        :param Playlist playlist: playlist
        """
        if self._tsparql_playlists is None:
            return

        self._tsparql_playlists.stage_playlist_deletion(playlist)

    def finish_playlist_deletion(
            self, playlist: Playlist, deleted: bool) -> None:
        """Finishes playlist deletion.

        :param Playlist playlist: playlist
        :param bool deleted: indicates if the playlist has been deleted
        """
        if self._tsparql_playlists is None:
            return

        self._tsparql_playlists.finish_playlist_deletion(playlist, deleted)

    def create_playlist(
            self, playlist_title: str,
            callback: Callable[[Playlist], None]) -> None:
        """Creates a new user playlist.

        :param str playlist_title: playlist title
        :param callback: function to perform once, the playlist is created
        """
        if self._tsparql_playlists is None:
            return

        self._tsparql_playlists.create_playlist(playlist_title, callback)
