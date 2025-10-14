# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from typing import Optional
import asyncio
import time

from gettext import gettext as _

from gi.repository import GLib, GObject, Gio

from gnomemusic.coresong import CoreSong
from gnomemusic.grilowrappers.playlist import Playlist
import gnomemusic.utils as utils


class SmartPlaylist(Playlist):
    """Base class for smart playlists"""

    __gtype_name__ = "SmartPlaylist"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.props.is_smart = True
        self._model: Optional[Gio.ListStore] = None

    @GObject.Property(type=Gio.ListStore, default=None)
    def model(self):
        if self._model is None:
            self._model = Gio.ListStore.new(CoreSong)
            asyncio.create_task(self._populate_model())

        return self._model

    async def _populate_model(self) -> None:
        async with self._notificationmanager:
            if self._model is None:
                return

            try:
                cursor = self._tsparql.query(self.props.query)
            except GLib.Error as error:
                self._log.warning(
                    f"Failure populating playlist model {self.props.pl_id}:"
                    f" {error.domain}, {error.message}")
                return

            try:
                has_next = await cursor.next_async()
            except GLib.Error as error:
                cursor.close()
                self._log.warning(
                    f"Cursor iteration error: {error.domain}, {error.message}")
                return
            while has_next:
                cursor_dict = utils.dict_from_cursor(cursor)
                coresong = CoreSong(self._application, cursor_dict)
                self._bind_to_main_song(coresong)
                if coresong not in self._songs_todelete:
                    self._model.append(coresong)

                try:
                    has_next = await cursor.next_async()
                except GLib.Error as error:
                    cursor.close()
                    self._log.warning(
                        f"Cursor iteration error: {error.domain}, "
                        f"{error.message}")
                    return
            else:
                cursor.close()
                self.props.count = self._model.get_n_items()

    def update(self):
        """Updates playlist model."""
        if self._model is None:
            return

        self._model.remove_all()
        asyncio.create_task(self._populate_model())

        return


class MostPlayed(SmartPlaylist):
    """Most Played smart playlist"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.props.tag_text = "MOST_PLAYED"
        # TRANSLATORS: this is a playlist name
        self._title = _("Most Played")
        self.props.icon_name = "audio-speakers-symbolic"
        self.props.query = """
        SELECT
            ?song AS ?id
            ?title
            ?url
            ?artist
            ?album
            ?duration
            ?trackNumber
            ?albumDiscNumber
            ?playCount
            ?tag AS ?favorite
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT
                        ?song
                        nie:title(?song) AS ?title
                        nie:isStoredAs(?song) AS ?url
                        nmm:artistName(nmm:artist(?song)) AS ?artist
                        nie:title(nmm:musicAlbum(?song)) AS ?album
                        nfo:duration(?song) AS ?duration
                        nmm:trackNumber(?song) AS ?trackNumber
                        nmm:setNumber(nmm:musicAlbumDisc(?song))
                            AS ?albumDiscNumber
                    WHERE {
                        ?song a nmm:MusicPiece .
                        %(location_filter)s
                    }
                }
            }
            ?song nie:usageCounter ?playCount
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        }
        ORDER BY DESC(?playCount) LIMIT 50
        """.replace('\n', ' ').strip() % {
            "location_filter": self._tsparql_wrapper.location_filter(),
            "miner_fs_busname": self._tsparql_wrapper.props.miner_fs_busname,
        }


class NeverPlayed(SmartPlaylist):
    """Never Played smart playlist"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.props.tag_text = "NEVER_PLAYED"
        # TRANSLATORS: this is a playlist name
        self._title = _("Never Played")
        self.props.icon_name = "deaf-symbolic"
        self.props.query = """
        SELECT
            ?song AS ?id
            ?title
            ?url
            ?artist
            ?album
            ?duration
            ?trackNumber
            ?albumDiscNumber
            nie:usageCounter(?song) AS ?playCount
            ?tag AS ?favorite
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT
                        ?song
                        nie:title(?song) AS ?title
                        nie:isStoredAs(?song) AS ?url
                        nmm:artistName(nmm:artist(?song)) AS ?artist
                        nie:title(nmm:musicAlbum(?song)) AS ?album
                        nfo:duration(?song) AS ?duration
                        nmm:trackNumber(?song) AS ?trackNumber
                        nmm:setNumber(nmm:musicAlbumDisc(?song))
                            AS ?albumDiscNumber
                    WHERE {
                        ?song a nmm:MusicPiece .
                        %(location_filter)s
                    }
                }
            }
            FILTER ( NOT EXISTS { ?song nie:usageCounter ?count .} )
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        } ORDER BY nfo:fileLastAccessed(?song) LIMIT 50
        """.replace('\n', ' ').strip() % {
            "location_filter": self._tsparql_wrapper.location_filter(),
            "miner_fs_busname": self._tsparql_wrapper.props.miner_fs_busname,
        }


class RecentlyPlayed(SmartPlaylist):
    """Recently Played smart playlist"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.props.tag_text = "RECENTLY_PLAYED"
        # TRANSLATORS: this is a playlist name
        self._title = _("Recently Played")
        self.props.icon_name = "document-open-recent-symbolic"

        sparql_midnight_dateTime_format = "%Y-%m-%dT00:00:00Z"
        days_difference = 7
        seconds_difference = days_difference * 86400
        compare_date = time.strftime(
            sparql_midnight_dateTime_format,
            time.gmtime(time.time() - seconds_difference))
        self.props.query = """
        SELECT
            ?song AS ?id
            ?title
            ?url
            ?artist
            ?album
            ?duration
            ?trackNumber
            ?albumDiscNumber
            nie:usageCounter(?song) AS ?playCount
            ?tag AS ?favorite
        WHERE {
            {
                SELECT
                    ?song
                    ?title
                    ?url
                    ?artist
                    ?album
                    ?duration
                    ?trackNumber
                    ?albumDiscNumber
                    ?playCount
                    ?tag
                    ?lastPlayed
                WHERE {
                    SERVICE <dbus:%(miner_fs_busname)s> {
                        GRAPH tracker:Audio {
                            SELECT
                                ?song
                                nie:title(?song) AS ?title
                                nie:isStoredAs(?song) AS ?url
                                nmm:artistName(nmm:artist(?song)) AS ?artist
                                nie:title(nmm:musicAlbum(?song)) AS ?album
                                nfo:duration(?song) AS ?duration
                                nmm:trackNumber(?song) AS ?trackNumber
                                nmm:setNumber(nmm:musicAlbumDisc(?song))
                                    AS ?albumDiscNumber
                            WHERE {
                                ?song a nmm:MusicPiece .
                                %(location_filter)s
                            }
                        }
                    }
                    ?song nie:contentAccessed ?lastPlayed ;
                        nie:usageCounter ?playCount .
                    OPTIONAL { ?song nao:hasTag ?tag .
                               FILTER (?tag = nao:predefined-tag-favorite) }
                } ORDER BY DESC(?lastPlayed) LIMIT 50
            }
            FILTER (?lastPlayed > '%(compare_date)s'^^xsd:dateTime)
        }
        """.replace('\n', ' ').strip() % {
            'compare_date': compare_date,
            "location_filter": self._tsparql_wrapper.location_filter(),
            "miner_fs_busname": self._tsparql_wrapper.props.miner_fs_busname,
        }


class RecentlyAdded(SmartPlaylist):
    """Recently Added smart playlist"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.props.tag_text = "RECENTLY_ADDED"
        # TRANSLATORS: this is a playlist name
        self._title = _("Recently Added")
        self.props.icon_name = "list-add-symbolic"

        sparql_midnight_dateTime_format = "%Y-%m-%dT00:00:00Z"
        days_difference = 7
        seconds_difference = days_difference * 86400
        compare_date = time.strftime(
            sparql_midnight_dateTime_format,
            time.gmtime(time.time() - seconds_difference))
        self.props.query = """
        SELECT
            ?song AS ?id
            ?title
            ?url
            ?artist
            ?album
            ?duration
            ?trackNumber
            ?albumDiscNumber
            nie:usageCounter(?song) AS ?playCount
            ?tag AS ?favorite
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT
                        ?song
                        nie:title(?song) AS ?title
                        nie:isStoredAs(?song) AS ?url
                        nmm:artistName(nmm:artist(?song)) AS ?artist
                        nie:title(nmm:musicAlbum(?song)) AS ?album
                        nfo:duration(?song) AS ?duration
                        nmm:trackNumber(?song) AS ?trackNumber
                        nmm:setNumber(nmm:musicAlbumDisc(?song))
                            AS ?albumDiscNumber
                        ?added
                    WHERE {
                        ?song a nmm:MusicPiece ;
                              nrl:added ?added .
                        %(location_filter)s
                        FILTER ( ?added > '%(compare_date)s'^^xsd:dateTime )
                    }
                }
            }
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        } ORDER BY DESC(nrl:added(?song)) LIMIT 50
        """.replace('\n', ' ').strip() % {
            'compare_date': compare_date,
            "location_filter": self._tsparql_wrapper.location_filter(),
            "miner_fs_busname": self._tsparql_wrapper.props.miner_fs_busname,
        }


class Favorites(SmartPlaylist):
    """Favorites smart playlist"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.props.tag_text = "FAVORITES"
        # TRANSLATORS: this is a playlist name
        self._title = _("Starred Songs")
        self.props.icon_name = "starred-symbolic"
        self.props.query = """
            SELECT
                ?song AS ?id
                ?title
                ?url
                ?artist
                ?album
                ?duration
                ?trackNumber
                ?albumDiscNumber
                nie:usageCounter(?song) AS ?playCount
                nao:predefined-tag-favorite AS ?favorite
            WHERE {
                SERVICE <dbus:%(miner_fs_busname)s> {
                    GRAPH tracker:Audio {
                        SELECT
                            ?song
                            nie:title(?song) AS ?title
                            nie:isStoredAs(?song) AS ?url
                            nmm:artistName(nmm:artist(?song)) AS ?artist
                            nie:title(nmm:musicAlbum(?song)) AS ?album
                            nfo:duration(?song) AS ?duration
                            nmm:trackNumber(?song) AS ?trackNumber
                            nmm:setNumber(nmm:musicAlbumDisc(?song))
                                AS ?albumDiscNumber
                            nrl:added(?song) AS ?added
                        WHERE {
                            ?song a nmm:MusicPiece .
                            %(location_filter)s
                        }
                    }
                }
                ?song nao:hasTag nao:predefined-tag-favorite .
            } ORDER BY DESC(?added)
        """.replace('\n', ' ').strip() % {
            "location_filter": self._tsparql_wrapper.location_filter(),
            "miner_fs_busname": self._tsparql_wrapper.props.miner_fs_busname,
        }


class InsufficientTagged(SmartPlaylist):
    """Lacking tags to be displayed in the artist/album views"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.props.tag_text = "INSUFFICIENT_TAGGED"
        # TRANSLATORS: this is a playlist name indicating that the
        # files are not tagged enough to be displayed in the albums
        # or artists views.
        self._title = _("Insufficiently Tagged")
        self.props.icon_name = "question-round-symbolic"
        self.props.query = """
        SELECT
            ?song AS ?id
            ?title
            ?url
            ?artist
            ?album
            ?duration
            ?trackNumber
            ?albumDiscNumber
            nie:usageCounter(?song) AS ?playCount
            ?tag AS ?favorite
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT
                        ?song
                        nie:title(?song) AS ?title
                        nie:isStoredAs(?song) AS ?url
                        nmm:artistName(nmm:artist(?song)) AS ?artist
                        nie:title(nmm:musicAlbum(?song)) AS ?album
                        nfo:duration(?song) AS ?duration
                        nmm:trackNumber(?song) AS ?trackNumber
                        nmm:setNumber(nmm:musicAlbumDisc(?song))
                            AS ?albumDiscNumber
                    WHERE {
                        {
                            ?song a nmm:MusicPiece .
                            %(location_filter)s
                            FILTER NOT EXISTS {
                                ?song nmm:musicAlbum ?album
                            }
                        } UNION {
                            ?song a nmm:MusicPiece .
                            %(location_filter)s
                            FILTER NOT EXISTS {
                                ?song nmm:artist ?artist
                            }
                        }
                    }
                }
            }
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        }
        """.replace('\n', ' ').strip() % {
            "location_filter": self._tsparql_wrapper.location_filter(),
            "miner_fs_busname": self._tsparql_wrapper.props.miner_fs_busname,
        }


class AllSongs(SmartPlaylist):
    """All Songs smart playlist"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.props.tag_text = "ALL_SONGS"
        # TRANSLATORS: this is a playlist name
        self._title = _("All Songs")
        self.props.icon_name = "folder-music-symbolic"

        self.props.query = """
        SELECT
            ?song AS ?id
            ?title
            ?url
            ?artist
            ?album
            ?duration
            ?trackNumber
            ?albumDiscNumber
            nie:usageCounter(?song) AS ?playCount
            ?tag AS ?favorite
        WHERE {
            SERVICE <dbus:%(miner_fs_busname)s> {
                GRAPH tracker:Audio {
                    SELECT
                        ?song
                        nie:title(?song) AS ?title
                        nie:isStoredAs(?song) AS ?url
                        nmm:artistName(nmm:artist(?song)) AS ?artist
                        nie:title(nmm:musicAlbum(?song)) AS ?album
                        nfo:duration(?song) AS ?duration
                        nmm:trackNumber(?song) AS ?trackNumber
                        nmm:setNumber(nmm:musicAlbumDisc(?song))
                            AS ?albumDiscNumber
                    WHERE {
                        ?song a nmm:MusicPiece .
                        %(location_filter)s
                    }
                }
            }
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        } ORDER BY ?artist ?album ?trackNumber
        """.replace('\n', ' ').strip() % {
            "location_filter": self._tsparql_wrapper.location_filter(),
            "miner_fs_busname": self._tsparql_wrapper.props.miner_fs_busname,
        }
