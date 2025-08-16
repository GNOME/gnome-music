# Copyright 2025 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from typing import Callable, Dict, List, Optional
import typing
import asyncio

import gi
gi.require_versions({"Tracker": "3.0"})
from gi.repository import Grl, Gio, Gtk, GLib, GObject, Tracker

from gnomemusic.corealbum import CoreAlbum
from gnomemusic.coreartist import CoreArtist
from gnomemusic.coredisc import CoreDisc
from gnomemusic.coresong import CoreSong
from gnomemusic.grilowrappers.grltrackerplaylists import (
    GrlTrackerPlaylists, Playlist)
from gnomemusic.storeart import StoreArt
from gnomemusic.trackerwrapper import TrackerWrapper
from gnomemusic.utils import CoreObjectType
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.coremodel import CoreModel
    from gnomemusic.musiclogger import MusicLogger
    from gnomemusic.notificationmanager import NotificationManager
import gnomemusic.utils as utils


class LocalSearchWrapper(GObject.Object):

    __gtype_name__ = "LocalSearchWrapper"

    def __init__(
        self, application: Application,
        trackerwrapper: TrackerWrapper) -> None:
        """
        """
        super().__init__()

        self._application = application
        self._log = application.props.log
        self._tracker = trackerwrapper.props.local_db
        self._trackerwrapper = trackerwrapper

        self._albums_model = Gio.ListStore.new(CoreAlbum)
        self._artists_model = Gio.ListStore.new(CoreArtist)
        self._songs_model = Gio.ListStore.new(CoreSong)

        cm = application.props.coremodel
        cm.props.albums_proxy.append(self._albums_model)
        cm.props.artists_proxy.append(self._artists_model)
        cm.props.songs_proxy.append(self._songs_model)

        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/albums.rq")
        self._albums_stmt = self._tracker.query_statement(prep_stmt)

        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/artists.rq")
        self._artists_stmt = self._tracker.query_statement(prep_stmt)

        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/songs.rq")
        self._songs_stmt = self._tracker.query_statement(prep_stmt)

        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/album_discs.rq")
        self._album_discs_stmt = self._tracker.query_statement(prep_stmt)

        asyncio.create_task(self._init_albums_model())
        asyncio.create_task(self._init_artists_model())
        asyncio.create_task(self._init_songs_model())

    def _prepare_statement(self, resource_path: str) -> str:
        """Helper to insert bus name and location filter in query"""
        gbytes = Gio.resources_lookup_data(
            resource_path, Gio.ResourceLookupFlags.NONE)
        query_str = gbytes.get_data().decode("utf-8")
        query_str = query_str.replace(
            "{bus_name}", self._trackerwrapper.props.miner_fs_busname)
        query_str = query_str.replace(
            "{location_filter}", self._trackerwrapper.location_filter())

        return query_str

    async def _init_albums_model(self) -> None:
        try:
            cursor = await self._albums_stmt.execute_async()
        except GLib.Error as error:
            print("log")

        has_next = await cursor.next_async()
        while has_next:
            media = utils.create_grilo_media_from_cursor(
                cursor, Grl.MediaType.CONTAINER)
            corealbum = CoreAlbum(self._application, media)

            self._albums_model.append(corealbum)

            has_next = await cursor.next_async()

        cursor.close()

    async def _init_artists_model(self) -> None:
        try:
            cursor = await self._artists_stmt.execute_async()
        except GLib.Error as error:
            print("log")

        has_next = await cursor.next_async()
        while has_next:
            media = utils.create_grilo_media_from_cursor(
                cursor, Grl.MediaType.CONTAINER)
            coreartist = CoreArtist(self._application, media)

            self._artists_model.append(coreartist)

            has_next = await cursor.next_async()

        cursor.close()

    async def _init_songs_model(self) -> None:
        try:
            cursor = await self._songs_stmt.execute_async()
        except GLib.Error as error:
            print("log")

        has_next = await cursor.next_async()
        while has_next:
            media = utils.create_grilo_media_from_cursor(
                cursor, Grl.MediaType.AUDIO)
            coresong = CoreSong(self._application, media)

            self._songs_model.append(coresong)

            has_next = await cursor.next_async()

        cursor.close()

    def get_album_discs(
            self, media: Grl.Media, disc_model: Gtk.SortListModel) -> None:
        """Get all discs of an album

        :param Grl.Media media: The media with the album id
        :param Gtk.SortListModel disc_model: The model to fill
        """
        async def _get_album_discs_internal():
            album_id = media.get_id()
            print("internal", album_id)
            self._album_discs_stmt.bind_string("aurn", album_id)
            print(self._album_discs_stmt.get_sparql())
            try:
                cursor = await self._album_discs_stmt.execute_async()
            except GLib.Error as error:
                print("log", error.message, error.domain)
                return

            has_next = await cursor.next_async()
            while has_next:
                new_media = utils.create_grilo_media_from_cursor(
                    cursor, Grl.MediaType.CONTAINER)
                nr = new_media.get_album_disc_number()

                coredisc = CoreDisc(self._application, media, nr)

                disc_model.append(coredisc)

                has_next = await cursor.next_async()

            cursor.close()

        asyncio.create_task(_get_album_discs_internal())

    def search(self, text: str) -> None:
        """Search for the given string in the wrappers

        If an empty string is provided, the wrapper should
        reset to an empty state.

        :param str text: The search string
        """
        pass
