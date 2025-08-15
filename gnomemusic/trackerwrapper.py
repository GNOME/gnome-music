# Copyright 2019 The GNOME Music developers
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
import asyncio
import os
import typing
from enum import IntEnum
from typing import Optional

import gi
gi.require_versions({"Tracker": "3.0"})
from gi.repository import Gio, GLib, GObject, Tracker

if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.coresong import CoreSong


class TrackerState(IntEnum):
    """Tracker Status
    """
    AVAILABLE = 0
    UNAVAILABLE = 1
    OUTDATED = 2


class TrackerWrapper(GObject.GObject):
    """Holds the connection to TinySparql.

    Setup the connection to TinySparql in host and flaptpak mode.

    Also provides some helper functions to query and update the
    TinySparql database.
    """

    def __init__(self, application: Application) -> None:
        """Create a connection to an instance of Tracker

        :param Application application: The application object
        """
        super().__init__()

        self._log = application.props.log
        self._application_id = application.props.application_id

        self._local_db: Tracker.SparqlConnection = None
        self._local_db_available = TrackerState.UNAVAILABLE

        self._miner_fs: Tracker.SparqlConnection = None
        self._miner_fs_busname = ""
        self._miner_fs_available = TrackerState.UNAVAILABLE

        asyncio.create_task(self._setup_local_db())
        asyncio.create_task(self._setup_host_miner_fs())

    @staticmethod
    def _in_flatpak() -> bool:
        """Indicates if Music is running as flatpak

        :returns: True if running as flatpak.
        :rtype: bool
        """
        return os.path.exists("/.flatpak-info")

    async def _setup_host_miner_fs(self) -> None:
        self._miner_fs_busname = "org.freedesktop.Tracker3.Miner.Files"

        self._log.debug(
            "Connecting to session-wide Tracker indexer at {}".format(
                self._miner_fs_busname))

        try:
            self._miner_fs = Tracker.SparqlConnection.bus_new(
                self._miner_fs_busname, None, None)
            self._log.info("Using session-wide tracker-miner-fs-3")
            self._miner_fs_available = TrackerState.AVAILABLE
            self.notify("tracker-available")
        except GLib.Error as error:
            self._log.warning(
                "Could not connect to host Tracker miner-fs at {}: {}".format(
                    self._miner_fs_busname, error))
            if self._in_flatpak():
                self._setup_local_miner_fs()
            else:
                self._miner_fs_busname = ""
                self.notify("tracker-available")

    def _setup_local_miner_fs(self) -> None:
        self._miner_fs_busname = self._application_id + ".Tracker3.Miner.Files"
        self._log.debug(
            "Connecting to bundled Tracker indexer at {}".format(
                self._miner_fs_busname))

        # Calling self._application.get_dbus_connection() seems to return None
        # here, so get the bus directly from Gio.
        Gio.bus_get(Gio.BusType.SESSION, None,
                    self._setup_local_bus_connection_cb)

    def _setup_local_bus_connection_cb(self, klass, result):
        # Query callback for _setup_local_miner_fs() to connect to session bus
        bus = Gio.bus_get_finish(result)

        miner_fs_startup_timeout_msec = 30 * 1000
        miner_fs_object_path = "/org/freedesktop/Tracker3/Miner/Files"

        bus.call(
            self._miner_fs_busname, miner_fs_object_path,
            "org.freedesktop.DBus.Peer", "Ping", None, None,
            Gio.DBusCallFlags.NONE, miner_fs_startup_timeout_msec, None,
            self._setup_local_miner_fs_ping_cb)

    def _setup_local_miner_fs_ping_cb(
            self, klass: Gio.DBusProxy, result: Gio.AsyncResult) -> None:
        try:
            klass.call_finish(result)
            self._log.info("Using bundled tracker-miner-fs-3")
            self._miner_fs = Tracker.SparqlConnection.bus_new(
                self._miner_fs_busname, None, None)
            self._miner_fs_available = TrackerState.AVAILABLE
            self.notify("tracker-available")
        except GLib.Error as error:
            self._log.warning(
                "Could not start local Tracker miner-fs at {}: {}".format(
                    self._miner_fs_busname, error))
            self._miner_fs_busname = ""
            self.notify("tracker-available")

    async def _setup_local_db(self) -> None:
        # Open a local Tracker database.
        try:
            self._local_db = Tracker.SparqlConnection.new(
                Tracker.SparqlConnectionFlags.NONE,
                Gio.File.new_for_path(self.cache_directory()),
                Tracker.sparql_get_ontology_nepomuk(),
                None)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self.notify("tracker-available")
            return

        # Version checks against the local version of Tracker can be done
        # here, set `self._tracker_available = TrackerState.OUTDATED` if the
        # checks fail.
        self._local_db_available = TrackerState.AVAILABLE
        self.notify("tracker-available")

    def cache_directory(self) -> str:
        """Get directory which contains Music private data.

        :returns: private store path
        :rtype: str
        """
        return GLib.build_pathv(
            GLib.DIR_SEPARATOR_S,
            [GLib.get_user_cache_dir(), "gnome-music", "db"])

    @GObject.Property(
        type=Tracker.SparqlConnection, flags=GObject.ParamFlags.READABLE)
    def miner_fs(self) -> Tracker.SparqlConnection:
        return self._miner_fs

    @GObject.Property(type=str, flags=GObject.ParamFlags.READABLE)
    def miner_fs_busname(self) -> str:
        return self._miner_fs_busname

    @GObject.Property(type=object, flags=GObject.ParamFlags.READABLE)
    def local_db(self) -> Tracker.SparqlConnection:
        return self._local_db

    @GObject.Property(
        type=int, default=TrackerState.UNAVAILABLE,
        flags=GObject.ParamFlags.READABLE)
    def tracker_available(self) -> TrackerState:
        """Get Tracker availability.

        :returns: tracker availability
        :rtype: TrackerState
        """
        if (self._local_db_available == TrackerState.AVAILABLE
                and self._miner_fs_available == TrackerState.AVAILABLE):
            return TrackerState.AVAILABLE
        elif (self._local_db_available == TrackerState.OUTDATED
                or self._miner_fs_available == TrackerState.OUTDATED):
            return TrackerState.OUTDATED
        else:
            return TrackerState.UNAVAILABLE

    def location_filter(self) -> Optional[str]:
        """Get a SPARQL query filter for files in XDG_MUSIC only."""
        try:
            music_dir = GLib.get_user_special_dir(
                GLib.UserDirectory.DIRECTORY_MUSIC)
            assert music_dir is not None
        except (TypeError, AssertionError):
            self._log.message("XDG Music dir is not set")
            return None

        music_dir = Tracker.sparql_escape_string(
            GLib.filename_to_uri(music_dir))

        query = "FILTER (STRSTARTS(nie:isStoredAs(?song), '{}/'))".format(
            music_dir)

        return query

    async def _update_favorite(self, coresong: CoreSong) -> None:
        if coresong.props.favorite:
            update = """
            INSERT DATA {
                <%(urn)s> a nmm:MusicPiece ;
                          nao:hasTag nao:predefined-tag-favorite .
            }
            """.replace("\n", "").strip() % {
                "urn": coresong.props.id,
            }
        else:
            update = """
            DELETE DATA {
                <%(urn)s> nao:hasTag nao:predefined-tag-favorite .
            }
            """.replace("\n", "").strip() % {
                "urn": coresong.props.id,
            }

        try:
            await self._local_db.update_async(update)
        except GLib.Error as error:
            self._log.warning(
                f"Unable to update favorite: {error.domain}, {error.message}")

    async def _update_play_count(self, coresong: CoreSong) -> None:
        update = """
        DELETE WHERE {
            <%(urn)s> nie:usageCounter ?count .
        };
        INSERT DATA {
            <%(urn)s> a nmm:MusicPiece ;
                      nie:usageCounter %(count)d .
        }
        """.replace("\n", "").strip() % {
            "urn": coresong.props.id,
            "count": coresong.props.play_count,
        }

        try:
            await self._local_db.update_async(update)
        except GLib.Error as error:
            self._log.warning(
                f"Unable to update play count: "
                f"{error.domain}, {error.message}")

    async def _update_last_played(self, coresong: CoreSong) -> None:
        last_played = coresong.props.last_played.format_iso8601()
        update = """
        DELETE WHERE {
            <%(urn)s> nie:contentAccessed ?accessed
        };
        INSERT DATA {
            <%(urn)s> a nmm:MusicPiece ;
                      nie:contentAccessed "%(last_played)s"
        }
        """.replace("\n", "").strip() % {
            "urn": coresong.props.id,
            "last_played": last_played,
        }

        try:
            await self._local_db.update_async(update)
        except GLib.Error as error:
            self._log.warning(
                f"Unable to update last played: "
                f"{error.domain}, {error.message}")

    def update_tag(self, coresong: CoreSong, tag: str) -> None:
        """Update property of a resource.

        :param CoreSong coresong: CoreSong with updated tag
        :param str tag: tag to update
        """
        if tag == "favorite":
            asyncio.create_task(self._update_favorite(coresong))
        elif tag == "last-played":
            asyncio.create_task(self._update_last_played(coresong))
        elif tag == "play-count":
            asyncio.create_task(self._update_play_count(coresong))
        else:
            self._log.warning("Unknown tag: '{}'".format(tag))
