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
import gnomemusic.utils as utils
from gettext import gettext as _
import inspect
import time
sparql_dateTime_format = "%Y-%m-%dT%H:%M:%SZ"

from gnomemusic import log
import logging
logger = logging.getLogger(__name__)


class Playlist(GObject.Object):
    """ Base class of static and intelligent playlists """

    __gproperties__ = {
        'id': (str, 'Identifier', 'id', '', GObject.ParamFlags.READWRITE),
        'query': (str, 'Query', 'query', '', GObject.ParamFlags.READWRITE),
        'tag_text': (str, 'Tag', 'tag', '', GObject.ParamFlags.READWRITE),
        'title': (str, 'Title', 'title', '', GObject.ParamFlags.READWRITE),
        'is_static': (bool, 'Is static', 'is static', False, GObject.ParamFlags.READWRITE),
    }

    @log
    def __init__(self, id=None, title=None, query=None, tag_text=None):
        GObject.Object.__init__(self)

        self.id = id
        self.query = query
        self.tag_text = tag_text
        self.title = title
        self.is_static = False


class StaticPlaylist(Playlist):
    """Base class for static playlists"""
    @log
    def __init__(self):
        Playlist.__init__(self)

        self.is_static = True


class MostPlayed(StaticPlaylist):
    """Most Played static playlist"""
    @log
    def __init__(self):
        StaticPlaylist.__init__(self)

        self.tag_text = "MOST_PLAYED"
        # TRANSLATORS: this is a playlist name
        self.title = _("Most Played")
        self.query = Query.get_never_played_songs()


class NeverPlayed(StaticPlaylist):
    """Never Played static playlist"""
    @log
    def __init__(self):
        StaticPlaylist.__init__(self)

        self.tag_text = "NEVER_PLAYED"
        # TRANSLATORS: this is a playlist name
        self.title = _("Never Played")
        self.query = Query.get_never_played_songs()


class RecentlyPlayed(StaticPlaylist):
    """Recently Played static playlist"""
    @log
    def __init__(self):
        StaticPlaylist.__init__(self)

        self.tag_text = "RECENTLY_PLAYED"
        # TRANSLATORS: this is a playlist name
        self.title = _("Recently Played")
        self.query = Query.get_recently_played_songs()


class RecentlyAdded(StaticPlaylist):
    """Recently Added static playlist"""
    @log
    def __init__(self):
        StaticPlaylist.__init__(self)

        self.tag_text = "RECENTLY_ADDED"
        # TRANSLATORS: this is a playlist name
        self.title = _("Recently Added")
        self.query = Query.get_recently_added_songs()


class Favorites(StaticPlaylist):
    """Favories static playlist"""
    @log
    def __init__(self):
        StaticPlaylist.__init__(self)

        self.tag_text = "FAVORITES"
        # TRANSLATORS: this is a playlist name
        self.title = _("Favorite Songs")
        self.query = Query.get_favorite_songs()


class StaticPlaylists:

    def __repr__(self):
        return '<StaticPlaylists>'

    def __init__(self):
        Query()
        self.MostPlayed = MostPlayed()
        self.NeverPlayed = NeverPlayed()
        self.RecentlyPlayed = RecentlyPlayed()
        self.RecentlyAdded = RecentlyAdded()
        self.Favorites = Favorites()

        self.playlists = [self.MostPlayed, self.NeverPlayed,
                          self.RecentlyPlayed, self.RecentlyAdded,
                          self.Favorites]

    @log
    def get_ids(self):
        """Get all static playlist IDs

        :return: A list of tracker.id's
        :rtype: A list of integers
        """
        return [str(playlist.id) for playlist in self.playlists]


class Playlists(GObject.GObject):
    __gsignals__ = {
        'playlist-added': (GObject.SignalFlags.RUN_FIRST, None, (Playlist,)),
        'playlist-deleted': (GObject.SignalFlags.RUN_FIRST, None, (Playlist,)),
        'playlist-updated': (GObject.SignalFlags.RUN_FIRST, None, (Playlist,)),
        'song-added-to-playlist': (
            GObject.SignalFlags.RUN_FIRST, None, (Grl.Media, Grl.Media)
        ),
        'song-removed-from-playlist': (
            GObject.SignalFlags.RUN_FIRST, None, (Grl.Media, Grl.Media)
        ),
    }

    __gproperties__ = {
        'ready': (bool, 'Ready', 'ready', False, GObject.ParamFlags.READABLE),
    }

    instance = None
    tracker = None

    def __repr__(self):
        return '<Playlists>'

    @classmethod
    def get_default(cls, tracker=None):
        if cls.instance:
            return cls.instance
        else:
            cls.instance = Playlists()
        return cls.instance

    @log
    def __init__(self):
        GObject.GObject.__init__(self)
        self.tracker = TrackerWrapper().tracker
        self._static_playlists = StaticPlaylists()
        self.playlists = {}
        self.ready = False

        self._loading_counter = len(self._static_playlists.playlists)
        self._user_playlists_ready = False

        grilo.connect('ready', self._on_grilo_ready)

    @log
    def _on_grilo_ready(self, data=None):
        """For all static playlists: get ID, if exists; if not, create the playlist and get ID."""

        def playlist_id_fetched_cb(cursor, res, playlist):
            """ Called after the playlist id is fetched """
            try:
                cursor.next_finish(res)
            except GLib.Error as error:
                logger.warn("Error: %s, %s", err.__class__, err)
                return

            playlist.id = cursor.get_integer(1)

            if not playlist.id:
                # Create the  static playlist
                self._create_static_playlist(playlist)
            else:
                # Update playlist
                self.update_static_playlist(playlist)

        def callback(obj, result, playlist):
            """ Starts retrieving the playlist id """
            try:
                cursor = obj.query_finish(result)
            except GLib.Error as error:
                logger.warn("Error: %s, %s", err.__class__, err)
                return

            # Search for the playlist ID
            cursor.next_async(None, playlist_id_fetched_cb, playlist)

        # Start fetching all the static playlists
        for playlist in self._static_playlists.playlists:
            self.tracker.query_async(
                Query.get_playlist_with_tag(playlist.tag_text), None,
                callback, playlist)

        # Gather the available playlists too
        grilo.populate_playlists(0, self._populate_playlists_finish_cb)

    @log
    def _populate_playlists_finish_cb(self, source, param, item, remaining=0, data=None):
        """Fill in the list of playlists currently available"""

        if not item:
            self._user_playlists_ready = True
            self._check_ready()
            return

        # We may hit the case of already having a static playlist added. Since
        # the static playlist has higher priority, we simply quit when they're
        # already added
        if item.get_id() in self.playlists:
            return

        playlist = Playlist(item.get_id(), utils.get_media_title(item))
        playlist.grilo_item = item

        self.playlists[playlist.id] = playlist
        self.emit('playlist-added', playlist)

    @log
    def _create_static_playlist(self, playlist):
        """ Create the tag and the static playlist, and fetch the newly created
        playlist's songs.
        """
        title = playlist.title
        tag_text = playlist.tag_text

        def playlist_next_async_cb(cursor, res, playlist):
            """ Called after we finished moving the Tracker cursor, and ready
            to retrieve the playlist id"""
            # Update the playlist ID
            try:
                cursor.next_finish(res)
            except GLib.Error as error:
                logger.warn("Error: %s, %s", err.__class__, err)
                return

            playlist.id = cursor.get_integer(0)

            # Fetch the playlist contents
            self.update_static_playlist(playlist)

        def playlist_queried_cb(obj, res, playlist):
            """ Called after the playlist is created and the ID is fetched """
            try:
                cursor = obj.query_finish(res)
            except GLib.Error as error:
                logger.warn("Error: %s, %s", err.__class__, err)
                return

            cursor.next_async(None, playlist_next_async_cb, playlist)

        def playlist_created_cb(obj, res, playlist):
            """ Called when the static playlist is created """
            data = obj.update_blank_finish(res)
            playlist_urn = data.get_child_value(0).get_child_value(0).\
                           get_child_value(0).get_child_value(1).get_string()

            query = Query.get_playlist_with_urn(playlist_urn)

            # Start fetching the playlist
            self.tracker.query_async(query, None, playlist_queried_cb, playlist)

        def tag_created_cb(obj, res, playlist):
            """ Called when the tag is created """
            creation_query = Query.create_playlist_with_tag(title, tag_text)

            # Start creating the playlist itself
            self.tracker.update_blank_async(creation_query, GLib.PRIORITY_LOW,
                                            None, playlist_created_cb, playlist)

        # Start the playlist creation by creating the tag
        self.tracker.update_blank_async(Query.create_tag(tag_text),
                                        GLib.PRIORITY_LOW, None,
                                        tag_created_cb, playlist)

    @log
    def update_static_playlist(self, playlist):
        """Given a static playlist (subclass of StaticPlaylists), updates according to its query."""
        # Clear the playlist
        self.clear_playlist(playlist)

    @log
    def clear_playlist(self, playlist):
        """Starts cleaning the playlist"""
        query = Query.clear_playlist_with_id(playlist.id)
        self.tracker.update_async(query, GLib.PRIORITY_LOW, None,
                                  self._static_playlist_cleared_cb, playlist)

    @log
    def _static_playlist_cleared_cb(self, connection, res, playlist):
        """After clearing the playlist, start querying the playlist's songs"""
        # Get a list of matching songs
        self.tracker.query_async(playlist.query, None,
                                 self._static_playlist_query_cb, playlist)

    @log
    def _static_playlist_query_cb(self, connection, res, playlist):
        """Fetch the playlist's songs"""
        final_query = ''

        # Get a list of matching songs
        try:
            cursor = connection.query_finish(res)
        except GLib.Error as err:
            logger.warn("Error: %s, %s", err.__class__, err)
            return

        def callback(cursor, res, final_query):
            uri = cursor.get_string(0)[0]
            final_query += Query.add_song_to_playlist(playlist.id, uri)

            try:
                has_next = cursor.next_finish(res)
            except GLib.Error as err:
                logger.warn("Error: %s, %s", err.__class__, err)
                has_next = False

            # Only perform the update when the cursor reached the end
            if has_next:
                cursor.next_async(None, callback, final_query)
                return

            self.tracker.update_blank_async(final_query, GLib.PRIORITY_LOW,
                                            None, None, None)

            # If the list is not here yet, emit :playlist-added - otherwise,
            # emit :playlist-updated so we reload the list
            if not playlist.id in self.playlists:
                signal_name = 'playlist-added'
            else:
                signal_name = 'playlist-updated'

            # Add the playlist to the cache
            self.playlists[playlist.id] = playlist
            self.emit(signal_name, playlist)

            # Check if we're ready
            self._loading_counter = self._loading_counter - 1
            self._check_ready()

        # Asynchronously form the playlist's final query
        cursor.next_async(None, callback, final_query)

    @log
    def update_all_static_playlists(self):
        for playlist in self._static_playlists.playlists:
            self.update_static_playlist(playlist)

    @log
    def create_playlist(self, title):
        def get_callback(source, param, item, count, data, error):
            if item:
                new_playlist = Playlist(item.get_id(), utils.get_media_title(item))
                new_playlist.grilo_item = item

                self.playlists[new_playlist] = new_playlist
                self.emit('playlist-added', playlist)

        def cursor_callback(cursor, res, data):
            try:
                has_next = cursor.next_finish()
            except GLib.Error as err:
                logger.warn("Error: %s, %s", err.__class__, err)
                return

            if has_next:
                cursor.next_async(None, cursor_callback, data)
                return

            playlist_id = cursor.get_integer(0)
            grilo.get_playlist_with_id(playlist_id, get_callback)

        def query_callback(conn, res, data):
            try:
                cursor = conn.query_finish(res)
            except GLib.Error as err:
                logger.warn("Error: %s, %s", err.__class__, err)
                return

            if not cursor:
                return

            cursor.next_async(None, cursor_callback, data)

        def update_callback(conn, res, data):
            playlist_urn = conn.update_blank_finish(res)[0][0]['playlist']
            self.tracker.query_async(
                Query.get_playlist_with_urn(playlist_urn),
                None, query_callback, None
            )

        self.tracker.update_blank_async(
            Query.create_playlist(title), GLib.PRIORITY_LOW,
            None, update_callback, None
        )

    @log
    def delete_playlist(self, playlist):
        def update_callback(conn, res, data):
            try:
                conn.update_finish(res)
                self.emit('playlist-deleted', self.playlists[playlist.id])
                del self.playlists[playlist.id]
            except GLib.Error as error:
                logger.warn("Error: %s, %s", error.__class__, error)

        self.tracker.update_async(
            Query.delete_playlist(playlist.id), GLib.PRIORITY_LOW,
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
                GLib.PRIORITY_LOW,
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
                    playlist.id, item.get_id()
                ),
                GLib.PRIORITY_LOW,
                None, update_callback, item
            )

    @log
    def get_playlists(self):
        """Retrieves the currently loaded playlists.

        :return: a list of Playlists
        :rtype: list
        """
        return self.playlists.values()

    @log
    def is_static_playlist(self, playlist):
        """Checks whether the given playlist is static or not

        :return: True if the playlist is static
        :rtype: bool
        """
        for static_playlist_id in self._static_playlists.get_ids():
            if playlist.get_id() == static_playlist_id:
                return True

        return False

    @log
    def do_get_property(self, property):
        if property.name == 'ready':
            return self.ready
        else:
            raise AttributeError('Unknown property %s' % property.name)

    @log
    def do_set_property(self, property, value):
        raise AttributeError('Unknown property %s' % property.name)

    @log
    def _check_ready(self):
        ready = self._user_playlists_ready and self._loading_counter == 0

        if ready != self.ready:
            self.ready = ready
            self.notify('ready')
