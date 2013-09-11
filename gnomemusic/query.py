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
            }
            LIMIT 1
        ) AS creation-date
        {
            ?album a nmm:MusicAlbum .
            FILTER (
                EXISTS {
                    ?_3 nmm:musicAlbum ?album ;
                        tracker:available 'true'
                }
            )
        }
    ORDER BY fn:lower-case(?title) ?author ?albumyear
    '''.replace('\n', ' ').strip()

    ALBUMS_COUNT = '''
    SELECT
        COUNT(?album) AS childcount
    WHERE {
        ?album a nmm:MusicAlbum
    }
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
            }
            LIMIT 1
        ) AS creation-date
        {
            ?album a nmm:MusicAlbum .
            FILTER (
                EXISTS {
                    ?_3 nmm:musicAlbum ?album ;
                        tracker:available 'true'
                }
            )
        }
    ORDER BY fn:lower-case(?author) ?albumyear nie:title(?album)
    '''.replace('\n', ' ').strip()

    ARTISTS_COUNT = '''
    SELECT
        COUNT(DISTINCT ?artist)
    WHERE {
        ?artist a nmm:Artist .
        ?album nmm:performer ?artist
    }
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
        }
    ORDER BY tracker:added(?song)
    '''.replace('\n', ' ').strip()

    SONGS_COUNT = '''
    SELECT
        COUNT(?song) AS childcount
    WHERE {
        ?song a nmm:MusicPiece ;
              a nfo:FileDataObject
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
    }
    ORDER BY
         nmm:setNumber(nmm:musicAlbumDisc(?song))
         nmm:trackNumber(?song)
         tracker:added(?song)
    '''.replace('\n', ' ').strip() % {'album_id': album_id}

        return query

    @staticmethod
    def get_album_for_id(album_id):
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
