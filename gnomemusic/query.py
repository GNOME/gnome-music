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


class Query():

    ALBUMS = '''
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
                    NOT EXISTS {
                        ?song a nmm:Video
                    } &&
                    NOT EXISTS {
                        ?song a nmm:Playlist
                    }
                )
            }
            LIMIT 1
        ) AS creation-date
        {
            ?album a nmm:MusicAlbum .
            FILTER (
                EXISTS {
                    ?_3 nmm:musicAlbum ?album ;
                        tracker:available 'true'
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
    '''.replace('\n', ' ').strip()

    ARTISTS = '''
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
            ?album a nmm:MusicAlbum .
            FILTER (
                EXISTS {
                    ?_3 nmm:musicAlbum ?album ;
                        tracker:available 'true'
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
    '''.replace('\n', ' ').strip()

    SONGS = '''
    SELECT DISTINCT
        rdf:type(?song)
        tracker:id(?song) AS id
        nie:url(?song) AS url
        nie:title(?song) AS title
        nmm:artistName(nmm:performer(?song)) AS artist
        nie:title(nmm:musicAlbum(?song)) AS album
        nfo:duration(?song) AS duration
        {
            ?song a nmm:MusicPiece ;
                  a nfo:FileDataObject
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
    '''.replace('\n', ' ').strip()

    SONGS_COUNT = '''
    SELECT
        COUNT(?song) AS childcount
    WHERE {
        ?song a nmm:MusicPiece ;
              a nfo:FileDataObject
        FILTER (
            NOT EXISTS {
                ?song a nmm:Video
            } &&
            NOT EXISTS {
                ?song a nmm:Playlist
            }
        )
    }
    '''.replace('\n', ' ').strip()

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
    '''.replace('\n', ' ').strip() % {'album_id': album_id}

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
    """.replace("\n", " ").strip() % {'album_id': album_id}
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
            NOT EXISTS {
                ?song a nmm:Video
            } &&
            NOT EXISTS {
                ?song a nmm:Playlist
            }
        )
    }
    """.replace("\n", " ").strip() % {'song_id': song_id}
        return query

    @staticmethod
    def get_song_with_url(url):
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
        ?song a nmm:MusicPiece .
        FILTER (
            nie:url(?song) = "%(url)s"
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
    '''.replace('\n', ' ').strip() % {'url': url}
        return query


    #Functions for search
    # TODO: make those queries actualyl return something
    @staticmethod
    def get_albums_with_any_match(name):
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
                ?song a nmm:MusicPiece .
                FILTER (
                    nie:url(?song) = "%(url)s"
                )
            }
            '''.replace('\n', ' ').strip() % {'url': name}

        return query

    @staticmethod
    def get_albums_with_artist_match(name):
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
                ?song a nmm:MusicPiece .
                FILTER (
                    nie:url(?song) = "%(url)s"
                )
            }
            '''.replace('\n', ' ').strip() % {'url': name}

        return query

    @staticmethod
    def get_albums_with_album_match(name):
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
                ?song a nmm:MusicPiece .
                FILTER (
                    nie:url(?song) = "%(url)s"
                )
            }
            '''.replace('\n', ' ').strip() % {'url': name}

        return query

    @staticmethod
    def get_albums_with_track_match(name):
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
                ?song a nmm:MusicPiece .
                FILTER (
                    nie:url(?song) = "%(url)s"
                )
            }
            '''.replace('\n', ' ').strip() % {'url': name}

        return query

    @staticmethod
    def get_artists_with_any_match(name):
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
                ?song a nmm:MusicPiece .
                FILTER (
                    nie:url(?song) = "%(url)s"
                )
            }
            '''.replace('\n', ' ').strip() % {'url': name}

        return query

    @staticmethod
    def get_artists_with_artist_match(name):
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
                ?song a nmm:MusicPiece .
                FILTER (
                    nie:url(?song) = "%(url)s"
                )
            }
            '''.replace('\n', ' ').strip() % {'url': name}

        return query

    @staticmethod
    def get_artists_with_album_match(name):
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
                ?song a nmm:MusicPiece .
                FILTER (
                    nie:url(?song) = "%(url)s"
                )
            }
            '''.replace('\n', ' ').strip() % {'url': name}

        return query

    @staticmethod
    def get_artists_with_track_match(name):
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
                ?song a nmm:MusicPiece .
                FILTER (
                    nie:url(?song) = "%(url)s"
                )
            }
            '''.replace('\n', ' ').strip() % {'url': name}

        return query

    @staticmethod
    def get_songs_with_any_match(name):
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
                ?song a nmm:MusicPiece .
                FILTER (
                    nie:url(?song) = "%(url)s"
                )
            }
            '''.replace('\n', ' ').strip() % {'url': name}

        return query

    @staticmethod
    def get_songs_with_artist_match(name):
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
                ?song a nmm:MusicPiece .
                FILTER (
                    nie:url(?song) = "%(url)s"
                )
            }
            '''.replace('\n', ' ').strip() % {'url': name}

        return query

    @staticmethod
    def get_songs_with_album_match(name):
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
                ?song a nmm:MusicPiece .
                FILTER (
                    fn:contains(fn:lower-case(nie:title(nmm:musicAlbum(?song))), '%(name)s')
                )
            }
            '''.replace('\n', ' ').strip() % {'name': name.lower()}

        return query

    @staticmethod
    def get_songs_with_track_match(name):
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
                ?song a nmm:MusicPiece .
                FILTER (
                    nie:url(?song) = "%(url)s"
                )
            }
            '''.replace('\n', ' ').strip() % {'url': name}

        return query
