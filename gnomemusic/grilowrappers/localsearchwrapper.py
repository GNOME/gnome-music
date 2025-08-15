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

        cm = application.props.coremodel
        cm.albums_proxy.append(self._albums_model)

        prep_stmt = self._prepare_statement(
            "/org/gnome/Music/queries/albums.rq")
        self._albums_stmt = self._tracker.query_statement(prep_stmt)

        asyncio.create_task(self._init_albums_model())

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
