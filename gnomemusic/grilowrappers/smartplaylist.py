# Copyright 2024 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations

import time

from gettext import gettext as _

import gi
gi.require_versions({"Grl": "0.3"})
from gi.repository import GObject, Gio, Grl

from gnomemusic.coresong import CoreSong
from gnomemusic.grilowrappers.playlist import Playlist


class SmartPlaylist(Playlist):
    """Base class for smart playlists"""

    __gtype_name__ = "SmartPlaylist"

    _METADATA_SMART_PLAYLIST_KEYS = [
        Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_ALBUM_DISC_NUMBER,
        Grl.METADATA_KEY_ARTIST,
        Grl.METADATA_KEY_DURATION,
        Grl.METADATA_KEY_FAVOURITE,
        Grl.METADATA_KEY_ID,
        Grl.METADATA_KEY_PLAY_COUNT,
        Grl.METADATA_KEY_URL,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_TRACK_NUMBER,
    ]

    def __init__(self, **args):
        super().__init__(**args)

        self.props.is_smart = True

    @GObject.Property(type=Gio.ListStore, default=None)
    def model(self):
        if self._model is None:
            self._model = Gio.ListStore.new(CoreSong)

            self._notificationmanager.push_loading()

            def _add_to_model(source, op_id, media, remaining, error):
                if error:
                    self._log.warning("Error: {}".format(error))
                    self._notificationmanager.pop_loading()
                    self.emit("playlist-loaded")
                    return

                if not media:
                    self.props.count = self._model.get_n_items()
                    self._notificationmanager.pop_loading()
                    self.emit("playlist-loaded")
                    return

                coresong = CoreSong(self._application, media)
                self._bind_to_main_song(coresong)
                self._model.append(coresong)

            self._source.query(
                self.props.query, self._METADATA_SMART_PLAYLIST_KEYS,
                self._fast_options, _add_to_model)

        return self._model

    def update(self):
        """Updates playlist model."""
        if self._model is None:
            return

        new_model_medias = []

        def _fill_new_model(source, op_id, media, remaining, error):
            if error:
                return

            if not media:
                self._finish_update(new_model_medias)
                return

            new_model_medias.append(media)

        self._source.query(
            self.props.query, self._METADATA_SMART_PLAYLIST_KEYS,
            self._fast_options, _fill_new_model)

    def _finish_update(self, new_model_medias):
        if not new_model_medias:
            self._model.remove_all()
            self.props.count = 0
            return

        current_models_ids = [coresong.props.media.get_id()
                              for coresong in self._model]
        new_model_ids = [media.get_id() for media in new_model_medias]

        idx_to_delete = []
        for idx, media_id in enumerate(current_models_ids):
            if media_id not in new_model_ids:
                idx_to_delete.insert(0, idx)

        for idx in idx_to_delete:
            self._model.remove(idx)
            self.props.count -= 1

        for idx, media in enumerate(new_model_medias):
            if media.get_id() not in current_models_ids:
                coresong = CoreSong(self._application, media)
                self._bind_to_main_song(coresong)
                self._model.append(coresong)
                self.props.count += 1


class MostPlayed(SmartPlaylist):
    """Most Played smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "MOST_PLAYED"
        # TRANSLATORS: this is a playlist name
        self._title = _("Most Played")
        self.props.icon_name = "audio-speakers-symbolic"
        self.props.query = """
        SELECT
            %(media_type)s AS ?type
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
            "media_type": int(Grl.MediaType.AUDIO),
            "location_filter": self._tracker_wrapper.location_filter(),
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
        }


class NeverPlayed(SmartPlaylist):
    """Never Played smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "NEVER_PLAYED"
        # TRANSLATORS: this is a playlist name
        self._title = _("Never Played")
        self.props.icon_name = "deaf-symbolic"
        self.props.query = """
        SELECT
            %(media_type)s AS ?type
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
            "media_type": int(Grl.MediaType.AUDIO),
            "location_filter": self._tracker_wrapper.location_filter(),
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
        }


class RecentlyPlayed(SmartPlaylist):
    """Recently Played smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

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
            %(media_type)s AS ?type
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
            "media_type": int(Grl.MediaType.AUDIO),
            'compare_date': compare_date,
            "location_filter": self._tracker_wrapper.location_filter(),
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
        }


class RecentlyAdded(SmartPlaylist):
    """Recently Added smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

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
            %(media_type)s AS ?type
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
            "media_type": int(Grl.MediaType.AUDIO),
            'compare_date': compare_date,
            "location_filter": self._tracker_wrapper.location_filter(),
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
        }


class Favorites(SmartPlaylist):
    """Favorites smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "FAVORITES"
        # TRANSLATORS: this is a playlist name
        self._title = _("Favorite Songs")
        self.props.icon_name = "starred-symbolic"
        self.props.query = """
            SELECT
                %(media_type)s AS ?type
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
            "media_type": int(Grl.MediaType.AUDIO),
            "location_filter": self._tracker_wrapper.location_filter(),
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
        }


class InsufficientTagged(SmartPlaylist):
    """Lacking tags to be displayed in the artist/album views"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "INSUFFICIENT_TAGGED"
        # TRANSLATORS: this is a playlist name indicating that the
        # files are not tagged enough to be displayed in the albums
        # or artists views.
        self._title = _("Insufficiently Tagged")
        self.props.icon_name = "question-round-symbolic"
        self.props.query = """
        SELECT
            %(media_type)s AS ?type
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
            "media_type": int(Grl.MediaType.AUDIO),
            "location_filter": self._tracker_wrapper.location_filter(),
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
        }


class AllSongs(SmartPlaylist):
    """All Songs smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "ALL_SONGS"
        # TRANSLATORS: this is a playlist name
        self._title = _("All Songs")
        self.props.icon_name = "folder-music-symbolic"

        self.props.query = """
        SELECT
            %(media_type)s AS ?type
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
            "media_type": int(Grl.MediaType.AUDIO),
            "location_filter": self._tracker_wrapper.location_filter(),
            "miner_fs_busname": self._tracker_wrapper.props.miner_fs_busname,
        }
