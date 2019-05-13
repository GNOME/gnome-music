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

import math

import gi
gi.require_version('Dazzle', '1.0')
gi.require_version('Grl', '0.3')
from gi.repository import Dazzle, Gio, Grl, GLib, GObject
from gnomemusic.grilo import grilo
from gnomemusic.query import Query
import gnomemusic.utils as utils
from gettext import gettext as _

from gnomemusic import log
import logging
logger = logging.getLogger(__name__)


class Playlist(GObject.Object):
    """ Base class of all playlists """

    creation_date = GObject.Property(type=GLib.DateTime, default=None)
    id_ = GObject.Property(type=str, default=None)
    is_smart = GObject.Property(type=bool, default=False)
    query = GObject.Property(type=str, default=None)
    tag_text = GObject.Property(type=str, default=None)
    title = GObject.Property(type=str, default=None)

    def __repr__(self):
        return "<Playlist>"

    def __init__(
            self, id_=None, query=None, tag_text=None, title=None,
            creation_date=None):
        super().__init__()

        self.props.id_ = id_
        self.props.query = query
        self.props.tag_text = tag_text
        self.props.title = title
        self.props.creation_date = creation_date

    @staticmethod
    def compare_playlist_func(playlist_a, playlist_b):
        if playlist_a.props.is_smart:
            if not playlist_b.props.is_smart:
                return -1
            return GLib.strcmp0(playlist_a.props.title, playlist_b.props.title)

        if playlist_b.props.is_smart:
            return 1

        # cannot use GLib.DateTime.compare
        # https://gitlab.gnome.org/GNOME/pygobject/issues/334
        date_diff = playlist_a.props.creation_date.difference(
            playlist_b.props.creation_date)
        return math.copysign(1, date_diff)


class SmartPlaylist(Playlist):
    """Base class for smart playlists"""

    def __repr__(self):
        return "<SmartPlaylist>"

    def __init__(self):
        super().__init__()

        self.props.is_smart = True


class MostPlayed(SmartPlaylist):
    """Most Played smart playlist"""

    def __init__(self):
        super().__init__()

        self.props.tag_text = "MOST_PLAYED"
        # TRANSLATORS: this is a playlist name
        self.props.title = _("Most Played")
        self.props.query = Query.get_never_played_songs()


class NeverPlayed(SmartPlaylist):
    """Never Played smart playlist"""

    def __init__(self):
        super().__init__()

        self.props.tag_text = "NEVER_PLAYED"
        # TRANSLATORS: this is a playlist name
        self.props.title = _("Never Played")
        self.props.query = Query.get_never_played_songs()


class RecentlyPlayed(SmartPlaylist):
    """Recently Played smart playlist"""

    def __init__(self):
        super().__init__()

        self.props.tag_text = "RECENTLY_PLAYED"
        # TRANSLATORS: this is a playlist name
        self.props.title = _("Recently Played")
        self.props.query = Query.get_recently_played_songs()


class RecentlyAdded(SmartPlaylist):
    """Recently Added smart playlist"""

    def __init__(self):
        super().__init__()

        self.props.tag_text = "RECENTLY_ADDED"
        # TRANSLATORS: this is a playlist name
        self.props.title = _("Recently Added")
        self.props.query = Query.get_recently_added_songs()


class Favorites(SmartPlaylist):
    """Favorites smart playlist"""

    def __init__(self):
        super().__init__()

        self.props.tag_text = "FAVORITES"
        # TRANSLATORS: this is a playlist name
        self.props.title = _("Favorite Songs")
        self.props.query = Query.get_favorite_songs()


class Playlists(GObject.GObject):

    __gsignals__ = {
        'activate-playlist': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'playlist-created': (
            GObject.SignalFlags.RUN_FIRST, None, (Grl.Media,)
        ),
        'playlist-deleted': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'playlist-updated': (GObject.SignalFlags.RUN_FIRST, None, (Playlist,)),
        'playlist-renamed': (GObject.SignalFlags.RUN_FIRST, None, (Playlist,)),
        'song-added-to-playlist': (
            GObject.SignalFlags.RUN_FIRST, None, (Playlist, Grl.Media)
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

        Query()
        self._smart_playlists = {
            "MostPlayed": MostPlayed(),
            "NeverPlayed": NeverPlayed(),
            "RecentlyPlayed": RecentlyPlayed(),
            "RecentlyAdded": RecentlyAdded(),
            "Favorites": Favorites()
        }
        self._playlists_model = Gio.ListStore.new(Playlist)

        self._pls_todelete = []

        self._ready = False

        self._loading_counter = len(self._smart_playlists)
        self._user_playlists_ready = False

        grilo.connect("ready", self._on_grilo_ready)

    @log
    def _on_grilo_ready(self, data=None):
        """For all smart playlists: get id, if exists; if not, create
        the playlist and get id.
        Also gather the user playlists.
        """

        def playlist_id_fetched_cb(cursor, res, playlist):
            """ Called after the playlist id is fetched """
            try:
                cursor.next_finish(res)
            except GLib.Error as err:
                logger.warning("Error: {}, {}".format(err.__class__, err))
                return

            playlist.props.id_ = cursor.get_integer(1)

            if not playlist.props.id_:
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

            # Search for the playlist id
            cursor.next_async(None, playlist_id_fetched_cb, playlist)

        self._tracker = grilo.tracker_sparql
        self.notify('ready')

        # Start fetching all the smart playlists
        for playlist in self._smart_playlists.values():
            self._tracker.query_async(
                Query.get_playlist_with_tag(playlist.props.tag_text), None,
                callback, playlist)

        # Gather the available user playlists too
        grilo.populate_user_playlists(
            0, self._populate_user_playlists_finish_cb)

    @log
    def _populate_user_playlists_finish_cb(
            self, source, param, item, remaining=0, data=None):
        """Fill in the list of playlists currently available"""
        if not item:
            self._user_playlists_ready = True
            self._check_ready()
            return

        playlist = Playlist(
            id_=item.get_id(), title=utils.get_media_title(item),
            creation_date=item.get_creation_date())

        self._playlists_model.insert_sorted(
            playlist, Playlist.compare_playlist_func)

    @log
    def _create_smart_playlist(self, playlist):
        """ Create the tag and the smart playlist, and fetch the newly created
        playlist's songs.
        """
        title = playlist.props.title
        tag_text = playlist.props.tag_text

        def playlist_next_async_cb(cursor, res, playlist):
            """ Called after we finished moving the Tracker cursor, and ready
            to retrieve the playlist id"""
            # Update the playlist id
            try:
                cursor.next_finish(res)
            except GLib.Error as err:
                logger.warning("Error: {}, {}".format(err.__class__, err))
                return

            playlist.props.id_ = cursor.get_integer(0)

            # Fetch the playlist contents
            self.update_smart_playlist(playlist)

        def playlist_queried_cb(obj, res, playlist):
            """ Called after the playlist is created and the id is fetched """
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
        """Given a smart playlist (subclass of SmartPlaylists),
        updates according to its query."""
        # Clear the playlist
        self.clear_playlist(playlist)

    @log
    def clear_playlist(self, playlist):
        """Starts cleaning the playlist"""
        query = Query.clear_playlist_with_id(playlist.props.id_)
        self._tracker.update_async(
            query, GLib.PRIORITY_LOW, None, self._smart_playlist_cleared_cb,
            playlist)

    @log
    def _smart_playlist_cleared_cb(self, connection, res, playlist):
        """After clearing the playlist, start querying the playlist's songs"""
        # Get a list of matching songs
        self._tracker.query_async(
            playlist.props.query, None, self._smart_playlist_query_cb,
            playlist)

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
                final_query += Query.add_song_to_playlist(
                    playlist.props.id_, uri)

                cursor.next_async(None, callback, final_query)
            else:
                self._tracker.update_blank_async(
                    final_query, GLib.PRIORITY_LOW, None,
                    self._smart_playlist_update_finished, playlist)

        # Asynchronously form the playlist's final query
        cursor.next_async(None, callback, final_query)

    @log
    def _smart_playlist_update_finished(self, source, res, smart_playlist):
        if smart_playlist in self._playlists_model:
            self.emit("playlist-updated", smart_playlist)
            return

        self._playlists_model.insert_sorted(
            smart_playlist, Playlist.compare_playlist_func)

        # Check if we're ready
        self._loading_counter = self._loading_counter - 1
        self._check_ready()

    @log
    def update_all_smart_playlists(self):
        for playlist in self._smart_playlists.values():
            self.update_smart_playlist(playlist)

    @log
    def create_playlist(self, title, callback):
        """Creates an user playlist.

        :param str title: new playlist title
        :param function callback: called once the playlist is created
        """
        def get_callback(source, param, item, count, data, error):
            if not item:
                return

            new_playlist = Playlist(
                id_=item.get_id(), title=utils.get_media_title(item),
                creation_date=item.get_creation_date())
            self._playlists_model.insert_sorted(
                new_playlist, Playlist.compare_playlist_func)
            self.emit('playlist-created', item)
            callback(new_playlist)

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
    def rename(self, playlist, new_name):
        """Rename a playlist

        :param Playlist item: playlist to rename
        :param str new_name: new playlist name
        """
        def update_callback(conn, res, data):
            conn.update_finish(res)
            self.emit('playlist-renamed', playlist)

        query = Query.rename_playlist(playlist.props.id_, new_name)
        self._tracker.update_async(
            query, GLib.PRIORITY_LOW, None, update_callback, None)

    @log
    def delete_playlist(self, playlist):
        """Deletes a user playlist

        :param Playlist playlist: Playlist to delete
        """
        def update_callback(conn, res, data):
            conn.update_finish(res)
            self.emit('playlist-deleted', playlist.props.id_)

        self._pls_todelete.remove(playlist)
        query = Query.delete_playlist(playlist.props.id_)
        self._tracker.update_async(
            query, GLib.PRIORITY_LOW, None, update_callback, None)

    @log
    def add_to_playlist(self, playlist, items):
        """Adds songs to a playlist.

        :param Playlist playlist:
        :param list items: list of Grl.Media
        """
        def get_callback(source, param, item, count, data, error):
            if item:
                self.emit('song-added-to-playlist', playlist, item)

        def query_callback(conn, res, data):
            cursor = conn.query_finish(res)
            if not cursor or not cursor.next():
                return
            entry_id = cursor.get_integer(0)
            grilo.get_playlist_song_with_id(
                playlist.props.id_, entry_id, get_callback)

        def update_callback(conn, res, data):
            entry_urn = conn.update_blank_finish(res)[0][0]['entry']
            self._tracker.query_async(
                Query.get_playlist_song_with_urn(entry_urn), None,
                query_callback, None)

        for item in items:
            uri = item.get_url()
            if not uri:
                continue
            self._tracker.update_blank_async(
                Query.add_song_to_playlist(playlist.props.id_, uri),
                GLib.PRIORITY_LOW, None, update_callback, None)

    @log
    def remove_from_playlist(self, playlist, items):
        def update_callback(conn, res, data):
            conn.update_finish(res)

        for item in items:
            item_id = item.get_id()
            self._tracker.update_async(
                Query.remove_song_from_playlist(playlist.props.id_, item_id),
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
    def get_playlists(self):
        """Retrieves the currently loaded playlists.

        :return: a list of Playlists
        :rtype: list
        """
        return self._playlists_model

    @log
    def get_user_playlists(self):
        def user_playlists_filter(playlist):
            return (playlist not in self._pls_todelete
                    and not playlist.props.is_smart)

        model_filter = Dazzle.ListModelFilter.new(self._playlists_model)
        model_filter.set_filter_func(user_playlists_filter)
        return model_filter

    @log
    def get_smart_playlist(self, name):
        """SmartPlaylist getter

        :param str name: smart playlist name
        :returns: Smart Playlist
        :rtype: Playlist
        """
        return self._smart_playlists[name]

    @log
    def is_smart_playlist(self, playlist):
        """Checks whether the given playlist is smart or not

        :return: True if the playlist is smart
        :rtype: bool
        """
        for smart_playlist in self._smart_playlists.values():
            if playlist.get_id() == smart_playlist.props.id_:
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

        :param Playlist playlist: playlist to delete
        :param int index: Playlist position in PlaylistView
        """
        self._pls_todelete.append(playlist)
        self._playlists_model.remove(index)

    @log
    def undo_pending_deletion(self, playlist):
        """Undo pending playlist deletion

        :param Playlist playlist: playlist to restore
        """
        self._pls_todelete.remove(playlist)
        self._playlists_model.insert_sorted(
            playlist, Playlist.compare_playlist_func)

    @GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READABLE)
    def ready(self):
        return self._ready

    def _check_ready(self):
        ready = (self._user_playlists_ready
                 and self._loading_counter == 0)
        if ready != self._ready:
            self._ready = ready
            self.notify("ready")
