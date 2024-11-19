# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from collections.abc import Callable
from typing import Optional

import gi
gi.require_versions({"Grl": "0.3", "Tracker": "3.0"})
from gi.repository import Gio, Grl, Gtk, GLib, GObject, Tracker

from gnomemusic.grilowrappers.playlist import Playlist
from gnomemusic.grilowrappers.smartplaylist import (
    AllSongs, InsufficientTagged, Favorites, RecentlyAdded, RecentlyPlayed,
    NeverPlayed, MostPlayed)
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
