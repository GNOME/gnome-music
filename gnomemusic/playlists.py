# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Sai Suman Prayaga <suman.sai14@gmail.com>
# Copyright (c) 2013 Eslam Mostafa <cseslam@gmail.com>
# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
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


from gi.repository import Grl, GLib, GObject
from gnomemusic import TrackerWrapper
from gnomemusic.grilo import grilo
from gnomemusic.query import Query
from gettext import gettext as _
import inspect
import time
sparql_dateTime_format = "%Y-%m-%dT%H:%M:%SZ"

from gnomemusic import log
import logging
logger = logging.getLogger(__name__)


class StaticPlaylists:
    class MostPlayed:
        ID = None
        QUERY = Query.get_most_played_songs()
        TAG_TEXT = "MOST_PLAYED"
        # TRANSLATORS: this is a playlist name
        TITLE = _("Most Played")

    class NeverPlayed:
        ID = None
        QUERY = Query.get_never_played_songs()
        TAG_TEXT = "NEVER_PLAYED"
        # TRANSLATORS: this is a playlist name
        TITLE = _("Never Played")

    class RecentlyPlayed:
        ID = None
        QUERY = Query.get_recently_played_songs()
        TAG_TEXT = "RECENTLY_PLAYED"
        # TRANSLATORS: this is a playlist name
        TITLE = _("Recently Played")

    class RecentlyAdded:
        ID = None
        QUERY = Query.get_recently_added_songs()
        TAG_TEXT = "RECENTLY_ADDED"
        # TRANSLATORS: this is a playlist name
        TITLE = _("Recently Added")

    class Favorites:
        ID = None
        QUERY = Query.get_favorite_songs()
        TAG_TEXT = "FAVORITES"
        # TRANSLATORS: this is a playlist name
        TITLE = _("Favorite Songs")


class Playlists(GObject.GObject):
    __gsignals__ = {
        'playlist-created': (GObject.SIGNAL_RUN_FIRST, None, (Grl.Media,)),
        'playlist-deleted': (GObject.SIGNAL_RUN_FIRST, None, (Grl.Media,)),
        'playlist-updated': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
        'song-added-to-playlist': (
            GObject.SIGNAL_RUN_FIRST, None, (Grl.Media, Grl.Media)
        ),
        'song-removed-from-playlist': (
            GObject.SIGNAL_RUN_FIRST, None, (Grl.Media, Grl.Media)
        ),
    }
    instance = None
    tracker = None

    @classmethod
    def get_default(self, tracker=None):
        if self.instance:
            return self.instance
        else:
            self.instance = Playlists()
        return self.instance

    @log
    def __init__(self):
        GObject.GObject.__init__(self)
        self.tracker = TrackerWrapper().tracker

    @log
    def fetch_or_create_static_playlists(self):
        """For all static playlists: get ID, if exists; if not, create the playlist and get ID."""
        playlists = [cls for name, cls in inspect.getmembers(StaticPlaylists)
                     if inspect.isclass(cls) and not (name == "__class__")]  # hacky

        def callback(obj, result, playlist):
            cursor = obj.query_finish(result)
            while (cursor.next(None)):
                playlist.ID = cursor.get_integer(1)

            if not playlist.ID:
                # create the playlist
                playlist.ID = self.create_playlist_and_return_id(playlist.TITLE, playlist.TAG_TEXT)

            self.update_static_playlist(playlist)

        for playlist in playlists:
            self.tracker.query_async(
                Query.get_playlist_with_tag(playlist.TAG_TEXT), None,
                callback, playlist)

    @log
    def clear_playlist_with_id(self, playlist_id):
        query = Query.clear_playlist_with_id(playlist_id)
        self.tracker.update(query, GLib.PRIORITY_DEFAULT, None)

    @log
    def update_playcount(self, song_url):
        query = Query.update_playcount(song_url)
        self.tracker.update(query, GLib.PRIORITY_DEFAULT, None)

    @log
    def update_last_played(self, song_url):
        cur_time = time.strftime(sparql_dateTime_format, time.gmtime())
        query = Query.update_last_played(song_url, cur_time)
        self.tracker.update(query, GLib.PRIORITY_DEFAULT, None)

    @log
    def update_static_playlist(self, playlist):
        """Given a static playlist (subclass of StaticPlaylists), updates according to its query."""
        # Clear the playlist
        self.clear_playlist_with_id(playlist.ID)

        final_query = ''

        # Get a list of matching songs
        cursor = self.tracker.query(playlist.QUERY, None)
        if not cursor:
            return

        # For each song run 'add song to playlist'
        while cursor.next():
            uri = cursor.get_string(0)[0]
            final_query += Query.add_song_to_playlist(playlist.ID, uri)

        self.tracker.update_blank_async(final_query, GLib.PRIORITY_DEFAULT,
                                        None, None, None)

        # tell system we updated the playlist so playlist is reloaded
        self.emit('playlist-updated', playlist.ID)

    @log
    def update_all_static_playlists(self):
        playlists = [cls for name, cls in inspect.getmembers(StaticPlaylists)
                     if inspect.isclass(cls) and not (name == "__class__")]  # hacky

        for playlist in playlists:
            self.update_static_playlist(playlist)

    @log
    def create_playlist_and_return_id(self, title, tag_text):
        self.tracker.update_blank(Query.create_tag(tag_text), GLib.PRIORITY_DEFAULT, None)

        data = self.tracker.update_blank(
            Query.create_playlist_with_tag(title, tag_text), GLib.PRIORITY_DEFAULT,
            None)
        playlist_urn = data.get_child_value(0).get_child_value(0).\
            get_child_value(0).get_child_value(1).get_string()

        cursor = self.tracker.query(
            Query.get_playlist_with_urn(playlist_urn),
            None)
        if not cursor or not cursor.next():
            return
        return cursor.get_integer(0)

    @log
    def create_playlist(self, title):
        def get_callback(source, param, item, count, data, error):
            if item:
                self.emit('playlist-created', item)

        def query_callback(conn, res, data):
            cursor = conn.query_finish(res)
            if not cursor or not cursor.next():
                return
            playlist_id = cursor.get_integer(0)
            grilo.get_playlist_with_id(playlist_id, get_callback)

        def update_callback(conn, res, data):
            playlist_urn = conn.update_blank_finish(res)[0][0]['playlist']
            self.tracker.query_async(
                Query.get_playlist_with_urn(playlist_urn),
                None, query_callback, None
            )

        self.tracker.update_blank_async(
            Query.create_playlist(title), GLib.PRIORITY_DEFAULT,
            None, update_callback, None
        )

    @log
    def delete_playlist(self, item):
        def update_callback(conn, res, data):
            conn.update_finish(res)
            self.emit('playlist-deleted', item)

        self.tracker.update_async(
            Query.delete_playlist(item.get_id()), GLib.PRIORITY_DEFAULT,
            None, update_callback, None
        )

    @log
    def add_to_playlist(self, playlist, items):
        def get_callback(source, param, item, count, data, error):
            if item:
                self.emit('song-added-to-playlist', playlist, item)

        def query_callback(conn, res, data):
            cursor = conn.query_finish(res)
            if not cursor or not cursor.next():
                return
            entry_id = cursor.get_integer(0)
            grilo.get_playlist_song_with_id(
                playlist.get_id(), entry_id, get_callback
            )

        def update_callback(conn, res, data):
            entry_urn = conn.update_blank_finish(res)[0][0]['entry']
            self.tracker.query_async(
                Query.get_playlist_song_with_urn(entry_urn),
                None, query_callback, None
            )

        for item in items:
            uri = item.get_url()
            if not uri:
                continue
            self.tracker.update_blank_async(
                Query.add_song_to_playlist(playlist.get_id(), uri),
                GLib.PRIORITY_DEFAULT,
                None, update_callback, None
            )

    @log
    def remove_from_playlist(self, playlist, items):
        def update_callback(conn, res, data):
            conn.update_finish(res)
            self.emit('song-removed-from-playlist', playlist, data)

        for item in items:
            self.tracker.update_async(
                Query.remove_song_from_playlist(
                    playlist.get_id(), item.get_id()
                ),
                GLib.PRIORITY_DEFAULT,
                None, update_callback, item
            )
