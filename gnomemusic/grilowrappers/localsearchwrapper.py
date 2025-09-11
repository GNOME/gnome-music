# Copyright 2025 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from typing import List, Union
import typing
import asyncio

from gi.repository import Grl, Gio, Gtk, GLib, GObject

from gnomemusic.corealbum import CoreAlbum
from gnomemusic.coreartist import CoreArtist
from gnomemusic.coredisc import CoreDisc
from gnomemusic.coresong import CoreSong
from gnomemusic.trackerwrapper import TrackerWrapper
import gnomemusic.utils as utils
if typing.TYPE_CHECKING:
    from gi.repository import TSparql
    from gnomemusic.application import Application
    CoreObject = Union[CoreAlbum, CoreArtist, CoreSong]


class LocalSearchWrapper(GObject.Object):
    """LocalSearch based data source
    """

    __gtype_name__ = "LocalSearchWrapper"

    def __init__(
            self, application: Application,
            trackerwrapper: TrackerWrapper) -> None:
        """Init LocalSearchWrapper
        """
        super().__init__()

        self._application = application
        self._log = application.props.log
        self._notificationmanager = application.props.notificationmanager
        self._tsparql = trackerwrapper.props.local_db
        self._tsparqlwrapper = trackerwrapper

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
            self._albums_model)
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

    def _prepare_statement(self, resource_path: str) -> str:
        """Helper to insert bus name and location filter in query"""
        gbytes = Gio.resources_lookup_data(
            resource_path, Gio.ResourceLookupFlags.NONE)
        query_str = gbytes.get_data().decode("utf-8")
        query_str = query_str.replace(
            "{bus_name}", self._tsparqlwrapper.props.miner_fs_busname)
        query_str = query_str.replace(
            "{location_filter}", self._tsparqlwrapper.location_filter())

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
                media = utils.create_grilo_media_from_cursor(
                    cursor, Grl.MediaType.CONTAINER)
                corealbum = CoreAlbum(self._application, media)

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
                media = utils.create_grilo_media_from_cursor(
                    cursor, Grl.MediaType.CONTAINER)
                coreartist = CoreArtist(self._application, media)

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

            try:
                has_next = await cursor.next_async()
            except GLib.Error as error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                has_next = False
            while has_next:
                media = utils.create_grilo_media_from_cursor(
                    cursor, Grl.MediaType.AUDIO)
                coresong = CoreSong(self._application, media)

                self._songs_model.append(coresong)

                try:
                    has_next = await cursor.next_async()
                except GLib.Error as error:
                    self._log.warning(
                        f"Error: {error.domain}, {error.message}")
                    has_next = False

            cursor.close()

    async def _get_album_discs(
            self, media: Grl.Media, disc_model: Gtk.SortListModel) -> None:
        async with self._notificationmanager:
            album_id = media.get_id()
            self._album_discs_stmt.bind_string("album_id", album_id)
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
                new_media = utils.create_grilo_media_from_cursor(
                    cursor, Grl.MediaType.CONTAINER)
                nr = new_media.get_album_disc_number()
                coredisc = CoreDisc(self._application, media, nr)

                disc_model.append(coredisc)

                try:
                    has_next = await cursor.next_async()
                except GLib.Error as error:
                    self._log.warning(
                        f"Error: {error.domain}, {error.message}")
                    has_next = False

            cursor.close()

    def get_album_discs(
            self, media: Grl.Media, disc_model: Gtk.SortListModel) -> None:
        """Get all discs of an album

        :param Grl.Media media: The media with the album id
        :param Gtk.SortListModel disc_model: The model to fill
        """
        asyncio.create_task(self._get_album_discs(media, disc_model))

    async def _get_album_disc(
            self, media: Grl.Media, disc_nr: int,
            model: Gtk.FilterListModel) -> None:
        async with self._notificationmanager:
            self._album_disc_stmt.bind_string("album_id", media.get_id())
            self._album_disc_stmt.bind_int("disc_nr", disc_nr)
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
                new_media = utils.create_grilo_media_from_cursor(
                    cursor, Grl.MediaType.CONTAINER)
                disc_song_ids.append(
                    new_media.get_source() + new_media.get_id())

                try:
                    has_next = await cursor.next_async()
                except GLib.Error as error:
                    self._log.warning(
                        f"Error: {error.domain}, {error.message}")
                    has_next = False

            cursor.close()

            def _filter_func(coresong: CoreSong) -> bool:
                return coresong.props.grlid in disc_song_ids

            custom_filter = Gtk.CustomFilter()
            custom_filter.set_filter_func(_filter_func)
            model.set_filter(custom_filter)

    def get_album_disc(
            self, media: Grl.Media, disc_nr: int,
            model: Gtk.FilterListModel) -> None:
        """Get all songs of an album disc

        :param Grl.Media media: The media with the album id
        :param int disc_nr: The disc number
        :param Gtk.FilterListModel model: The model to fill
        """
        asyncio.create_task(self._get_album_disc(media, disc_nr, model))

    async def _get_artist_albums(
            self, media: Grl.Media, model: Gtk.FilterListModel) -> None:
        async with self._notificationmanager:
            artist = media.get_id()
            self._artist_albums_stmt.bind_string("artist", artist)
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
                new_media = utils.create_grilo_media_from_cursor(
                    cursor, Grl.MediaType.CONTAINER)
                album_ids.append(new_media.get_id())

                try:
                    has_next = await cursor.next_async()
                except GLib.Error as error:
                    self._log.warning(
                        f"Error: {error.domain}, {error.message}")
                    has_next = False

            cursor.close()

        def albums_filter(corealbum: CoreAlbum, albums: List[str]) -> bool:
            return corealbum.props.media.get_id() in albums

        custom_filter = Gtk.CustomFilter()
        custom_filter.set_filter_func(albums_filter, album_ids)
        model.set_filter(custom_filter)

    def get_artist_albums(
            self, media: Grl.Media, model: Gtk.FilterListModel) -> None:
        """Get all albums by an artist

        :param Grl.Media media: The media with the artist id
        :param Gtk.FilterListModel model: The model to fill
        """
        asyncio.create_task(self._get_artist_albums(media, model))

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
                new_media = utils.create_grilo_media_from_cursor(
                    cursor, Grl.MediaType.CONTAINER)
                filter_ids.append(new_media.get_id())

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
                return coreobject.props.media.get_id() in filter_ids

            if len(filter_ids) == 0:
                custom_filter = Gtk.AnyFilter()
            else:
                custom_filter = Gtk.CustomFilter()
                custom_filter.set_filter_func(filter_func)

            model.set_filter(custom_filter)
