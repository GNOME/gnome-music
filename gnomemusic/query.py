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

from gi.repository import Tracker
from gi.repository import GLib


class Query():

    MUSIC_DIR = Tracker.sparql_escape_string(GLib.filename_to_uri(
        GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC)
    ))

    DOWNLOAD_DIR = Tracker.sparql_escape_string(GLib.filename_to_uri(
        GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
    ))

    @staticmethod
    def get_all_albums():
        return '''
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
                                } && (
                                tracker:uri-is-descendant(
                                    '%(music_dir)s', nie:url(?_1)
                                ) ||
                                tracker:uri-is-descendant(
                                    '%(download_dir)s', nie:url(?_1)
                                ))
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
                        } && (
                        tracker:uri-is-descendant(
                            '%(music_dir)s', nie:url(?song)
                        ) ||
                        tracker:uri-is-descendant(
                            '%(download_dir)s', nie:url(?song)
                        ))
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
                            } && (
                            tracker:uri-is-descendant(
                                '%(music_dir)s', nie:url(?_3)
                            ) ||
                            tracker:uri-is-descendant(
                                '%(download_dir)s', nie:url(?_3)
                            ))
                        )
                    }
                )
            }
        ORDER BY fn:lower-case(?title) ?author ?albumyear
        '''.replace('\n', ' ').strip() % {'music_dir': Query.MUSIC_DIR,
                                          'download_dir': Query.DOWNLOAD_DIR}

    @staticmethod
    def get_albums_count():
        return '''
        SELECT
            COUNT(?album) AS childcount
        WHERE {
            ?album a nmm:MusicAlbum
        }
        '''.replace('\n', ' ').strip()

    @staticmethod
    def get_artists():
        return '''
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
                                        } && (
                                        tracker:uri-is-descendant(
                                            '%(music_dir)s', nie:url(?_12)
                                        ) ||
                                        tracker:uri-is-descendant(
                                            '%(download_dir)s', nie:url(?_12)
                                        ))
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
                                } && (
                                tracker:uri-is-descendant(
                                    '%(music_dir)s', nie:url(?_1)
                                ) ||
                                tracker:uri-is-descendant(
                                    '%(download_dir)s', nie:url(?_1)
                                ))
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
                        } && (
                        tracker:uri-is-descendant(
                            '%(music_dir)s', nie:url(?_2)
                        ) ||
                        tracker:uri-is-descendant(
                            '%(download_dir)s', nie:url(?_2)
                        ))
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
                        } && (
                        tracker:uri-is-descendant(
                            '%(music_dir)s', nie:url(?_3)
                        ) ||
                        tracker:uri-is-descendant(
                            '%(download_dir)s', nie:url(?_3)
                        ))
                    )
                    }
                )
            }
        ORDER BY fn:lower-case(?author) ?albumyear nie:title(?album)
        '''.replace('\n', ' ').strip() % {'music_dir': Query.MUSIC_DIR,
                                          'download_dir': Query.DOWNLOAD_DIR}

    ARTISTS_COUNT = '''
    SELECT
        COUNT(DISTINCT ?artist)
    WHERE {
        ?artist a nmm:Artist .
        ?album nmm:performer ?artist
    }
    '''.replace('\n', ' ').strip()

    @staticmethod
    def get_songs():
        return '''
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
                    } && (
                    tracker:uri-is-descendant(
                        '%(music_dir)s', nie:url(?song)
                    ) ||
                    tracker:uri-is-descendant(
                        '%(download_dir)s', nie:url(?song)
                    ))
                )
            }
        ORDER BY tracker:added(?song)
        '''.replace('\n', ' ').strip() % {'music_dir': Query.MUSIC_DIR,
                                          'download_dir': Query.DOWNLOAD_DIR}

    @staticmethod
    def get_songs_count():
        return '''
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
                } && (
                tracker:uri-is-descendant(
                    '%(music_dir)s', nie:url(?song)
                ) ||
                tracker:uri-is-descendant(
                    '%(download_dir)s', nie:url(?song)
                ))
            )
        }
        '''.replace('\n', ' ').strip() % {'music_dir': Query.MUSIC_DIR,
                                          'download_dir': Query.DOWNLOAD_DIR}

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
            } && (
            tracker:uri-is-descendant(
                '%(music_dir)s', nie:url(?song)
            ) ||
            tracker:uri-is-descendant(
                '%(download_dir)s', nie:url(?song)
            ))
        )
    }
    ORDER BY
         nmm:setNumber(nmm:musicAlbumDisc(?song))
         nmm:trackNumber(?song)
         tracker:added(?song)
    '''.replace('\n', ' ').strip() % {'album_id': album_id,
                                      'music_dir': Query.MUSIC_DIR,
                                      'download_dir': Query.DOWNLOAD_DIR}

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
            } && (
            tracker:uri-is-descendant(
                '%(music_dir)s', nie:url(?song)
            ) ||
            tracker:uri-is-descendant(
                '%(download_dir)s', nie:url(?song)
            ))
        )
    }
    '''.replace('\n', ' ').strip() % {'url': url,
                                      'music_dir': Query.MUSIC_DIR,
                                      'download_dir': Query.DOWNLOAD_DIR}

        return query
