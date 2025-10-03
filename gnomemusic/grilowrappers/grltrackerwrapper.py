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

from __future__ import annotations
from typing import Callable, Dict, List, Optional
import typing

import gi
gi.require_versions({"Grl": "0.3", "Tracker": "3.0"})
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


class GrlTrackerWrapper(GObject.GObject):
    """Wrapper for the Grilo Tracker source.
    """

    _SPLICE_SIZE: int = 100

    _METADATA_ALBUM_CHANGED_KEYS: List[int] = [
        Grl.METADATA_KEY_ARTIST,
        Grl.METADATA_KEY_ALBUM_ARTIST,
        Grl.METADATA_KEY_COMPOSER,
        Grl.METADATA_KEY_ID,
        Grl.METADATA_KEY_PUBLICATION_DATE,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_URL
    ]

    _METADATA_SONG_FILL_KEYS: List[int] = [
        Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_ALBUM_DISC_NUMBER,
        Grl.METADATA_KEY_ARTIST,
        Grl.METADATA_KEY_DURATION,
        Grl.METADATA_KEY_FAVOURITE,
        Grl.METADATA_KEY_ID,
        Grl.METADATA_KEY_PLAY_COUNT,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_TRACK_NUMBER,
        Grl.METADATA_KEY_URL
    ]

    _METADATA_SONG_MEDIA_QUERY_KEYS: List[int] = [
        Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_ALBUM_DISC_NUMBER,
        Grl.METADATA_KEY_ARTIST,
        Grl.METADATA_KEY_DURATION,
        Grl.METADATA_KEY_FAVOURITE,
        Grl.METADATA_KEY_ID,
        Grl.METADATA_KEY_PLAY_COUNT,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_TRACK_NUMBER,
        Grl.METADATA_KEY_URL
    ]

    _METADATA_THUMBNAIL_KEYS: List[int] = [
        Grl.METADATA_KEY_ID,
        Grl.METADATA_KEY_THUMBNAIL
    ]

    def __init__(
            self, source: Grl.Source, application: Application,
            tracker_wrapper: TrackerWrapper) -> None:
        """Initialize the Tracker wrapper

        :param Grl.TrackerSource source: The Tracker source to wrap
        :param Application application: Application instance
        :param TrackerWrapper tracker_wrapper: The TrackerWrapper instance
        """
        super().__init__()

        self._application: Application = application
        cm: CoreModel = application.props.coremodel
        self._log: MusicLogger = application.props.log
        self._songs_model = Gio.ListStore.new(CoreSong)
        cm.props.songs_proxy.append(self._songs_model)
        self._source: Optional[Grl.Source] = None
        self._albums_model = Gio.ListStore.new(CoreAlbum)
        cm.props.albums_proxy.append(self._albums_model)
        self._album_ids: Dict[str, CoreAlbum] = {}
        self._artists_model = Gio.ListStore.new(CoreArtist)
        cm.props.artists_proxy.append(self._artists_model)
        self._artist_ids: Dict[str, CoreArtist] = {}
        self._hash: Dict[str, CoreSong] = {}
        self._batch_changed_media_ids: Dict[
            Grl.SourceChangeType, List[str]] = {}
        self._content_changed_timeout: int = 0
        self._tracker_playlists: Optional[GrlTrackerPlaylists] = None
        self._tracker_wrapper: TrackerWrapper = tracker_wrapper
        self._notificationmanager: NotificationManager = (
            application.props.notificationmanager)

        self._songs_search: Gtk.FilterListModel = Gtk.FilterListModel.new(
            self._songs_model)
        self._songs_search.set_filter(Gtk.AnyFilter())
        cm.props.songs_search_proxy.append(self._songs_search)

        self._albums_search: Gtk.FilterListModel = Gtk.FilterListModel.new(
            self._albums_model)
        self._albums_search.set_filter(Gtk.AnyFilter())
        cm.props.albums_search_proxy.append(self._albums_search)

        self._artists_search: Gtk.FilterListModel = Gtk.FilterListModel.new(
            self._artists_model)
        self._artists_search.set_filter(Gtk.AnyFilter())
        cm.props.artists_search_proxy.append(self._artists_search)

        self._fast_options: Grl.OperationOptions = Grl.OperationOptions()
        self._fast_options.set_type_filter(Grl.TypeFilter.AUDIO)
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY)

        self._fast_options_lprio = Grl.OperationOptions()
        self._fast_options_lprio.set_type_filter(Grl.TypeFilter.AUDIO)
        self._fast_options_lprio.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self._full_options: Grl.OperationOptions = Grl.OperationOptions()
        self._full_options.set_type_filter(Grl.TypeFilter.AUDIO)
        self._full_options.set_resolution_flags(
            Grl.ResolutionFlags.FULL)

        self._full_options_lprio = Grl.OperationOptions()
        self._full_options_lprio.set_type_filter(Grl.TypeFilter.AUDIO)
        self._full_options_lprio.set_resolution_flags(
            Grl.ResolutionFlags.FULL | Grl.ResolutionFlags.IDLE_RELAY)

        self._content_changed_id: int = 0
        self._grilo_search_operation_ids: List[int] = []

        self.props.source = source

        self._initial_songs_fill()
        self._initial_albums_fill()
        self._initial_artists_fill()

    @GObject.Property(type=Grl.Source, default=None)
    def source(self) -> Grl.Source:
        return self._source

    @source.setter  # type: ignore
    def source(self, new_source: Grl.Source):
        """Set a new grilo tracker source

        Everytime, the tracker plugin is loaded, a new source is
        created. The source needs to be updated to get notifications.

        :param Grl.Source new_source: new grilo tracker source
        """
        if self._content_changed_id != 0:
            self._source.disconnect(self._content_changed_id)
            self._content_changed_id = 0

        self._source = new_source
        self._source.notify_change_start()
        self._content_changed_id = self._source.connect(
            "content-changed", self._batch_content_changed)

    def _batch_content_changed(
            self, source: Grl.Source, medias: List[Grl.Media],
            change_type: Grl.SourceChangeType, loc_unknown: bool) -> None:
        if medias == []:
            return

        if change_type not in self._batch_changed_media_ids.keys():
            self._batch_changed_media_ids[change_type] = []

        # Remove notifications contain two events for the same file.
        # One event as a file uri and the other one as a
        # nie:InformationElement. Only the nie:InformationElement event
        # needs to be kept because it is saved in the hash.
        changed_medias = [
            media.get_id() for media in medias
            if ((media.is_audio() or media.is_container())
                and media.get_id().startswith("urn:"))]
        self._batch_changed_media_ids[change_type].extend(changed_medias)

        if self._content_changed_timeout == 0:
            self._content_changed_timeout = GLib.timeout_add(
                250, self._on_content_changed)

    def _on_content_changed(self) -> bool:
        for change_type in self._batch_changed_media_ids.keys():
            media_ids: List[str] = self._batch_changed_media_ids[change_type]

            # The Tracker indexed paths may differ from Music's paths.
            # In that case Tracker will report it as 'changed', while
            # it means 'added' to Music.
            if (change_type == Grl.SourceChangeType.CHANGED
                    or change_type == Grl.SourceChangeType.ADDED):
                self._log.debug(
                    "Added/Changed media(s): {}".format(media_ids))
                self._changed_media(media_ids)
            elif change_type == Grl.SourceChangeType.REMOVED:
                self._log.debug(
                    "Removed media(s): {}".format(media_ids))
                self._remove_media(media_ids)

        self._check_album_change()
        self._check_artist_change()
        if self._tracker_playlists is not None:
            self._tracker_playlists.check_smart_playlist_change()

        self._batch_changed_media_ids = {}
        self._content_changed_timeout = 0

        return GLib.SOURCE_REMOVE

    def _check_album_change(self) -> None:
        album_ids: Dict[str, CoreAlbum] = {}

        query = """
        SELECT
            ?type ?id ?title ?composer ?albumArtist
            ?artist ?url ?publicationDate
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT
                        %(media_type)s AS ?type
                        ?album AS ?id
                        nie:title(?album) AS ?title
                        ?composer
                        ?albumArtist
                        nmm:artistName(?artist) AS ?artist
                        nie:isStoredAs(?song) AS ?url
                        YEAR(MAX(nie:contentCreated(?song)))
                            AS ?publicationDate
                    WHERE {
                        ?album a nmm:MusicAlbum .
                        ?song a nmm:MusicPiece ;
                                nmm:musicAlbum ?album ;
                                nmm:artist ?artist .
                        OPTIONAL { ?song nmm:composer/
                                         nmm:artistName ?composer . }
                        OPTIONAL { ?album nmm:albumArtist/
                                          nmm:artistName ?albumArtist . }
                        %(location_filter)s
                    } GROUP BY ?album
                }
            }
        }
        """.replace('\n', ' ').strip() % {
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
            "media_type": int(Grl.MediaType.CONTAINER),
            'location_filter': self._tracker_wrapper.location_filter()
        }

        def check_album_cb(
                source: Grl.Source, op_id: int, media: Optional[Grl.Media],
                remaining: int, error: str) -> None:
            if error:
                self._log.warning("Error: {}".format(error))
                return

            if not media:
                changed_ids = set(
                    album_ids.keys()) ^ set(self._album_ids.keys())

                self._log.debug(
                    "Albums changed ID's: {}".format(changed_ids))

                for key in changed_ids:
                    if key in album_ids:
                        self._albums_model.append(album_ids[key])
                    elif key in self._album_ids:
                        for idx, corealbum in enumerate(self._albums_model):
                            if corealbum.media.get_id() == key:
                                self._albums_model.remove(idx)
                                break

                self._album_ids = album_ids
                return

            if media.get_id() in self._album_ids.keys():
                album = self._album_ids[media.get_id()]
            else:
                album = CoreAlbum(self._application, media)

            album_ids[media.get_id()] = album

        self.props.source.query(
            query, self._METADATA_ALBUM_CHANGED_KEYS, self._fast_options,
            check_album_cb)

    def _check_artist_change(self) -> None:
        artist_ids: Dict[str, CoreArtist] = {}

        query = """
        SELECT ?type ?id ?artist
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT
                        %(media_type)s AS ?type
                        (COALESCE(?album_artist, ?artist) AS ?id)
                        ?artist_bind AS ?artist
                    WHERE {
                        ?song a nmm:MusicPiece;
                                nmm:musicAlbum ?album;
                                nmm:artist ?artist .
                        OPTIONAL {
                            ?album a nmm:MusicAlbum;
                                     nmm:albumArtist ?album_artist .
                        }
                        BIND(COALESCE(nmm:artistName(?album_artist),
                                      nmm:artistName(?artist)) AS ?artist_bind)
                        %(location_filter)s
                    }
                    GROUP BY ?artist_bind
                }
            }
        }
        """.replace('\n', ' ').strip() % {
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
            "media_type": int(Grl.MediaType.CONTAINER),
            'location_filter': self._tracker_wrapper.location_filter()
        }

        metadata_keys = [
            Grl.METADATA_KEY_ALBUM_ARTIST,
            Grl.METADATA_KEY_ARTIST,
            Grl.METADATA_KEY_ID
        ]

        def check_artist_cb(
                source: Grl.Source, op_id: int, media: Optional[Grl.Media],
                remaining: int, error: Optional[GLib.Error]) -> None:
            if error:
                self._log.warning("Error: {}".format(error))
                return

            if not media:
                changed_ids = set(
                    artist_ids.keys()) ^ set(self._artist_ids.keys())
                self._log.debug(
                    "Artists changed ID's: {}".format(changed_ids))

                for key in changed_ids:
                    if key in artist_ids:
                        self._artists_model.append(artist_ids[key])
                    elif key in self._artist_ids:
                        for idx, coreartist in enumerate(self._artists_model):
                            if coreartist.media.get_id() == key:
                                self._artists_model.remove(idx)
                                break

                self._artist_ids = artist_ids
                return

            if media.get_id() in self._artist_ids.keys():
                artist = self._artist_ids[media.get_id()]
            else:
                artist = CoreArtist(self._application, media)

            artist_ids[media.get_id()] = artist

        self.props.source.query(
            query, metadata_keys, self._fast_options, check_artist_cb)

    def _remove_media(self, media_ids: List[str]) -> None:
        for media_id in media_ids:
            try:
                coresong = self._hash.pop(media_id)
            except KeyError:
                self._log.warning("Removal KeyError.")
                return

            for idx, coresong_model in enumerate(self._songs_model):
                if coresong_model is coresong:
                    self._log.debug("Removing: {}, {}".format(
                        coresong.props.media.get_id(), coresong.props.title))

                    self._songs_model.remove(idx)
                    break

    def _song_media_query(self, ids: Optional[List[str]] = None) -> str:
        """Returns a songs query string

        :param list ids: List of Media ids to filter by or None
        """
        songs_filter = ""
        if ids is not None:
            media_ids = ", ".join([f"<{media_id}>" for media_id in ids])
            songs_filter = f"FILTER ( ?song in ( {media_ids} ) )"

        location_filter = self._tracker_wrapper.location_filter()
        media_type = int(Grl.MediaType.AUDIO)
        miner_fs_busname = self._tracker_wrapper.props.miner_fs_busname
        query = " ".join(f"""
        SELECT
            ?type ?urn ?title ?id ?url
            ?artist ?album
            ?duration ?trackNumber
            ?albumDiscNumber
            nie:contentAccessed(?urn) AS ?lastPlayed
            nie:usageCounter(?urn) AS ?playCount
            ?tag AS ?favorite
        WHERE {{
            SERVICE <dbus:{miner_fs_busname}> {{
                GRAPH tracker:Audio {{
                    SELECT DISTINCT
                        {media_type} AS ?type
                        ?song AS ?urn
                        nie:title(?song) AS ?title
                        ?song AS ?id
                        nie:isStoredAs(?song) AS ?url
                        nmm:artistName(nmm:artist(?song)) AS ?artist
                        nie:title(nmm:musicAlbum(?song)) AS ?album
                        nfo:duration(?song) AS ?duration
                        nmm:trackNumber(?song) AS ?trackNumber
                        nmm:setNumber(nmm:musicAlbumDisc(?song))
                            AS ?albumDiscNumber
                    WHERE {{
                        ?song a nmm:MusicPiece .
                        {songs_filter}
                        {location_filter}
                    }}
                }}
            }}
            OPTIONAL {{
                ?urn nao:hasTag ?tag .
                FILTER (?tag = nao:predefined-tag-favorite)
            }}
        }} ORDER BY ?title ?artist
        """.split())

        return query

    def _changed_media(self, media_ids: List[str]) -> None:

        def _update_changed_media(
                source: Grl.Source, op_id: int, media: Optional[Grl.Media],
                remaining: int, error: Optional[GLib.Error]) -> None:
            if error:
                self._log.warning("Error: {}".format(error))
                return

            if not media:
                self._remove_media(media_ids)
                return

            media_id: str = media.get_id()
            if media_id not in self._hash:
                song = CoreSong(self._application, media)
                self._songs_model.append(song)
                self._hash[media_id] = song
                self._log.debug(
                    "Adding: {}, {}".format(media_id, song.props.title))
            else:
                self._hash[media_id].update(media)

            media_ids.remove(media_id)

        self.props.source.query(
            self._song_media_query(media_ids),
            self._METADATA_SONG_MEDIA_QUERY_KEYS, self._fast_options,
            _update_changed_media)

    def _initial_songs_fill(self) -> None:
        self._notificationmanager.push_loading()
        songs_added: List[int] = []

        def _add_to_model(
                source: Grl.Source, op_id: int, media: Optional[Grl.Media],
                remaining: int, error: Optional[GLib.Error]) -> None:
            if error:
                self._log.warning("Error: {}".format(error))
                self._notificationmanager.pop_loading()
                return

            if not media:
                self._songs_model.splice(
                    self._songs_model.get_n_items(), 0, songs_added)
                self._notificationmanager.pop_loading()

                # Initialize the playlists subwrapper after the initial
                # songs model fill, the playlists expect a filled songs
                # hashtable.
                self._tracker_playlists = GrlTrackerPlaylists(
                    self.props.source, self._application,
                    self._tracker_wrapper, self._hash)

                return

            song = CoreSong(self._application, media)
            songs_added.append(song)
            self._hash[media.get_id()] = song
            if len(songs_added) == self._SPLICE_SIZE:
                self._songs_model.splice(
                    self._songs_model.get_n_items(), 0, songs_added)
                songs_added.clear()

        self.props.source.query(
            self._song_media_query(), self._METADATA_SONG_FILL_KEYS,
            self._fast_options, _add_to_model)

    def _initial_albums_fill(self) -> None:
        self._notificationmanager.push_loading()
        albums_added: List[int] = []

        def _add_to_albums_model(
                source: Grl.Source, op_id: int, media: Optional[Grl.Media],
                remaining: int, error: Optional[GLib.Error]) -> None:
            if error:
                self._log.warning("Error: {}".format(error))
                self._notificationmanager.pop_loading()
                return

            if not media:
                self._albums_model.splice(
                    self._albums_model.get_n_items(), 0, albums_added)
                self._notificationmanager.pop_loading()
                return

            album = CoreAlbum(self._application, media)
            self._album_ids[media.get_id()] = album
            albums_added.append(album)
            if len(albums_added) == self._SPLICE_SIZE:
                self._albums_model.splice(
                    self._albums_model.get_n_items(), 0, albums_added)
                albums_added.clear()

        query = """
        SELECT
            ?type ?id ?title ?composer ?albumArtist
            ?artist ?url ?publicationDate
        WHERE
        {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT
                        %(media_type)s AS ?type
                        ?album AS ?id
                        nie:title(?album) AS ?title
                        ?composer
                        ?albumArtist
                        nmm:artistName(?artist) AS ?artist
                        nie:isStoredAs(?song) AS ?url
                        YEAR(MAX(nie:contentCreated(?song)))
                            AS ?publicationDate
                    WHERE
                    {
                        ?album a nmm:MusicAlbum .
                        ?song a nmm:MusicPiece ;
                                nmm:musicAlbum ?album ;
                                nmm:artist ?artist .
                        OPTIONAL { ?song nmm:composer/
                                         nmm:artistName ?composer . }
                        OPTIONAL { ?album nmm:albumArtist/
                                          nmm:artistName ?albumArtist . }
                        %(location_filter)s
                    }
                    GROUP BY ?album
                    ORDER BY ?title ?albumArtist ?artist ?publicationDate
                }
            }
        }
        """.replace('\n', ' ').strip() % {
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
            "media_type": int(Grl.MediaType.CONTAINER),
            'location_filter': self._tracker_wrapper.location_filter()
        }

        self.props.source.query(
            query, self._METADATA_ALBUM_CHANGED_KEYS, self._fast_options,
            _add_to_albums_model)

    def _initial_artists_fill(self) -> None:
        self._notificationmanager.push_loading()
        artists_added: List[int] = []

        def _add_to_artists_model(
                source: Grl.Source, op_id: int, media: Optional[Grl.Media],
                remaining: int, error: Optional[GLib.Error]) -> None:
            if error:
                self._log.warning("Error: {}".format(error))
                self._notificationmanager.pop_loading()
                return

            if not media:
                self._artists_model.splice(
                    self._artists_model.get_n_items(), 0, artists_added)
                self._notificationmanager.pop_loading()
                return

            artist = CoreArtist(self._application, media)
            self._artist_ids[media.get_id()] = artist
            artists_added.append(artist)
            if len(artists_added) == self._SPLICE_SIZE:
                self._artists_model.splice(
                    self._artists_model.get_n_items(), 0, artists_added)
                artists_added.clear()

        query = """
        SELECT ?type ?id ?artist
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT
                       %(media_type)s AS ?type
                       (COALESCE(?album_artist, ?artist) AS ?id)
                       ?artist_bind AS ?artist
                    WHERE {
                        ?song a nmm:MusicPiece;
                                nmm:musicAlbum ?album;
                                nmm:artist ?artist .
                        OPTIONAL {
                            ?album a nmm:MusicAlbum;
                                     nmm:albumArtist ?album_artist .
                        }
                        BIND(COALESCE(nmm:artistName(?album_artist),
                                      nmm:artistName(?artist)) AS ?artist_bind)
                        %(location_filter)s
                    }
                    GROUP BY ?artist_bind
                    ORDER BY ?artist_bind
                }
            }
        }
        """.replace('\n', ' ').strip() % {
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
            "media_type": int(Grl.MediaType.CONTAINER),
            'location_filter': self._tracker_wrapper.location_filter()
        }

        metadata_keys: List[int] = [
            Grl.METADATA_KEY_ARTIST,
            Grl.METADATA_KEY_ID
        ]

        self.props.source.query(
            query, metadata_keys, self._fast_options, _add_to_artists_model)

    def get_artist_albums(
            self, media: Grl.Source, model: Gtk.FilterListModel) -> None:
        """Get all albums by an artist

        :param Grl.Media media: The media with the artist id
        :param Gtk.FilterListModel model: The model to fill
        """
        self._notificationmanager.push_loading()
        artist_id = media.get_id()

        query = """
        SELECT
            ?type ?id ?title ?publicationDate
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT DISTINCT
                        %(media_type)s AS ?type
                        ?album AS ?id
                        nie:title(?album) AS ?title
                        nie:contentCreated(?song) AS ?publicationDate
                    WHERE {
                        ?album a nmm:MusicAlbum .
                        OPTIONAL { ?album  nmm:albumArtist ?album_artist . }
                        ?song a nmm:MusicPiece;
                              nmm:musicAlbum ?album;
                              nmm:artist ?artist .
                        FILTER ( ?album_artist = <%(artist_id)s>
                                 || ?artist = <%(artist_id)s> )
                        %(location_filter)s
                    }
                   GROUP BY ?album
                   ORDER BY ?publicationDate ?album
                }
            }
        }
        """.replace('\n', ' ').strip() % {
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
            "media_type": int(Grl.MediaType.CONTAINER),
            "artist_id": artist_id,
            'location_filter': self._tracker_wrapper.location_filter()
        }

        albums: List[str] = []

        def query_cb(
                source: Grl.Source, op_id: int, media: Optional[Grl.Media],
                remaining: int, error: Optional[GLib.Error]) -> None:
            if error:
                self._log.warning("Error: {}".format(error))
                self._notificationmanager.pop_loading()
                return

            if not media:
                custom_filter = Gtk.CustomFilter()
                custom_filter.set_filter_func(albums_filter, albums)
                model.set_filter(custom_filter)
                self._notificationmanager.pop_loading()
                return

            albums.append(media.get_id())

        def albums_filter(corealbum: CoreAlbum, albums: List[str]) -> bool:
            return corealbum.props.media.get_id() in albums

        self.props.source.query(
            query, [Grl.METADATA_KEY_TITLE], self._fast_options, query_cb)

    def get_album_discs(
            self, media: Grl.Media, disc_model: Gtk.SortListModel) -> None:
        """Get all discs of an album

        :param Grl.Media media: The media with the album id
        :param Gtk.SortListModel disc_model: The model to fill
        """
        self._notificationmanager.push_loading()
        album_id = media.get_id()

        query = """
        SELECT
            ?type ?id ?albumDiscNumber
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT DISTINCT
                        %(media_type)s AS ?type
                        ?album AS ?id
                        nmm:setNumber(nmm:musicAlbumDisc(?song))
                            AS ?albumDiscNumber
                    WHERE {
                        ?song a nmm:MusicPiece;
                                nmm:musicAlbum ?album .
                        FILTER ( ?album = <%(album_id)s> )
                        %(location_filter)s
                    }
                    ORDER BY ?albumDiscNumber
                }
            }
        }
        """.replace('\n', ' ').strip() % {
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
            "media_type": int(Grl.MediaType.CONTAINER),
            "album_id": album_id,
            'location_filter': self._tracker_wrapper.location_filter()
        }

        def _disc_nr_cb(
                source: Grl.Source, op_id: int, media: Optional[Grl.Media],
                remaining: int, error: Optional[GLib.Error]) -> None:
            if error:
                self._log.warning("Error: {}".format(error))
                self._notificationmanager.pop_loading()
                return

            if not media:
                self._notificationmanager.pop_loading()
                return

            disc_nr = media.get_album_disc_number()
            coredisc = CoreDisc(self._application, media, disc_nr)
            disc_model.append(coredisc)

        self.props.source.query(
            query, [Grl.METADATA_KEY_ALBUM_DISC_NUMBER], self._fast_options,
            _disc_nr_cb)

    def get_album_disc(
            self, media: Grl.Media, disc_nr: int,
            model: Gtk.FilterListModel) -> None:
        """Get all songs of an album disc

        :param Grl.Media media: The media with the album id
        :param int disc_nr: The disc number
        :param Gtk.FilterListModel model: The model to fill
        """
        album_id = media.get_id()

        query = """
        SELECT
            ?type ?id ?url ?title
            ?artist ?album
            ?duration ?trackNumber ?albumDiscNumber
            ?publicationDate
            nie:usageCounter(?id) AS ?playCount
            ?tag AS ?favorite
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT DISTINCT
                        %(media_type)s AS ?type
                        ?song AS ?id
                        nie:isStoredAs(?song) AS ?url
                        nie:title(?song) AS ?title
                        nmm:artistName(nmm:artist(?song)) AS ?artist
                        nie:title(nmm:musicAlbum(?song)) AS ?album
                        nfo:duration(?song) AS ?duration
                        nmm:trackNumber(?song) AS ?trackNumber
                        nmm:setNumber(nmm:musicAlbumDisc(?song))
                            AS ?albumDiscNumber
                        YEAR(?date) AS ?publicationDate
                    WHERE {
                        ?song a nmm:MusicPiece ;
                                nmm:musicAlbum ?album .
                        OPTIONAL { ?song nie:contentCreated ?date . }
                        FILTER (
                            ?album = <%(album_id)s> &&
                            nmm:setNumber(nmm:musicAlbumDisc(?song)) =
                                %(disc_nr)s
                        )
                        %(location_filter)s
                    }
                    ORDER BY ?trackNumber
                }
            }
            OPTIONAL {
                ?id nao:hasTag ?tag .
                FILTER (?tag = nao:predefined-tag-favorite)
            }
        }
        """.replace('\n', ' ').strip() % {
            "media_type": int(Grl.MediaType.AUDIO),
            'album_id': album_id,
            'disc_nr': disc_nr,
            'location_filter': self._tracker_wrapper.location_filter(),
            'miner_fs_busname': self._tracker_wrapper.props.miner_fs_busname
        }

        metadata_keys: List[int] = [
            Grl.METADATA_KEY_ALBUM,
            Grl.METADATA_KEY_ALBUM_DISC_NUMBER,
            Grl.METADATA_KEY_ARTIST,
            Grl.METADATA_KEY_DURATION,
            Grl.METADATA_KEY_FAVOURITE,
            Grl.METADATA_KEY_ID,
            Grl.METADATA_KEY_PLAY_COUNT,
            Grl.METADATA_KEY_TITLE,
            Grl.METADATA_KEY_URL
        ]

        disc_song_ids: List[str] = []

        def _filter_func(coresong: CoreSong) -> bool:
            return coresong.props.grlid in disc_song_ids

        def _callback(
                source: Grl.Source, op_id: int, media: Grl.Media,
                remaining: int, error: GLib.Error) -> None:
            if error:
                self._log.warning(f"Error: {error.domain}, {error.message}")
                return

            if media is None:
                custom_filter = Gtk.CustomFilter()
                custom_filter.set_filter_func(_filter_func)
                model.set_filter(custom_filter)
                return

            disc_song_ids.append(media.get_source() + media.get_id())

        self.props.source.query(
            query, metadata_keys, self._fast_options, _callback)

    def _search_artist(self, term: str) -> None:
        """Search the artist tag and display results.."""
        self._notificationmanager.push_loading()

        query = """
        SELECT
            ?type ?id
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT DISTINCT
                        %(media_type)s AS ?type
                        COALESCE(?album_artist, ?artist) AS ?id
                    WHERE {
                        ?song a nmm:MusicPiece ;
                                nmm:musicAlbum ?album ;
                                nmm:artist ?artist .
                        OPTIONAL {
                            ?album a nmm:MusicAlbum ;
                                     nmm:albumArtist ?album_artist .
                        }
                        BIND(COALESCE(nmm:artistName(?album_artist),
                                      nmm:artistName(?artist)) AS ?artist_bind)
                        BIND(tracker:normalize(nmm:artistName(
                                 nmm:albumArtist(?artist_bind)), 'nfkd')
                             AS ?match1) .
                        BIND(tracker:normalize(
                                 nmm:artistName(nmm:artist(?song)), 'nfkd')
                             AS ?match2) .
                        BIND(tracker:normalize(nmm:composer(?song), 'nfkd')
                             AS ?match4) .
                        FILTER (
                            CONTAINS(tracker:case-fold(
                                tracker:unaccent(?match1)), "%(name)s")
                            || CONTAINS(tracker:case-fold(?match1), "%(name)s")
                            || CONTAINS(tracker:case-fold(
                                tracker:unaccent(?match2)), "%(name)s")
                            || CONTAINS(tracker:case-fold(?match2), "%(name)s")
                            || CONTAINS(tracker:case-fold(
                                tracker:unaccent(?match4)), "%(name)s")
                            || CONTAINS(tracker:case-fold(?match4), "%(name)s")
                        )
                        %(location_filter)s
                    }
                    LIMIT 50
                }
            }
        }
        """.replace('\n', ' ').strip() % {
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
            "media_type": int(Grl.MediaType.AUDIO),
            'location_filter': self._tracker_wrapper.location_filter(),
            'name': term
        }

        self._run_query(query, self._artists_search)

    def _search_album(self, term: str) -> None:
        """Search the album tag and display results."""
        self._notificationmanager.push_loading()

        query = """
        SELECT
            ?type ?id
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT DISTINCT
                        %(media_type)s AS ?type
                        nmm:musicAlbum(?song) AS ?id
                    WHERE {
                        ?song a nmm:MusicPiece .
                        BIND(tracker:normalize(
                                 nie:title(nmm:musicAlbum(?song)), 'nfkd')
                             AS ?match1) .
                        BIND(tracker:normalize(
                                 nmm:artistName(nmm:artist(?song)), 'nfkd')
                             AS ?match2) .
                        BIND(tracker:normalize(nmm:composer(?song), 'nfkd')
                             AS ?match4) .
                        FILTER (
                            CONTAINS(tracker:case-fold(
                                tracker:unaccent(?match1)), "%(name)s")
                            || CONTAINS(tracker:case-fold(?match1), "%(name)s")
                            || CONTAINS(tracker:case-fold(
                                tracker:unaccent(?match2)), "%(name)s")
                            || CONTAINS(tracker:case-fold(?match2), "%(name)s")
                            || CONTAINS(tracker:case-fold(
                                tracker:unaccent(?match4)), "%(name)s")
                            || CONTAINS(tracker:case-fold(?match4), "%(name)s")
                        )
                        %(location_filter)s
                    }
                    LIMIT 50
                }
            }
        }
        """.replace('\n', ' ').strip() % {
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
            "media_type": int(Grl.MediaType.CONTAINER),
            'location_filter': self._tracker_wrapper.location_filter(),
            'name': term
        }

        self._run_query(query, self._albums_search)

    def _search_song(self, term: str) -> None:
        """Search for song names and display results."""
        self._notificationmanager.push_loading()

        query = """
        SELECT
            ?type ?id
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT DISTINCT
                        %(media_type)s AS ?type
                        ?song AS ?id
                    WHERE {
                        ?song a nmm:MusicPiece .
                        BIND(tracker:normalize(
                                 nie:title(nmm:musicAlbum(?song)), 'nfkd')
                             AS ?match1) .
                        BIND(tracker:normalize(
                                 nmm:artistName(nmm:artist(?song)), 'nfkd')
                             AS ?match2) .
                        BIND(tracker:normalize(
                            nie:title(?song), 'nfkd') AS ?match3) .
                        BIND(tracker:normalize(nmm:composer(?song), 'nfkd')
                             AS ?match4) .
                        FILTER (
                            CONTAINS(tracker:case-fold(
                                tracker:unaccent(?match1)), "%(name)s")
                            || CONTAINS(tracker:case-fold(?match1), "%(name)s")
                            || CONTAINS(tracker:case-fold(
                                tracker:unaccent(?match2)), "%(name)s")
                            || CONTAINS(tracker:case-fold(?match2), "%(name)s")
                            || CONTAINS(tracker:case-fold(
                                tracker:unaccent(?match3)), "%(name)s")
                            || CONTAINS(tracker:case-fold(?match3), "%(name)s")
                            || CONTAINS(tracker:case-fold(
                                tracker:unaccent(?match4)), "%(name)s")
                            || CONTAINS(tracker:case-fold(?match4), "%(name)s")
                        )
                        %(location_filter)s
                    }
                    LIMIT 50
                }
            }
        }
        """.replace('\n', ' ').strip() % {
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
            "media_type": int(Grl.MediaType.AUDIO),
            'location_filter': self._tracker_wrapper.location_filter(),
            'name': term
        }

        self._run_query(query, self._songs_search)

    def _run_query(
            self, query: str, filter_list_model: Gtk.FilterListModel) -> None:
        """Run a SPARQL query and display results."""
        filter_ids: List[str] = []

        def filter_func(obj: GObject.GObject) -> bool:
            return obj.media.get_id() in filter_ids

        def _search_callback(
                source: Grl.Source, op_id: int, media: Optional[Grl.Media],
                remaining: int, error: Optional[GLib.Error]) -> None:
            if error:
                if error.code != Grl.CoreError.OPERATION_CANCELLED:
                    self._log.warning("Error: {}".format(error))
                    self._albums_search.set_filter(Gtk.AnyFilter())
                    self._grilo_search_operation_ids.remove(op_id)
                self._notificationmanager.pop_loading()
                return

            if not media:
                custom_filter = Gtk.CustomFilter()
                custom_filter.set_filter_func(filter_func)
                filter_list_model.set_filter(custom_filter)
                # If a search does not change the number of items found,
                # SearchView will not update without a signal.
                filter_list_model.emit("items-changed", 0, 0, 0)

                self._notificationmanager.pop_loading()
                self._grilo_search_operation_ids.remove(op_id)
                return

            filter_ids.append(media.get_id())

        op_id = self.props.source.query(
            query, [Grl.METADATA_KEY_ID], self._fast_options, _search_callback)
        self._grilo_search_operation_ids.append(op_id)

    def search(self, text: str) -> None:
        """Do a search in all relevant tags and display results.

        :param str text: An arbitrary user-defined search string.
        """
        # FIXME: Searches are limited to not bog down the UI with
        # widget creation ({List,Flow}Box limitations). The limit is
        # arbitrarily set to 50 and set in the Tracker query. It should
        # be possible to set it through Grilo options instead. This
        # does not work as expected and needs further investigation.
        term: str = Tracker.sparql_escape_string(
            GLib.utf8_normalize(
                GLib.utf8_casefold(text, -1), -1, GLib.NormalizeMode.NFKD))

        for operation_id in self._grilo_search_operation_ids:
            Grl.operation_cancel(operation_id)
            self._grilo_search_operation_ids.remove(operation_id)

        if text == "":
            self._artists_search.set_filter(Gtk.AnyFilter())
            self._albums_search.set_filter(Gtk.AnyFilter())
            self._songs_search.set_filter(Gtk.AnyFilter())
            return

        self._search_artist(term)
        self._search_album(term)
        self._search_song(term)

    def _get_album_for_media_id_query(
            self, media_id: str, song: bool = True) -> str:
        # Even though we check for the album_artist, we fill
        # the artist key, since Grilo coverart plugins use
        # only that key for retrieval.

        if song:
            filter_clause = "?song = <{}>".format(str(media_id))
        else:
            filter_clause = "?album = <{}>".format(str(media_id))

        query = """
        SELECT
            ?type ?id ?mbReleaseGroup ?mbRelease ?artist ?album
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT DISTINCT
                        %(media_type)s AS ?type
                        ?album AS ?id
                        tracker:referenceIdentifier(?release_group_id)
                            AS ?mbReleaseGroup
                        tracker:referenceIdentifier(?release_id) AS ?mbRelease
                        tracker:coalesce(nmm:artistName(?album_artist),
                                         nmm:artistName(?song_artist))
                            AS ?artist
                        nie:title(?album) AS ?album
                    WHERE {
                        ?album a nmm:MusicAlbum .
                        ?song a nmm:MusicPiece ;
                                nmm:musicAlbum ?album ;
                                nmm:artist ?song_artist .
                        OPTIONAL {
                            ?album tracker:hasExternalReference
                                ?release_group_id .
                            ?release_group_id tracker:referenceSource
                                "https://musicbrainz.org/doc/Release_Group" .
                        }
                        OPTIONAL {
                            ?album tracker:hasExternalReference ?release_id .
                            ?release_id tracker:referenceSource
                                "https://musicbrainz.org/doc/Release" .
                        }
                        OPTIONAL { ?album nmm:albumArtist ?album_artist . }
                        FILTER (
                            %(filter_clause)s
                        )
                        %(location_filter)s
                    }
                }
            }
        }
        """.replace("\n", " ").strip() % {
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
            "media_type": int(Grl.MediaType.CONTAINER),
            "filter_clause": filter_clause,
            "location_filter": self._tracker_wrapper.location_filter()
        }

        return query

    def get_song_art(self, coresong: CoreSong) -> None:
        """Retrieve song art for the given CoreSong

        Since MediaArt does not really support per-song art this
        uses the songs album information as base to retrieve relevant
        art and store it.

        :param CoreSong coresong: CoreSong to get art for
        """
        media: Grl.Media = coresong.props.media

        # If there is no album and artist do not go through with the
        # query, it will not give any results.
        if (media.get_album() is None
                and (media.get_album_artist() is None
                     or media.get_artist() is None)):
            return

        def art_retrieved_cb(
                source: Grl.Source, op_id: int,
                queried_media: Optional[Grl.Media], remaining: int,
                error: Optional[GLib.Error]) -> None:
            if error:
                self._log.warning("Error: {}".format(error))
                return

            if queried_media is None:
                return

            StoreArt().start(
                coresong, queried_media.get_thumbnail(), CoreObjectType.SONG)

        song_id: str = media.get_id()
        query: str = self._get_album_for_media_id_query(song_id)

        self.props.source.query(
            query, self._METADATA_THUMBNAIL_KEYS, self._full_options_lprio,
            art_retrieved_cb)

    def get_album_art(self, corealbum: CoreAlbum) -> None:
        """Retrieve album art for the given CoreAlbum

        :param CoreAlbum corealbum: CoreAlbum to get art for
        """
        media: Grl.Media = corealbum.props.media

        def art_retrieved_cb(
                source: Grl.Source, op_id: int,
                queried_media: Optional[Grl.Media], remaining: int,
                error: Optional[GLib.Error]) -> None:
            if error:
                self._log.warning("Error: {}".format(error))
                return

            if queried_media is None:
                return

            StoreArt().start(
                corealbum, queried_media.get_thumbnail(), CoreObjectType.ALBUM)

        album_id: str = media.get_id()
        query: str = self._get_album_for_media_id_query(album_id, False)

        self.props.source.query(
            query, self._METADATA_THUMBNAIL_KEYS, self._full_options_lprio,
            art_retrieved_cb)

    def get_artist_art(self, coreartist: CoreArtist) -> None:
        """Retrieve artist art for the given CoreArtist

        This retrieves art through Grilo online services only.

        :param CoreArtist coreartist: CoreArtist to get art for
        """
        media: Grl.Media = coreartist.props.media

        def art_resolved_cb(
                source: Grl.Source, op_id: int,
                resolved_media: Optional[Grl.Media],
                error: Optional[GLib.Error]) -> None:
            if error:
                self._log.warning("Error: {}".format(error))
                return

            if resolved_media is None:
                return

            thumbnail = resolved_media.get_thumbnail()
            if thumbnail is None:
                return

            StoreArt().start(coreartist, thumbnail, CoreObjectType.ARTIST)

        self.props.source.resolve(
            media, [Grl.METADATA_KEY_THUMBNAIL], self._full_options_lprio,
            art_resolved_cb)

    def stage_playlist_deletion(self, playlist: Optional[Playlist]) -> None:
        """Prepares playlist deletion.

        :param Playlist playlist: playlist
        """
        if self._tracker_playlists is None:
            return

        self._tracker_playlists.stage_playlist_deletion(playlist)

    def finish_playlist_deletion(
            self, playlist: Playlist, deleted: bool) -> None:
        """Finishes playlist deletion.

        :param Playlist playlist: playlist
        :param bool deleted: indicates if the playlist has been deleted
        """
        if self._tracker_playlists is None:
            return

        self._tracker_playlists.finish_playlist_deletion(playlist, deleted)

    def create_playlist(
            self, playlist_title: str,
            callback: Callable[[Playlist], None]) -> None:
        """Creates a new user playlist.

        :param str playlist_title: playlist title
        :param callback: function to perform once, the playlist is created
        """
        if self._tracker_playlists is None:
            return

        self._tracker_playlists.create_playlist(playlist_title, callback)
