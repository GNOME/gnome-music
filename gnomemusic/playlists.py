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


import gi
gi.require_version('Grl', '0.3')
from gi.repository import Grl, GLib, GObject
from gnomemusic.grilo import grilo
from gnomemusic.query import Query
from gettext import gettext as _
import inspect

from gnomemusic import log
import logging
logger = logging.getLogger(__name__)


class Playlist(GObject.GObject):
    """ Base class of all playlists """
    ID = None
    QUERY = None
    TAG_TEXT = ""
    TITLE = ""

    def __repr__(self):
        return "<Playlist>"

    def __init__(self):
        super().__init()

class SmartPlaylists:

    def __repr__(self):
        return '<SmartPlaylists>'

    class MostPlayed(Playlist):
        TAG_TEXT = "MOST_PLAYED"
        # TRANSLATORS: this is a playlist name
        TITLE = _("Most Played")

    class NeverPlayed(Playlist):
        TAG_TEXT = "NEVER_PLAYED"
        # TRANSLATORS: this is a playlist name
        TITLE = _("Never Played")

    class RecentlyPlayed(Playlist):
        TAG_TEXT = "RECENTLY_PLAYED"
        # TRANSLATORS: this is a playlist name
        TITLE = _("Recently Played")

    class RecentlyAdded(Playlist):
        TAG_TEXT = "RECENTLY_ADDED"
        # TRANSLATORS: this is a playlist name
        TITLE = _("Recently Added")

    class Favorites(Playlist):
        TAG_TEXT = "FAVORITES"
        # TRANSLATORS: this is a playlist name
        TITLE = _("Favorite Songs")

    def __init__(self):
        Query()
        self.MostPlayed.QUERY = Query.get_most_played_songs()
        self.NeverPlayed.QUERY = Query.get_never_played_songs()
        self.RecentlyPlayed.QUERY = Query.get_recently_played_songs()
        self.RecentlyAdded.QUERY = Query.get_recently_added_songs()
        self.Favorites.QUERY = Query.get_favorite_songs()

    @staticmethod
    def get_ids():
        """Get all smart playlist IDs

        :return: A list of tracker.id's
        :rtype: A list of integers
        """
        return [str(playlist.ID) for playlist in SmartPlaylists.get_all()]

    @staticmethod
    def get_all():
        """Get all smart playlist classes

        :return: All SmartPlaylists innerclasses
        :rtype: A list of classes
        """
        return [cls for name, cls in inspect.getmembers(SmartPlaylists)
                if inspect.isclass(cls) and not name == "__class__"]


class Playlists(GObject.GObject):

    __gsignals__ = {
        'activate-playlist': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'playlist-created': (
            GObject.SignalFlags.RUN_FIRST, None, (Grl.Media,)
        ),
        'playlist-deleted': (
            GObject.SignalFlags.RUN_FIRST, None, (str,)
        ),
        'playlist-updated': (
            GObject.SignalFlags.RUN_FIRST, None, (int,)
        ),
        'playlist-renamed': (
            GObject.SignalFlags.RUN_FIRST, None, (Grl.Media,)
        ),
        'song-added-to-playlist': (
            GObject.SignalFlags.RUN_FIRST, None, (Grl.Media, Grl.Media)
        ),
    }

    instance = None
    _tracker = None

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
        super().__init__()

        self._smart_playlists = SmartPlaylists()
        self._pls_todelete = {}

        grilo.connect('ready', self._on_grilo_ready)

    @log
    def _on_grilo_ready(self, data=None):
        """For all smart playlists: get ID, if exists; if not, create
        the playlist and get ID."""

        def playlist_id_fetched_cb(cursor, res, playlist):
            """ Called after the playlist id is fetched """
            try:
                cursor.next_finish(res)
            except GLib.Error as err:
                logger.warning("Error: {}, {}".format(err.__class__, err))
                return

            playlist.ID = cursor.get_integer(1)

            if not playlist.ID:
                # Create the smart playlist
                self._create_smart_playlist(playlist)
            else:
                # Update playlist
                self.update_smart_playlist(playlist)

        def callback(obj, result, playlist):
            """ Starts retrieving the playlist id """
            try:
                cursor = obj.query_finish(result)
            except GLib.Error as err:
                logger.warning("Error: {}, {}".format(err.__class__, err))
                return

            # Search for the playlist ID
            cursor.next_async(None, playlist_id_fetched_cb, playlist)

        self._tracker = grilo.tracker_sparql
        # Start fetching all the smart playlists
        for playlist in self._smart_playlists.get_all():
            self._tracker.query_async(
                Query.get_playlist_with_tag(playlist.TAG_TEXT), None,
                callback, playlist)

    @log
    def _create_smart_playlist(self, playlist):
        """ Create the tag and the smart playlist, and fetch the newly created
        playlist's songs.
        """
        title = playlist.TITLE
        tag_text = playlist.TAG_TEXT

        def playlist_next_async_cb(cursor, res, playlist):
            """ Called after we finished moving the Tracker cursor, and ready
            to retrieve the playlist id"""
            # Update the playlist ID
            try:
                cursor.next_finish(res)
            except GLib.Error as err:
                logger.warning("Error: {}, {}".format(err.__class__, err))
                return

            playlist.ID = cursor.get_integer(0)

            # Fetch the playlist contents
            self.update_smart_playlist(playlist)

        def playlist_queried_cb(obj, res, playlist):
            """ Called after the playlist is created and the ID is fetched """
            try:
                cursor = obj.query_finish(res)
            except GLib.Error as err:
                logger.warning("Error: {}, {}".format(err.__class__, err))
                return

            cursor.next_async(None, playlist_next_async_cb, playlist)

        def playlist_created_cb(obj, res, playlist):
            """ Called when the smart playlist is created """
            data = obj.update_blank_finish(res)
            playlist_urn = data.get_child_value(0).get_child_value(0).\
                get_child_value(0).get_child_value(1).get_string()

            query = Query.get_playlist_with_urn(playlist_urn)

            # Start fetching the playlist
            self._tracker.query_async(
                query, None, playlist_queried_cb, playlist)

        def tag_created_cb(obj, res, playlist):
            """ Called when the tag is created """
            creation_query = Query.create_playlist_with_tag(title, tag_text)

            # Start creating the playlist itself
            self._tracker.update_blank_async(
                creation_query, GLib.PRIORITY_LOW, None, playlist_created_cb,
                playlist)

        # Start the playlist creation by creating the tag
        self._tracker.update_blank_async(
            Query.create_tag(tag_text), GLib.PRIORITY_LOW, None,
            tag_created_cb, playlist)

    @log
    def update_smart_playlist(self, playlist):
        """Updates a smart playlists.

        :param SmartPlaylist playlist: playlist to update
        """
        # Clear the smart playlist and then repopulate it
        query = Query.clear_playlist_with_id(playlist.ID)
        self._tracker.update_async(
            query, GLib.PRIORITY_LOW, None, self._smart_playlist_cleared_cb,
            playlist)

    @log
    def _smart_playlist_cleared_cb(self, connection, res, playlist):
        """After clearing the playlist, start querying the playlist's songs"""
        # Get a list of matching songs
        self._tracker.query_async(
            playlist.QUERY, None, self._smart_playlist_query_cb, playlist)

    @log
    def _smart_playlist_query_cb(self, connection, res, playlist):
        """Fetch the playlist's songs"""
        final_query = ''

        # Get a list of matching songs
        try:
            cursor = connection.query_finish(res)
        except GLib.Error as err:
            logger.warning("Error: {}, {}".format(err.__class__, err))
            return

        def callback(cursor, res, final_query):
            has_next = False
            try:
                has_next = cursor.next_finish(res)
            except GLib.Error as err:
                logger.warning("Error: {}, {}".format(err.__class__, err))

            # Only perform the update when the cursor reached the end
            if has_next:
                uri = cursor.get_string(0)[0]
                final_query += Query.add_song_to_playlist(playlist.ID, uri)

                cursor.next_async(None, callback, final_query)
            else:
                self._tracker.update_blank_async(
                    final_query, GLib.PRIORITY_LOW, None,
                    self._smart_playlist_update_finished, playlist)

        # Asynchronously form the playlist's final query
        cursor.next_async(None, callback, final_query)

    @log
    def _smart_playlist_update_finished(self, source, res, smart_playlist):
        self.emit('playlist-updated', smart_playlist.ID)

    @log
    def update_all_smart_playlists(self):
        for playlist in self._smart_playlists.get_all():
            self.update_smart_playlist(playlist)

    @log
    def create_playlist(self, title):
        def get_callback(source, param, item, count, data, error):
            if item:
                self.emit('playlist-created', item)

        def cursor_callback(cursor, res, data):
            try:
                cursor.next_finish(res)
            except GLib.Error as err:
                logger.warning("Error: {}, {}".format(err.__class__, err))
                return

            playlist_id = cursor.get_integer(0)
            grilo.get_playlist_with_id(playlist_id, get_callback)

        def query_callback(conn, res, data):
            try:
                cursor = conn.query_finish(res)
            except GLib.Error as err:
                logger.warning("Error: {}, {}".format(err.__class__, err))
                return

            if not cursor:
                return

            cursor.next_async(None, cursor_callback, data)

        def update_callback(conn, res, data):
            playlist_urn = conn.update_blank_finish(res)[0][0]['playlist']
            self._tracker.query_async(
                Query.get_playlist_with_urn(playlist_urn), None,
                query_callback, None)

        self._tracker.update_blank_async(
            Query.create_playlist(title), GLib.PRIORITY_LOW, None,
            update_callback, None)

    @log
    def rename(self, item, new_name):
        """Rename a playlist

        :param item: playlist to rename
        :param new_name: new playlist name
        :type item: Grl.Media
        :type new_name: str
        :return: None
        :rtype: None
        """
        def update_callback(conn, res, data):
            conn.update_finish(res)
            self.emit('playlist-renamed', item)

        self._tracker.update_async(
            Query.rename_playlist(item.get_id(), new_name), GLib.PRIORITY_LOW,
            None, update_callback, None)

    @log
    def delete_playlist(self, item_id):
        """Deletes a user playlist

        :param str item_id: Playlist id to delete
        """
        def update_callback(conn, res, data):
            conn.update_finish(res)
            self.emit("playlist-deleted", item_id)

        self._pls_todelete.pop(item_id)
        self._tracker.update_async(
            Query.delete_playlist(item_id), GLib.PRIORITY_LOW,
            None, update_callback, None)

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
                playlist_id, entry_id, get_callback)

        def update_callback(conn, res, data):
            entry_urn = conn.update_blank_finish(res)[0][0]['entry']
            self._tracker.query_async(
                Query.get_playlist_song_with_urn(entry_urn), None,
                query_callback, None)

        playlist_id = playlist.get_id()
        for item in items:
            uri = item.get_url()
            if not uri:
                continue
            self._tracker.update_blank_async(
                Query.add_song_to_playlist(playlist_id, uri),
                GLib.PRIORITY_LOW, None, update_callback, None)

    @log
    def remove_from_playlist(self, playlist, items):
        def update_callback(conn, res, data):
            conn.update_finish(res)

        playlist_id = playlist.get_id()
        for item in items:
            item_id = item.get_id()
            self._tracker.update_async(
                Query.remove_song_from_playlist(playlist_id, item_id),
                GLib.PRIORITY_LOW, None, update_callback, item)

    @log
    def reorder_playlist(self, playlist, items, new_positions):
        """Change the order of songs on a playlist.

        :param GlrMedia playlist: playlist to reorder
        :param list items: songs to reorder
        :param list new_positions: new songs positions
        """
        def update_callback(conn, res, data):
            conn.update_finish(res)

        playlist_id = playlist.get_id()
        for item, new_position in zip(items, new_positions):
            item_id = item.get_id()
            self._tracker.update_async(
                Query.change_song_position(playlist_id, item_id, new_position),
                GLib.PRIORITY_LOW, None, update_callback, item)

    @log
    def is_smart_playlist(self, playlist):
        """Checks whether the given playlist is smart or not

        :return: True if the playlist is smart
        :rtype: bool
        """
        for smart_playlist_id in self._smart_playlists.get_ids():
            if playlist.get_id() == smart_playlist_id:
                return True

        return False

    @log
    def activate_playlist(self, playlist_id):
        """Activates a playlist.

        Selects a playlist and start playing.

        :param str playlist_id: playlist id
        """
        # FIXME: just a proxy
        self.emit('activate-playlist', playlist_id)

    @log
    def stage_playlist_for_deletion(self, playlist, index):
        """Adds a playlist to the list of playlists to delete

        :param Grl.Media playlist: playlist to delete
        :param int index: Playlist position in PlaylistView
        """
        playlist_id = playlist.get_id()
        self._pls_todelete[playlist_id] = {
            "playlist": playlist,
            "index": index
        }

    @log
    def undo_pending_deletion(self, playlist):
        """Undo pending playlist deletion

        :param Grl.Media playlist: playlist to restore
        :returns: playlist previous index
        :rtype: int
        """
        playlist_id = playlist.get_id()
        index = self._pls_todelete[playlist_id]["index"]
        self._pls_todelete.pop(playlist_id)

        return index

    @log
    def get_playlists_to_delete(self):
        """Gets playlists ids ready for deletion"""
        return self._pls_todelete.keys()
