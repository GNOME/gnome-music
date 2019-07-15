# Copyright 2019 The GNOME Music developers
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

import time

from gettext import gettext as _

import gi
gi.require_versions({"Grl": "0.3"})
from gi.repository import Gio, Grl, GLib, GObject

from gnomemusic.coresong import CoreSong
from gnomemusic.trackerwrapper import TrackerWrapper
import gnomemusic.utils as utils


class GrlTrackerPlaylists(GObject.GObject):

    METADATA_KEYS = [
        Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_ALBUM_ARTIST,
        Grl.METADATA_KEY_ALBUM_DISC_NUMBER,
        Grl.METADATA_KEY_ARTIST,
        Grl.METADATA_KEY_CHILDCOUNT,
        Grl.METADATA_KEY_CREATION_DATE,
        Grl.METADATA_KEY_COMPOSER,
        Grl.METADATA_KEY_DURATION,
        Grl.METADATA_KEY_FAVOURITE,
        Grl.METADATA_KEY_ID,
        Grl.METADATA_KEY_PLAY_COUNT,
        Grl.METADATA_KEY_THUMBNAIL,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_TRACK_NUMBER,
        Grl.METADATA_KEY_URL
    ]

    def __repr__(self):
        return "<GrlTrackerPlaylists>"

    def __init__(self, source, coremodel, coreselection, grilo):
        super().__init__()

        self._coremodel = coremodel
        self._coreselection = coreselection
        self._grilo = grilo
        self._source = source
        self._model = self._coremodel.props.playlists
        self._model_filter = self._coremodel.props.playlists_filter
        self._pls_todelete = []
        self._tracker = TrackerWrapper().props.tracker

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self._initial_playlists_fill()

    def _initial_playlists_fill(self):
        args = {
            "source": self._source,
            "coreselection": self._coreselection,
            "grilo": self._grilo
        }

        smart_playlists = {
            "MostPlayed": MostPlayed(**args),
            "NeverPlayed": NeverPlayed(**args),
            "RecentlyPlayed": RecentlyPlayed(**args),
            "RecentlyAdded": RecentlyAdded(**args),
            "Favorites": Favorites(**args)
        }

        for playlist in smart_playlists.values():
            self._model.append(playlist)

        query = """
        SELECT DISTINCT
            rdf:type(?playlist)
            tracker:id(?playlist) AS ?id
            nie:title(?playlist) AS ?title
            tracker:added(?playlist) AS ?creation_date
            nfo:entryCounter(?playlist) AS ?childcount
        WHERE
        {
            ?playlist a nmm:Playlist .
            OPTIONAL { ?playlist nie:url ?url;
                       tracker:available ?available . }
            FILTER ( !STRENDS(LCASE(?url), '.m3u')
                     && !STRENDS(LCASE(?url), '.m3u8')
                     && !STRENDS(LCASE(?url), '.pls')
                     || !BOUND(nfo:belongsToContainer(?playlist)) )
            FILTER ( !BOUND(?tag) )
            OPTIONAL { ?playlist nao:hasTag ?tag }
        }
        """.replace('\n', ' ').strip()

        options = self._fast_options.copy()

        self._source.query(
            query, self.METADATA_KEYS, options, self._add_user_playlist)

    def _add_user_playlist(
            self, source, op_id, media, remaining, data=None, error=None):
        if error:
            print("ERROR", error)
            return
        if not media:
            self._coremodel.emit("playlists-loaded")
            return

        playlist = Playlist(
            media=media, source=self._source, coremodel=self._coremodel,
            coreselection=self._coreselection, grilo=self._grilo)

        self._model.append(playlist)
        callback = data
        if callback is not None:
            callback(playlist)

    def _playlists_filter(self, playlist):
        return playlist not in self._pls_todelete

    def stage_playlist_deletion(self, playlist):
        """Adds playlist to the list of playlists to delete

        :param Playlist playlist: playlist
        """
        self._pls_todelete.append(playlist)
        self._model_filter.set_filter_func(self._playlists_filter)

    def finish_playlist_deletion(self, playlist, deleted):
        """Removes playlist from the list of playlists to delete

        :param Playlist playlist: playlist
        :param bool deleted: indicates if the playlist has been deleted
        """
        self._pls_todelete.remove(playlist)
        if deleted is False:
            self._model_filter.set_filter_func(self._playlists_filter)
            return

        def _delete_cb(conn, res, data):
            # FIXME: Check for failure.
            conn.update_finish(res)
            for idx, playlist_model in enumerate(self._model):
                if playlist_model is playlist:
                    self._model.remove(idx)
                    break

            self._model_filter.set_filter_func(self._playlists_filter)

        query = """
        DELETE {
            ?playlist a rdfs:Resource .
            ?entry a rdfs:Resource .

        }
        WHERE {
            ?playlist a nmm:Playlist ;
                      a nfo:MediaList .
            OPTIONAL {
                ?playlist nfo:hasMediaFileListEntry ?entry .
            }
            FILTER (
            tracker:id(?playlist) = %(playlist_id)s
            )
        }
        """.replace("\n", " ").strip() % {
            "playlist_id": playlist.props.pl_id
        }
        self._tracker.update_async(
            query, GLib.PRIORITY_LOW, None, _delete_cb, None)

    def create_playlist(self, playlist_title, callback):
        """Creates a new user playlist.

        :param str playlist_title: playlist title
        :param callback: function to perform once, the playlist is created
        """
        def _create_cb(conn, res, data):
            result = conn.update_blank_finish(res)
            playlist_urn = result[0][0]['playlist']
            query = """
            SELECT
                rdf:type(?playlist)
                tracker:id(?playlist) AS ?id
                nie:title(?playlist) AS ?title
                tracker:added(?playlist) AS ?creation_date
                nfo:entryCounter(?playlist) AS ?childcount
                WHERE
                {
                    ?playlist a nmm:Playlist .
                    FILTER ( <%(playlist_urn)s> = ?playlist )
                }
            """.replace("\n", " ").strip() % {"playlist_urn": playlist_urn}

            options = self._fast_options.copy()
            self._source.query(
                query, self.METADATA_KEYS, options, self._add_user_playlist,
                callback)

        query = """
            INSERT {
                _:playlist a nmm:Playlist ;
                           a nfo:MediaList ;
                             nie:title "%(title)s" ;
                             nfo:entryCounter 0 .
            }
            """.replace("\n", " ").strip() % {"title": playlist_title}
        self._tracker.update_blank_async(
            query, GLib.PRIORITY_LOW, None, _create_cb, None)


class Playlist(GObject.GObject):
    """ Base class of all playlists """

    __gsignals__ = {
        "playlist-loaded": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    METADATA_KEYS = [
        Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_ALBUM_ARTIST,
        Grl.METADATA_KEY_ALBUM_DISC_NUMBER,
        Grl.METADATA_KEY_ARTIST,
        Grl.METADATA_KEY_CREATION_DATE,
        Grl.METADATA_KEY_COMPOSER,
        Grl.METADATA_KEY_DURATION,
        Grl.METADATA_KEY_FAVOURITE,
        Grl.METADATA_KEY_ID,
        Grl.METADATA_KEY_PLAY_COUNT,
        Grl.METADATA_KEY_THUMBNAIL,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_TRACK_NUMBER,
        Grl.METADATA_KEY_URL
    ]

    count = GObject.Property(type=int, default=0)
    creation_date = GObject.Property(type=GLib.DateTime, default=None)
    is_smart = GObject.Property(type=bool, default=False)
    pl_id = GObject.Property(type=str, default=None)
    query = GObject.Property(type=str, default=None)
    tag_text = GObject.Property(type=str, default=None)
    title = GObject.Property(type=str, default=None)

    def __repr__(self):
        return "<Playlist>"

    def __init__(
            self, media=None, query=None, tag_text=None, source=None,
            coremodel=None, coreselection=None, grilo=None):
        super().__init__()

        if media:
            self.props.pl_id = media.get_id()
            self.props.title = utils.get_media_title(media)
            self.props.count = media.get_childcount()
            self.props.creation_date = media.get_creation_date()

        self.props.query = query
        self.props.tag_text = tag_text
        self._model = None
        self._source = source
        self._coremodel = coremodel
        self._coreselection = coreselection
        self._grilo = grilo
        self._tracker = TrackerWrapper().props.tracker

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self._songs_todelete = []

    @GObject.Property(type=Gio.ListStore, default=None)
    def model(self):
        if self._model is None:
            self._model = Gio.ListStore()

            self._populate_model()

        return self._model

    @model.setter
    def model(self, value):
        self._model = value

    def _populate_model(self):
        query = """
        SELECT
            rdf:type(?song)
            ?song AS ?tracker_urn
            tracker:id(?entry) AS ?id
            nie:url(?song) AS ?url
            nie:title(?song) AS ?title
            nmm:artistName(nmm:performer(?song)) AS ?artist
            nie:title(nmm:musicAlbum(?song)) AS ?album
            nfo:duration(?song) AS ?duration
            ?tag AS ?favourite
            nie:contentAccessed(?song) AS ?last_played_time
            nie:usageCounter(?song) AS ?play_count
        WHERE {
            ?playlist a nmm:Playlist ;
                      a nfo:MediaList ;
                        nfo:hasMediaFileListEntry ?entry .
            ?entry a nfo:MediaFileListEntry ;
                     nfo:entryUrl ?url .
            ?song a nmm:MusicPiece ;
                  a nfo:FileDataObject ;
                    nie:url ?url .
            OPTIONAL {
                ?song nao:hasTag ?tag .
                FILTER( ?tag = nao:predefined-tag-favorite )
            }
            FILTER (
                %(filter_clause)s
            )
            FILTER (
                NOT EXISTS { ?song a nmm:Video }
                && NOT EXISTS { ?song a nmm:Playlist }
            )
        }
        ORDER BY nfo:listPosition(?entry)
        """.replace('\n', ' ').strip() % {
            'filter_clause': 'tracker:id(?playlist) = ' + self.props.pl_id
        }

        def _add_to_playlist_cb(
                source, op_id, media, remaining, user_data, error):
            if not media:
                self.props.count = self._model.get_n_items()
                self.emit("playlist-loaded")
                return

            coresong = CoreSong(media, self._coreselection, self._grilo)
            if coresong not in self._songs_todelete:
                self._model.append(coresong)

        options = Grl.OperationOptions()
        options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self._source.query(
            query, self.METADATA_KEYS, options, _add_to_playlist_cb, None)

    def rename(self, new_name):
        """Rename a playlist

        :param str new_name: new playlist name
        """
        def update_cb(conn, res, data):
            # FIXME: Check for failure.
            conn.update_finish(res)
            # FIXME: Requery instead?
            self.props.title = new_name

        query = """
        INSERT OR REPLACE {
            ?playlist nie:title "%(title)s"
        }
        WHERE {
            ?playlist a nmm:Playlist ;
                      a nfo:MediaList .
            OPTIONAL {
                ?playlist nfo:hasMediaFileListEntry ?entry .
            }
            FILTER (
                tracker:id(?playlist) = %(playlist_id)s
            )
        }
        """.replace("\n", " ").strip() % {
            'title': new_name,
            'playlist_id': self.props.pl_id
        }

        self._tracker.update_async(
            query, GLib.PRIORITY_LOW, None, update_cb, None)

    def stage_song_deletion(self, coresong, index):
        """Adds a song to the list of songs to delete

        :param CoreSong coresong: song to delete
        :param int position: Song position in the playlist
        """
        self._songs_todelete.append(coresong)
        self._model.remove(index)
        self.props.count -= 1

    def undo_pending_song_deletion(self, coresong, position):
        """Removes song from the list of songs to delete

        :param CoreSong coresong: song to delete
        :param int position: Song position in the playlist
        """
        self._songs_todelete.remove(coresong)
        self._model.insert(position, coresong)
        self.props.count += 1

    def finish_song_deletion(self, coresong):
        """Removes a song from the playlist

        :param CoreSong coresong: song to remove
        """

        def update_cb(conn, res, data):
            # FIXME: Check for failure.
            conn.update_finish(res)

        query = """
        INSERT OR REPLACE {
            ?entry nfo:listPosition ?position .

        }
        WHERE {
            SELECT ?entry
                   (?old_position - 1) AS ?position
            WHERE {
                ?entry a nfo:MediaFileListEntry ;
                         nfo:listPosition ?old_position .
                ?playlist nfo:hasMediaFileListEntry ?entry .
                FILTER (?old_position > ?removed_position)
                {
                    SELECT ?playlist
                           ?removed_position
                    WHERE {
                        ?playlist a nmm:Playlist ;
                                  a nfo:MediaList ;
                                    nfo:hasMediaFileListEntry ?removed_entry .
                        ?removed_entry nfo:listPosition ?removed_position .
                        FILTER (
                            tracker:id(?playlist) = %(playlist_id)s &&
                            tracker:id(?removed_entry) = %(song_id)s
                        )
                    }
                }
            }
        }
        INSERT OR REPLACE {
            ?playlist nfo:entryCounter ?new_counter .
        }
        WHERE {
            SELECT ?playlist
                   (?counter - 1) AS ?new_counter
            WHERE {
                ?playlist a nmm:Playlist ;
                          a nfo:MediaList ;
                            nfo:entryCounter ?counter .
                FILTER (
                    tracker:id(?playlist) = %(playlist_id)s
                )
            }
        }
        DELETE {
            ?playlist nfo:hasMediaFileListEntry ?entry .
            ?entry a rdfs:Resource .
        }
        WHERE {
            ?playlist a nmm:Playlist ;
                      a nfo:MediaList ;
                        nfo:hasMediaFileListEntry ?entry .
            FILTER (
                tracker:id(?playlist) = %(playlist_id)s &&
                tracker:id(?entry) = %(song_id)s
            )
        }
        """.replace("\n", " ").strip() % {
            "playlist_id": self.props.pl_id,
            "song_id": coresong.props.media.get_id()
        }

        self._tracker.update_async(
            query, GLib.PRIORITY_LOW, None, update_cb, None)

    def add_songs(self, coresongs):
        """Adds songs to the playlist

        :param Playlist playlist:
        :param list coresongs: list of Coresong
        """
        def _add_to_model(source, op_id, media, remaining, error):
            if not media:
                self.props.count = self._model.get_n_items()
                return

            coresong = CoreSong(media, self._coreselection, self._grilo)
            if coresong not in self._songs_todelete:
                self._model.append(coresong)

        def _requery_media(conn, res, coresong):
            if self._model is None:
                return

            media_id = coresong.props.media.get_id()
            query = """
            SELECT
                rdf:type(?song)
                ?song AS ?tracker_urn
                tracker:id(?entry) AS ?id
                nie:url(?song) AS ?url
                nie:title(?song) AS ?title
                nmm:artistName(nmm:performer(?song)) AS ?artist
                nie:title(nmm:musicAlbum(?song)) AS ?album
                nfo:duration(?song) AS ?duration
                ?tag AS ?favourite
                nie:contentAccessed(?song) AS ?last_played_time
                nie:usageCounter(?song) AS ?play_count
            WHERE {
                ?playlist a nmm:Playlist ;
                          a nfo:MediaList ;
                            nfo:hasMediaFileListEntry ?entry .
                ?entry a nfo:MediaFileListEntry ;
                         nfo:entryUrl ?url .
                ?song a nmm:MusicPiece ;
                      a nfo:FileDataObject ;
                        nie:url ?url .
                OPTIONAL {
                    ?song nao:hasTag ?tag .
                    FILTER( ?tag = nao:predefined-tag-favorite )
                }
                FILTER (
                   %(filter_clause)s
                )
                FILTER (
                    NOT EXISTS { ?song a nmm:Video }
                    && NOT EXISTS { ?song a nmm:Playlist }
                )
            }
            """.replace("\n", " ").strip() % {
                "filter_clause": "tracker:id(?entry) = " + media_id}
            options = self._fast_options.copy()
            self._source.query(
                query, self.METADATA_KEYS, options, _add_to_model)

        for coresong in coresongs:
            query = """
            INSERT OR REPLACE {
                _:entry a nfo:MediaFileListEntry ;
                          nfo:entryUrl "%(song_uri)s" ;
                          nfo:listPosition ?position .
                ?playlist nfo:entryCounter ?position ;
                          nfo:hasMediaFileListEntry _:entry .
            }
            WHERE {
                SELECT ?playlist
                       (?counter + 1) AS ?position
                WHERE {
                    ?playlist a nmm:Playlist ;
                              a nfo:MediaList ;
                                nfo:entryCounter ?counter .
                    FILTER (
                        tracker:id(?playlist) = %(playlist_id)s
                    )
                }
            }
            """.replace("\n", " ").strip() % {
                "playlist_id": self.props.pl_id,
                "song_uri": coresong.props.media.get_url()}

            self._tracker.update_blank_async(
                query, GLib.PRIORITY_LOW, None, _requery_media, coresong)

    def reorder(self, previous_position, new_position):
        """Changes the order of a songs in the playlist.

        :param int previous_position: preivous song position
        :param int new_position: new song position
        """
        def _position_changed_cb(conn, res, position):
            # FIXME: Check for failure.
            conn.update_finish(res)

        coresong = self._model.get_item(previous_position)
        self._model.remove(previous_position)
        self._model.insert(new_position, coresong)

        main_query = """
        INSERT OR REPLACE {
        ?entry
            nfo:listPosition %(position)s
        }
        WHERE {
            ?playlist a nmm:Playlist ;
                      a nfo:MediaList ;
                        nfo:hasMediaFileListEntry ?entry .
            FILTER (
                tracker:id(?playlist) = %(playlist_id)s &&
                tracker:id(?entry) = %(song_id)s
            )
        }
        """.replace("\n", " ").strip()

        first_pos = min(previous_position, new_position)
        last_pos = max(previous_position, new_position)

        for position in range(first_pos, last_pos + 1):
            coresong = self._model.get_item(position)
            query = main_query % {
                "playlist_id": self.props.pl_id,
                "song_id": coresong.props.media.get_id(),
                "position": position
            }
            self._tracker.update_async(
                query, GLib.PRIORITY_LOW, None, _position_changed_cb,
                position)


class SmartPlaylist(Playlist):
    """Base class for smart playlists"""

    def __repr__(self):
        return "<SmartPlaylist>"

    def __init__(self, **args):
        super().__init__(**args)

        self.props.is_smart = True

    @GObject.Property(type=Gio.ListStore, default=None)
    def model(self):
        if self._model is None:
            self._model = Gio.ListStore.new(CoreSong)

            def _add_to_model(source, op_id, media, remaining, error):
                if error:
                    print("ERROR", error)
                    return

                if not media:
                    self.props.count = self._model.get_n_items()
                    return

                coresong = CoreSong(media, self._coreselection, self._grilo)
                self._model.append(coresong)

            options = self._fast_options.copy()

            self._source.query(
                self.props.query, self.METADATA_KEYS, options, _add_to_model)

        return self._model


class MostPlayed(SmartPlaylist):
    """Most Played smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "MOST_PLAYED"
        # TRANSLATORS: this is a playlist name
        self.props.title = _("Most Played")
        self.props.query = """
        SELECT
            rdf:type(?song)
            tracker:id(?song) AS ?id
            ?song AS ?tracker_urn
            nie:title(?song) AS ?title
            nie:url(?song) AS ?url
            nie:title(?song) AS ?title
            nmm:artistName(nmm:performer(?song)) AS ?artist
            nie:title(nmm:musicAlbum(?song)) AS ?album
            nfo:duration(?song) AS ?duration
            nie:usageCounter(?song) AS ?play_count
            nmm:trackNumber(?song) AS ?track_number
            nmm:setNumber(nmm:musicAlbumDisc(?song)) AS ?album_disc_number
            ?tag AS ?favourite
        WHERE {
            ?song a nmm:MusicPiece ;
                    nie:usageCounter ?count .
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        }
        ORDER BY DESC(?count) LIMIT 50
        """.replace('\n', ' ').strip()


class NeverPlayed(SmartPlaylist):
    """Never Played smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "NEVER_PLAYED"
        # TRANSLATORS: this is a playlist name
        self.props.title = _("Never Played")
        self.props.query = """
        SELECT
            rdf:type(?song)
            tracker:id(?song) AS ?id
            ?song AS ?tracker_urn
            nie:title(?song) AS ?title
            nie:url(?song) AS ?url
            nie:title(?song) AS ?title
            nmm:artistName(nmm:performer(?song)) AS ?artist
            nie:title(nmm:musicAlbum(?song)) AS ?album
            nfo:duration(?song) AS ?duration
            nie:usageCounter(?song) AS ?play_count
            nmm:trackNumber(?song) AS ?track_number
            nmm:setNumber(nmm:musicAlbumDisc(?song)) AS ?album_disc_number
            ?tag AS ?favourite
        WHERE {
            ?song a nmm:MusicPiece ;
            FILTER ( NOT EXISTS { ?song nie:usageCounter ?count .} )
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        } ORDER BY nfo:fileLastAccessed(?song) LIMIT 50
        """.replace('\n', ' ').strip()


class RecentlyPlayed(SmartPlaylist):
    """Recently Played smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "RECENTLY_PLAYED"
        # TRANSLATORS: this is a playlist name
        self.props.title = _("Recently Played")

        sparql_midnight_dateTime_format = "%Y-%m-%dT00:00:00Z"
        days_difference = 7
        seconds_difference = days_difference * 86400
        compare_date = time.strftime(
            sparql_midnight_dateTime_format,
            time.gmtime(time.time() - seconds_difference))
        self.props.query = """
        SELECT
            rdf:type(?song)
            tracker:id(?song) AS ?id
            ?song AS ?tracker_urn
            nie:title(?song) AS ?title
            nie:url(?song) AS ?url
            nie:title(?song) AS ?title
            nmm:artistName(nmm:performer(?song)) AS ?artist
            nie:title(nmm:musicAlbum(?song)) AS ?album
            nfo:duration(?song) AS ?duration
            nie:usageCounter(?song) AS ?play_count
            nmm:trackNumber(?song) AS ?track_number
            nmm:setNumber(nmm:musicAlbumDisc(?song)) AS ?album_disc_number
            ?tag AS ?favourite
        WHERE {
            ?song a nmm:MusicPiece ;
                    nie:contentAccessed ?last_played .
            FILTER ( ?last_played > '%(compare_date)s'^^xsd:dateTime
                     && EXISTS { ?song nie:usageCounter ?count .} )
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        } ORDER BY DESC(?last_played) LIMIT 50
        """.replace('\n', ' ').strip() % {
            'compare_date': compare_date
        }


class RecentlyAdded(SmartPlaylist):
    """Recently Added smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "RECENTLY_ADDED"
        # TRANSLATORS: this is a playlist name
        self.props.title = _("Recently Added")

        sparql_midnight_dateTime_format = "%Y-%m-%dT00:00:00Z"
        days_difference = 7
        seconds_difference = days_difference * 86400
        compare_date = time.strftime(
            sparql_midnight_dateTime_format,
            time.gmtime(time.time() - seconds_difference))
        self.props.query = """
        SELECT
            rdf:type(?song)
            tracker:id(?song) AS ?id
            ?song AS ?tracker_urn
            nie:title(?song) AS ?title
            nie:url(?song) AS ?url
            nie:title(?song) AS ?title
            nmm:artistName(nmm:performer(?song)) AS ?artist
            nie:title(nmm:musicAlbum(?song)) AS ?album
            nfo:duration(?song) AS ?duration
            nie:usageCounter(?song) AS ?play_count
            nmm:trackNumber(?song) AS ?track_number
            nmm:setNumber(nmm:musicAlbumDisc(?song)) AS ?album_disc_number
            ?tag AS ?favourite
        WHERE {
            ?song a nmm:MusicPiece ;
                    tracker:added ?added .
            FILTER ( tracker:added(?song) > '%(compare_date)s'^^xsd:dateTime )
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        } ORDER BY DESC(tracker:added(?song)) LIMIT 50
        """.replace('\n', ' ').strip() % {
            'compare_date': compare_date,
        }


class Favorites(SmartPlaylist):
    """Favorites smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "FAVORITES"
        # TRANSLATORS: this is a playlist name
        self.props.title = _("Favorite Songs")
        self.props.query = """
            SELECT
                rdf:type(?song)
                tracker:id(?song) AS ?id
                ?song AS ?tracker_urn
                nie:title(?song) AS ?title
                nie:url(?song) AS ?url
                nie:title(?song) AS ?title
                nmm:artistName(nmm:performer(?song)) AS ?artist
                nie:title(nmm:musicAlbum(?song)) AS ?album
                nfo:duration(?song) AS ?duration
                nie:usageCounter(?song) AS ?play_count
                nmm:trackNumber(?song) AS ?track_number
                nmm:setNumber(nmm:musicAlbumDisc(?song)) AS ?album_disc_number
                nao:predefined-tag-favorite AS ?favourite
            WHERE {
                ?song a nmm:MusicPiece ;
                        nie:isStoredAs ?as ;
                        nao:hasTag nao:predefined-tag-favorite .
                ?as nie:url ?url .
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }

            } ORDER BY DESC(tracker:added(?song))
        """.replace('\n', ' ').strip()
