# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Vadim Rutkovsky <roignac@gmail.com>
# Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
# Copyright (c) 2013 Guillaume Quintard <guillaume.quintard@gmail.com>
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

from gi.repository import GLib, Tracker


class Query():
    MUSIC_DIR = Tracker.sparql_escape_string(GLib.filename_to_uri(
        GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC)
    ))
    DOWNLOAD_DIR = Tracker.sparql_escape_string(GLib.filename_to_uri(
        GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
    ))

    @staticmethod
    def all_albums():
        return Query.albums('?album a nmm:MusicAlbum .')

    @staticmethod
    def all_artists():
        return Query.artists('?album a nmm:MusicAlbum .')

    @staticmethod
    def all_songs():
        return Query.songs('?song a nmm:MusicPiece ; a nfo:FileDataObject .')

    @staticmethod
    def all_playlists():
        return Query.playlists('?playlist a nmm:Playlist .')

    @staticmethod
    def all_songs_count():
        query = '''
    SELECT
        COUNT(?song) AS childcount
    WHERE {
        ?song a nmm:MusicPiece ;
              a nfo:FileDataObject
        FILTER (
            tracker:uri-is-descendant(
                '%(music_dir)s', nie:url(?song)
            ) ||
            tracker:uri-is-descendant(
                '%(download_dir)s', nie:url(?song)
            )
        )
        FILTER (
            NOT EXISTS {
                ?song a nmm:Video
            } &&
            NOT EXISTS {
                ?song a nmm:Playlist
            }
        )
    }
    '''.replace('\n', ' ').strip() % {
            'music_dir': Query.MUSIC_DIR,
            'download_dir': Query.DOWNLOAD_DIR
        }

        return query

    @staticmethod
    def albums(where_clause):
        query = '''
    SELECT DISTINCT
        rdf:type(?album)
        tracker:id(?album) AS id
        (
            SELECT
                nmm:artistName(?artist)
            WHERE {
                ?album nmm:albumArtist ?artist
            }
            LIMIT 1
        ) AS artist
        nie:title(?album) AS title
        nie:title(?album) AS album
        tracker:coalesce(
            (
                SELECT
                    GROUP_CONCAT(
                        nmm:artistName(?artist),
                        ','
                    )
                WHERE {
                    ?album nmm:albumArtist ?artist
                }
            ),
            (
                SELECT
                    GROUP_CONCAT(
                        (
                            SELECT
                                nmm:artistName(nmm:performer(?_12)) AS perf
                            WHERE {
                                ?_12 nmm:musicAlbum ?album
                            }
                            GROUP BY ?perf
                        ),
                        ','
                    ) AS album_performer
                WHERE {
                }
            )
        ) AS author
        xsd:integer(
            tracker:coalesce(
                nmm:albumTrackCount(?album),
                (
                    SELECT
                        COUNT(?_1)
                    WHERE {
                        ?_1 nmm:musicAlbum ?album ;
                            tracker:available 'true'
                        FILTER (
                            tracker:uri-is-descendant(
                                '%(music_dir)s', nie:url(?_1)
                            ) ||
                            tracker:uri-is-descendant(
                                '%(download_dir)s', nie:url(?_1)
                            )
                        )
                        FILTER (
                            NOT EXISTS {
                                ?_1 a nmm:Video
                            } &&
                            NOT EXISTS {
                                ?_1 a nmm:Playlist
                            }
                        )
                    }
                )
            )
        ) AS childcount
        (
            SELECT
                fn:year-from-dateTime(?c)
            WHERE {
                ?_2 nmm:musicAlbum ?album ;
                    nie:contentCreated ?c ;
                    tracker:available 'true'
                FILTER (
                    tracker:uri-is-descendant(
                        '%(music_dir)s', nie:url(?_2)
                    ) ||
                    tracker:uri-is-descendant(
                        '%(download_dir)s', nie:url(?_2)
                    )
                )
                FILTER (
                    NOT EXISTS {
                        ?_2 a nmm:Video
                    } &&
                    NOT EXISTS {
                        ?_2 a nmm:Playlist
                    }
                )
            }
            LIMIT 1
        ) AS creation-date
        {
            %(where_clause)s
            FILTER (
                EXISTS {
                    ?_3 nmm:musicAlbum ?album ;
                        tracker:available 'true'
                    FILTER (
                        tracker:uri-is-descendant(
                            '%(music_dir)s', nie:url(?_3)
                        ) ||
                        tracker:uri-is-descendant(
                            '%(download_dir)s', nie:url(?_3)
                        )
                    )
                    FILTER (
                        NOT EXISTS {
                            ?_3 a nmm:Video
                        } &&
                        NOT EXISTS {
                            ?_3 a nmm:Playlist
                        }
                    )
                }
            )
        }
    ORDER BY fn:lower-case(?title) ?author ?albumyear
    '''.replace('\n', ' ').strip() % {
            'where_clause': where_clause.replace('\n', ' ').strip(),
            'music_dir': Query.MUSIC_DIR,
            'download_dir': Query.DOWNLOAD_DIR
        }

        return query

    @staticmethod
    def artists(where_clause):
        query = '''
    SELECT DISTINCT
        rdf:type(?album)
        tracker:id(?album) AS id
        (
            SELECT
                nmm:artistName(?artist)
            WHERE {
                ?album nmm:albumArtist ?artist
            }
            LIMIT 1
        ) AS artist
        nie:title(?album) AS title
        nie:title(?album) AS album
        tracker:coalesce(
            (
                SELECT
                    GROUP_CONCAT(
                        nmm:artistName(?artist),
                        ','
                    )
                WHERE {
                    ?album nmm:albumArtist ?artist
                }
            ),
            (
                SELECT
                    GROUP_CONCAT(
                        (
                            SELECT
                                nmm:artistName(nmm:performer(?_12)) AS perf
                            WHERE {
                                ?_12 nmm:musicAlbum ?album
                                FILTER (
                                    tracker:uri-is-descendant(
                                        '%(music_dir)s', nie:url(?_12)
                                    ) ||
                                    tracker:uri-is-descendant(
                                        '%(download_dir)s', nie:url(?_12)
                                    )
                                )
                                FILTER (
                                    NOT EXISTS {
                                        ?_12 a nmm:Video
                                    } &&
                                    NOT EXISTS {
                                        ?_12 a nmm:Playlist
                                    }
                                )
                            }
                            GROUP BY ?perf
                        ),
                        ','
                    ) AS album_performer
                WHERE {
                }
            )
        ) AS author
        xsd:integer(
            tracker:coalesce(
                nmm:albumTrackCount(?album),
                (
                    SELECT
                        COUNT(?_1)
                    WHERE {
                        ?_1 nmm:musicAlbum ?album ;
                        tracker:available 'true'
                        FILTER (
                            tracker:uri-is-descendant(
                                '%(music_dir)s', nie:url(?_1)
                            ) ||
                            tracker:uri-is-descendant(
                                '%(download_dir)s', nie:url(?_1)
                            )
                        )
                        FILTER (
                            NOT EXISTS {
                                ?_1 a nmm:Video
                            } &&
                            NOT EXISTS {
                                ?_1 a nmm:Playlist
                            }
                        )
                    }
                )
            )
        ) AS childcount
        (
            SELECT
                fn:year-from-dateTime(?c)
            WHERE {
                ?_2 nmm:musicAlbum ?album ;
                    nie:contentCreated ?c ;
                    tracker:available 'true'
                FILTER (
                    tracker:uri-is-descendant(
                        '%(music_dir)s', nie:url(?_2)
                    ) ||
                    tracker:uri-is-descendant(
                        '%(download_dir)s', nie:url(?_2)
                    )
                )
                FILTER (
                    NOT EXISTS {
                        ?_2 a nmm:Video
                    } &&
                    NOT EXISTS {
                        ?_2 a nmm:Playlist
                    }
                )
            }
            LIMIT 1
        ) AS creation-date
        {
            %(where_clause)s
            FILTER (
                EXISTS {
                    ?_3 nmm:musicAlbum ?album ;
                        tracker:available 'true'
                    FILTER (
                        tracker:uri-is-descendant(
                            '%(music_dir)s', nie:url(?_3)
                        ) ||
                        tracker:uri-is-descendant(
                            '%(download_dir)s', nie:url(?_3)
                        )
                    )
                    FILTER (
                        NOT EXISTS {
                            ?_3 a nmm:Video
                        } &&
                        NOT EXISTS {
                            ?_3 a nmm:Playlist
                        }
                    )
                }
            )
        }
    ORDER BY fn:lower-case(?author) ?albumyear nie:title(?album)
    '''.replace('\n', ' ').strip() % {
            'where_clause': where_clause.replace('\n', ' ').strip(),
            'music_dir': Query.MUSIC_DIR,
            'download_dir': Query.DOWNLOAD_DIR
        }

        return query

    @staticmethod
    def songs(where_clause):
        query = '''
    SELECT DISTINCT
        rdf:type(?song)
        tracker:id(?song) AS id
        nie:url(?song) AS url
        nie:title(?song) AS title
        nmm:artistName(nmm:performer(?song)) AS artist
        nie:title(nmm:musicAlbum(?song)) AS album
        nfo:duration(?song) AS duration
        {
            %(where_clause)s
            FILTER (
                tracker:uri-is-descendant(
                    '%(music_dir)s', nie:url(?song)
                ) ||
                tracker:uri-is-descendant(
                    '%(download_dir)s', nie:url(?song)
                )
            )
            FILTER (
                NOT EXISTS {
                    ?song a nmm:Video
                } &&
                NOT EXISTS {
                    ?song a nmm:Playlist
                }
            )
        }
    ORDER BY tracker:added(?song)
    '''.replace('\n', ' ').strip() % {
            'where_clause': where_clause.replace('\n', ' ').strip(),
            'music_dir': Query.MUSIC_DIR,
            'download_dir': Query.DOWNLOAD_DIR
        }

        return query

    @staticmethod
    def playlists(where_clause):
        query = '''
    SELECT DISTINCT
        rdf:type(?playlist)
        tracker:id(?playlist) AS id
        nie:title(?playlist) AS title
        nfo:entryCounter(?playlist) AS childcount
        {
            %(where_clause)s
            OPTIONAL {
                ?playlist a nfo:FileDataObject .
                FILTER (
                    EXISTS {
                        ?playlist tracker:available 'true'
                        FILTER (
                            tracker:uri-is-descendant(
                                '%(music_dir)s', nie:url(?playlist)
                            ) ||
                            tracker:uri-is-descendant(
                                '%(download_dir)s', nie:url(?playlist)
                            )
                        )
                    }
                )
            }
        }
    ORDER BY fn:lower-case(?title) ?author ?albumyear
    '''.replace('\n', ' ').strip() % {
            'where_clause': where_clause.replace('\n', ' ').strip(),
            'music_dir': Query.MUSIC_DIR,
            'download_dir': Query.DOWNLOAD_DIR
        }

        return query

    @staticmethod
    def album_songs(album_id):
        query = '''
    SELECT DISTINCT
        rdf:type(?song)
        tracker:id(?song) AS id
        nie:url(?song) AS url
        nie:title(?song) AS title
        nmm:artistName(nmm:performer(?song)) AS artist
        nie:title(nmm:musicAlbum(?song)) AS album
        nfo:duration(?song) AS duration
    WHERE {
        ?song a nmm:MusicPiece ;
              a nfo:FileDataObject ;
              nmm:musicAlbum ?album .
        FILTER (
            tracker:id(?album) = %(album_id)s
        )
        FILTER (
            tracker:uri-is-descendant(
                '%(music_dir)s', nie:url(?song)
            ) ||
            tracker:uri-is-descendant(
                '%(download_dir)s', nie:url(?song)
            )
        )
        FILTER (
            NOT EXISTS {
                ?song a nmm:Video
            } &&
            NOT EXISTS {
                ?song a nmm:Playlist
            }
        )
    }
    ORDER BY
         nmm:setNumber(nmm:musicAlbumDisc(?song))
         nmm:trackNumber(?song)
         tracker:added(?song)
    '''.replace('\n', ' ').strip() % {
            'album_id': album_id,
            'music_dir': Query.MUSIC_DIR,
            'download_dir': Query.DOWNLOAD_DIR
        }

        return query

    @staticmethod
    def playlist_songs(playlist_id, filter_clause=None):
        query = '''
    SELECT
        rdf:type(?song)
        tracker:id(?entry) AS id
        nie:url(?song) AS url
        nie:title(?song) AS title
        nmm:artistName(nmm:performer(?song)) AS artist
        nie:title(nmm:musicAlbum(?song)) AS album
        nfo:duration(?song) AS duration
    WHERE {
        ?playlist a nmm:Playlist ;
            a nfo:MediaList ;
            nfo:hasMediaFileListEntry ?entry .
        ?entry a nfo:MediaFileListEntry ;
            nfo:entryUrl ?url .
        ?song a nmm:MusicPiece ;
             a nfo:FileDataObject ;
             nie:url ?url .
        FILTER (
            %(filter_clause)s
        )
        FILTER (
            NOT EXISTS {
                ?song a nmm:Video
            } &&
            NOT EXISTS {
                ?song a nmm:Playlist
            }
        )
    }
    ORDER BY
         nfo:listPosition(?entry)
    '''.replace('\n', ' ').strip() % {
            'playlist_id': playlist_id,
            'filter_clause':
                filter_clause or 'tracker:id(?playlist) = ' + playlist_id,
            'music_dir': Query.MUSIC_DIR,
            'download_dir': Query.DOWNLOAD_DIR
        }

        return query

    @staticmethod
    def get_album_for_album_id(album_id):
        query = """
    SELECT DISTINCT
        rdf:type(?album)
        tracker:id(?album) AS id
        (
            SELECT
                nmm:artistName(?artist)
            WHERE {
                ?album nmm:albumArtist ?artist
            }
            LIMIT 1
        ) AS artist
        nie:title(?album) AS title
        nie:title(?album) AS album
    WHERE {
        ?album a nmm:MusicAlbum  .
        FILTER (
            tracker:id(?album) = %(album_id)s
        )
    }
    """.replace("\n", " ").strip() % {
            'album_id': album_id,
            'music_dir': Query.MUSIC_DIR,
            'download_dir': Query.DOWNLOAD_DIR
        }
        return query

    @staticmethod
    def get_album_for_song_id(song_id):
        query = """
    SELECT DISTINCT
        rdf:type(?album)
        tracker:id(?album) AS id
        (
            SELECT
                nmm:artistName(?artist)
            WHERE {
                ?album nmm:albumArtist ?artist
            }
            LIMIT 1
        ) AS artist
        nie:title(?album) AS title
        nie:title(?album) AS album
    WHERE {
        ?song a nmm:MusicPiece ;
              nmm:musicAlbum ?album .
        FILTER (
            tracker:id(?song) = %(song_id)s
        )
        FILTER (
            tracker:uri-is-descendant(
                '%(music_dir)s', nie:url(?song)
            ) ||
            tracker:uri-is-descendant(
                '%(download_dir)s', nie:url(?song)
            )
        )
        FILTER (
            NOT EXISTS {
                ?song a nmm:Video
            } &&
            NOT EXISTS {
                ?song a nmm:Playlist
            }
        )
    }
    """.replace("\n", " ").strip() % {
            'song_id': song_id,
            'music_dir': Query.MUSIC_DIR,
            'download_dir': Query.DOWNLOAD_DIR
        }
        return query

    @staticmethod
    def create_playlist(title):
        query = """
    INSERT {
        _:playlist
            a nmm:Playlist ;
            a nfo:MediaList ;
            nie:title "%(title)s" ;
            nfo:entryCounter 0 .
    }
    """.replace("\n", " ").strip() % {
            'title': title
        }
        return query

    @staticmethod
    def delete_playlist(playlist_id):
        query = """
    DELETE {
        ?playlist
            a rdfs:Resource .
        ?entry
            a rdfs:Resource .
    }
    WHERE {
        ?playlist
            a nmm:Playlist ;
            a nfo:MediaList .
        OPTIONAL {
            ?playlist
                nfo:hasMediaFileListEntry ?entry .
        }
        FILTER (
            tracker:id(?playlist) = %(playlist_id)s
        )
    }
    """.replace("\n", " ").strip() % {
            'playlist_id': playlist_id
        }
        return query

    @staticmethod
    def add_song_to_playlist(playlist_id, song_uri):
        query = """
    INSERT OR REPLACE {
        _:entry
            a nfo:MediaFileListEntry ;
            nfo:entryUrl "%(song_uri)s" ;
            nfo:listPosition ?position .
        ?playlist
            nfo:entryCounter ?position ;
            nfo:hasMediaFileListEntry _:entry .
    }
    WHERE {
        SELECT
            ?playlist
            (?counter + 1) AS position
        WHERE {
            ?playlist
                a nmm:Playlist ;
                a nfo:MediaList ;
                nfo:entryCounter ?counter .
            FILTER (
                tracker:id(?playlist) = %(playlist_id)s
            )
        }
    }
    """.replace("\n", " ").strip() % {
            'playlist_id': playlist_id,
            'song_uri': song_uri
        }
        return query

    @staticmethod
    def remove_song_from_playlist(playlist_id, song_id):
        query = """
    INSERT OR REPLACE {
        ?entry
            nfo:listPosition ?position .
    }
    WHERE {
        SELECT
            ?entry
            (?old_position - 1) AS position
        WHERE {
            ?entry
                a nfo:MediaFileListEntry ;
                nfo:listPosition ?old_position .
            ?playlist
                nfo:hasMediaFileListEntry ?entry .
            FILTER (?old_position > ?removed_position)
            {
                SELECT
                    ?playlist
                    ?removed_position
                WHERE {
                    ?playlist
                        a nmm:Playlist ;
                        a nfo:MediaList ;
                        nfo:hasMediaFileListEntry ?removed_entry .
                    ?removed_entry
                        nfo:listPosition ?removed_position .
                    FILTER (
                        tracker:id(?playlist) = %(playlist_id)s &&
                        tracker:id(?removed_entry) = %(song_id)s
                    )
                }
            }
        }
    }
    INSERT OR REPLACE {
        ?playlist
            nfo:entryCounter ?new_counter .
    }
    WHERE {
        SELECT
            ?playlist
            (?counter - 1) AS new_counter
        WHERE {
            ?playlist
                a nmm:Playlist ;
                a nfo:MediaList ;
                nfo:entryCounter ?counter .
            FILTER (
                tracker:id(?playlist) = %(playlist_id)s
            )
        }
    }
    DELETE {
        ?playlist
            nfo:hasMediaFileListEntry ?entry .
        ?entry
            a rdfs:Resource .
    }
    WHERE {
        ?playlist
            a nmm:Playlist ;
            a nfo:MediaList ;
            nfo:hasMediaFileListEntry ?entry .
        FILTER (
            tracker:id(?playlist) = %(playlist_id)s &&
            tracker:id(?entry) = %(song_id)s
        )
    }
    """.replace("\n", " ").strip() % {
            'playlist_id': playlist_id,
            'song_id': song_id
        }
        return query

    @staticmethod
    def get_playlist_with_id(playlist_id):
        query = """
    ?playlist a nmm:Playlist .
    FILTER (
        tracker:id(?playlist) = %(playlist_id)s
    )
    """.replace('\n', ' ').strip() % {'playlist_id': playlist_id}

        return Query.playlists(query)

    @staticmethod
    def get_playlist_with_urn(playlist_urn):
        query = """
    SELECT DISTINCT
        tracker:id(<%(playlist_urn)s>) AS id
    WHERE {
        <%(playlist_urn)s> a nmm:Playlist
    }
    """.replace('\n', ' ').strip() % {'playlist_urn': playlist_urn}
        return query

    @staticmethod
    def get_playlist_song_with_id(playlist_id, entry_id):
        return Query.playlist_songs(
            playlist_id, 'tracker:id(?entry) = ' + str(entry_id)
        )

    @staticmethod
    def get_playlist_song_with_urn(entry_urn):
        query = """
    SELECT DISTINCT
        tracker:id(<%(entry_urn)s>) AS id
    WHERE {
        <%(entry_urn)s> a nfo:MediaFileListEntry
    }
    """.replace('\n', ' ').strip() % {'entry_urn': entry_urn}
        return query

    # Functions for search
    # TODO: make those queries actually return something
    @staticmethod
    def get_albums_with_any_match(name):
        name = Tracker.sparql_escape_string(GLib.utf8_casefold(name, -1))
        query = '''
            {
                SELECT DISTINCT
                    nmm:musicAlbum(?song) AS album
                WHERE {
                    ?song a nmm:MusicPiece .
                    FILTER (
                        fn:contains(tracker:case-fold(nie:title(nmm:musicAlbum(?song))), "%(name)s") ||
                        fn:contains(tracker:case-fold(nmm:artistName(nmm:performer(?song))), "%(name)s") ||
                        fn:contains(tracker:case-fold(nie:title(?song)), "%(name)s")
                    )
                }
            }
            '''.replace('\n', ' ').strip() % {'name': name}

        return Query.albums(query)

    @staticmethod
    def get_albums_with_artist_match(name):
        name = Tracker.sparql_escape_string(GLib.utf8_casefold(name, -1))
        query = '''
            {
                SELECT DISTINCT
                    ?album
                WHERE {
                    ?album a nmm:MusicAlbum ;
                        nmm:albumArtist ?artist .
                    FILTER (
                        fn:contains(tracker:case-fold(nmm:artistName(?artist)), "%(name)s")
                    )
                }
            }
            '''.replace('\n', ' ').strip() % {'name': name}

        return Query.albums(query)

    @staticmethod
    def get_albums_with_album_match(name):
        name = Tracker.sparql_escape_string(GLib.utf8_casefold(name, -1))
        query = '''
            {
                SELECT DISTINCT
                    ?album
                WHERE {
                    ?album a nmm:MusicAlbum .
                    FILTER (
                        fn:contains(tracker:case-fold(nie:title(?album)), "%(name)s")
                    )
                }
            }
            '''.replace('\n', ' ').strip() % {'name': name}

        return Query.albums(query)

    @staticmethod
    def get_albums_with_track_match(name):
        name = Tracker.sparql_escape_string(GLib.utf8_casefold(name, -1))
        query = '''
            {
                SELECT DISTINCT
                    nmm:musicAlbum(?song) AS album
                WHERE {
                    ?song a nmm:MusicPiece .
                    FILTER (
                        fn:contains(tracker:case-fold(nie:title(?song)), "%(name)s")
                    )
                }
            }
            '''.replace('\n', ' ').strip() % {'name': name}

        return Query.albums(query)

    @staticmethod
    def get_artists_with_any_match(name):
        name = Tracker.sparql_escape_string(GLib.utf8_casefold(name, -1))
        query = '''
            {
                SELECT DISTINCT
                    nmm:musicAlbum(?song) AS album
                WHERE {
                    ?song a nmm:MusicPiece .
                    FILTER (
                        fn:contains(tracker:case-fold(nie:title(nmm:musicAlbum(?song))), "%(name)s") ||
                        fn:contains(tracker:case-fold(nmm:artistName(nmm:performer(?song))), "%(name)s") ||
                        fn:contains(tracker:case-fold(nie:title(?song)), "%(name)s")
                    )
                }
            }
            '''.replace('\n', ' ').strip() % {'name': name}

        return Query.artists(query)

    @staticmethod
    def get_artists_with_artist_match(name):
        name = Tracker.sparql_escape_string(GLib.utf8_casefold(name, -1))
        query = '''
            {
                SELECT DISTINCT
                    ?album
                WHERE {
                    ?album a nmm:MusicAlbum ;
                        nmm:albumArtist ?artist .
                    FILTER (
                        fn:contains(tracker:case-fold(nmm:artistName(?artist)), "%(name)s")
                    )
                }
            }
            '''.replace('\n', ' ').strip() % {'name': name}

        return Query.artists(query)

    @staticmethod
    def get_artists_with_album_match(name):
        name = Tracker.sparql_escape_string(GLib.utf8_casefold(name, -1))
        query = '''
            {
                SELECT DISTINCT
                    ?album
                WHERE {
                    ?album a nmm:MusicAlbum .
                    FILTER (
                        fn:contains(tracker:case-fold(nie:title(?album)), "%(name)s")
                    )
                }
            }
            '''.replace('\n', ' ').strip() % {'name': name}

        return Query.artists(query)

    @staticmethod
    def get_artists_with_track_match(name):
        name = Tracker.sparql_escape_string(GLib.utf8_casefold(name, -1))
        query = '''
            {
                SELECT DISTINCT
                    nmm:musicAlbum(?song) AS album
                WHERE {
                    ?song a nmm:MusicPiece .
                    FILTER (
                        fn:contains(tracker:case-fold(nie:title(?song)), "%(name)s")
                    )
                }
            }
            '''.replace('\n', ' ').strip() % {'name': name}

        return Query.artists(query)

    @staticmethod
    def get_songs_with_any_match(name):
        name = Tracker.sparql_escape_string(GLib.utf8_casefold(name, -1))
        query = '''
            {
                SELECT DISTINCT
                    ?song
                WHERE {
                    ?song a nmm:MusicPiece .
                    FILTER (
                        fn:contains(tracker:case-fold(nie:title(?song)), "%(name)s") ||
                        fn:contains(tracker:case-fold(nmm:artistName(nmm:performer(?song))), "%(name)s") ||
                        fn:contains(tracker:case-fold(nie:title(nmm:musicAlbum(?song))), "%(name)s")
                    )
                }
            }
            '''.replace('\n', ' ').strip() % {'name': name}

        return Query.songs(query)

    @staticmethod
    def get_songs_with_artist_match(name):
        name = Tracker.sparql_escape_string(GLib.utf8_casefold(name, -1))
        query = '''
            {
                SELECT DISTINCT
                    ?song
                WHERE {
                    ?song a nmm:MusicPiece .
                    FILTER (
                        fn:contains(tracker:case-fold(nmm:artistName(nmm:performer(?song))), "%(name)s")
                    )
                }
            }
            '''.replace('\n', ' ').strip() % {'name': name}

        return Query.songs(query)

    @staticmethod
    def get_songs_with_album_match(name):
        name = Tracker.sparql_escape_string(GLib.utf8_casefold(name, -1))
        query = '''
            {
                SELECT DISTINCT
                    ?song
                WHERE {
                    ?song a nmm:MusicPiece .
                    FILTER (
                        fn:contains(tracker:case-fold(nie:title(nmm:musicAlbum(?song))), "%(name)s")
                    )
                }
            }
            '''.replace('\n', ' ').strip() % {'name': name}

        return Query.songs(query)

    @staticmethod
    def get_songs_with_track_match(name):
        name = Tracker.sparql_escape_string(GLib.utf8_casefold(name, -1))
        query = '''
            {
                SELECT DISTINCT
                    ?song
                WHERE {
                    ?song a nmm:MusicPiece .
                    FILTER (
                        fn:contains(tracker:case-fold(nie:title(?song)), "%(name)s")
                    )
                }
            }
            '''.replace('\n', ' ').strip() % {'name': name}

        return Query.songs(query)
