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

from gettext import gettext as _
from gi.repository import GLib, Tracker
from gnomemusic import log
import os
import logging
logger = logging.getLogger(__name__)

import time
sparql_midnight_dateTime_format = "%Y-%m-%dT00:00:00Z"

SECONDS_PER_DAY = 86400
PUNCTUATION_FILTER = " !\\\"#$%&'()*+,-./:;<=>?@[\\\\]^_`{|}~"

class Query():

    music_folder = None
    MUSIC_URI = None

    @log
    def __init__(self):
        try:
            Query.music_folder = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_MUSIC)
            assert Query.music_folder is not None
        except (TypeError, AssertionError):
            logger.warn("XDG Music dir is not set")
            return

        Query.MUSIC_URI = Tracker.sparql_escape_string(GLib.filename_to_uri(Query.music_folder))

        for folder in [Query.music_folder]:
            if os.path.islink(folder):
                logger.warn("%s is a symlink, this folder will be omitted", folder)
            else:
                i = len(next(os.walk(folder)))
                logger.debug("Found %d files in %s", i, folder)

    def __repr__(self):
        return '<Query>'

    @staticmethod
    def _order_by_statement(attr):
        """Returns a specifically sorted SPARQL ORDER BY statement.

        Returns a SPARQL ORDER BY statement sorting by the given
        attribute, ignoring articles as defined in _("the") as well as
        the punctuation at the start and the end of the string.

        :param str attr: The attribute to order by
        :return: The sparql order by statement
        :rtype: str
        """
        return_statement = """fn:replace(fn:lower-case(%(attribute)s),
        "^[%(punctuation)s]+|[%(punctuation)s]+$", "")
        """.replace('\n', ' ').strip() % {
            'attribute': attr,
            'punctuation': PUNCTUATION_FILTER
        }

        # TRANSLATORS: The following translatable string should be a
        # vertical bar-separated list of all-lowercase articles that
        # should be ignored when alphabetizing artists/albums. This
        # list should include the basic english translatable strings
        # regardless of language because they are so universal.
        # If some articles occur more frequently than others, the most
        # common one should appear first, the least common one last.
        for article in reversed(_("the|a|an").split("|")):
            return_statement = """IF(STRSTARTS(%(attribute)s, "%(article)s"),
            SUBSTR(%(attribute)s, %(substr_start)s), %(nested_if)s)
            """ % {
                'attribute': attr,
                'article': article + " ",
                'substr_start': str(len(article) + 2),
                'nested_if': return_statement
            }
        return return_statement

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
        query = """
    SELECT
        COUNT(?song) AS ?childcount
    {
        ?song a nmm:MusicPiece ;
              a nfo:FileDataObject ;
	      nie:url ?url .
        FILTER(STRSTARTS(?url, '%(music_dir)s/'))
    }
    """.replace('\n', ' ').strip() % {
            'music_dir': Query.MUSIC_URI
        }

        return query

    @staticmethod
    def albums(where_clause):
        query = """
    SELECT
        rdf:type(?album)
        tracker:id(?album) AS ?id
        nmm:artistName(?albumArtist) AS ?album_artist
        nmm:artistName(?composer) AS ?composer
        nmm:artistName(?performer) AS ?artist
        ?title
        COUNT(?song) AS ?childcount
        YEAR(MAX(nie:contentCreated(?song))) AS ?creation_date
    {
        %(where_clause)s
        ?song a nmm:MusicPiece ;
            nmm:musicAlbum ?album ;
            nmm:performer ?performer .
        ?album nie:title ?title .
        OPTIONAL { ?album nmm:albumArtist ?albumArtist . }
        OPTIONAL { ?song nmm:composer ?composer . }
        BIND(tracker:coalesce(nmm:artistName(?albumArtist),
                              nmm:artistName(?performer)) AS ?artist_presort)
        BIND(LCASE(?title) AS ?title_lower)
        BIND((%(album_order)s) AS ?album_collation)
        FILTER(STRSTARTS(nie:url(?song), '%(music_dir)s/'))
    }
    GROUP BY ?album
    ORDER BY ?album_collation (%(artist_sort)s) ?creation_date
    """.replace('\n', ' ').strip() % {
            'where_clause': where_clause.replace('\n', ' ').strip(),
            'music_dir': Query.MUSIC_URI,
            'album_order': Query._order_by_statement("?title_lower"),
            'artist_sort': Query._order_by_statement("?artist_presort"),
        }

        return query

    @staticmethod
    def artists(where_clause):
        query = """
    SELECT
        rdf:type(?album)
        tracker:id(?album) AS ?id
        nmm:artistName(?performer) AS ?artist
        nmm:artistName(?albumArtist) AS ?album_artist
        ?title
        COUNT(?song) AS ?childcount
        YEAR(MAX(nie:contentCreated(?song))) AS ?creation_date
    {
        %(where_clause)s
        ?album a nmm:MusicAlbum ;
               nie:title ?title .
        ?song nmm:musicAlbum ?album ;
              nmm:performer ?performer .
        OPTIONAL { ?album nmm:albumArtist ?albumArtist }
        BIND(tracker:coalesce(nmm:artistName(?albumArtist),
                              nmm:artistName(?performer)) AS ?artist_presort)
        BIND(LCASE(?title) AS ?title_lower)
        BIND((%(album_order)s) AS ?title_collation)
        FILTER(STRSTARTS(nie:url(?song), '%(music_dir)s/'))
    }
    GROUP BY ?album
    ORDER BY (%(artist_sort)s) ?creation_date ?album_collation
    """.replace('\n', ' ').strip() % {
            'where_clause': where_clause.replace('\n', ' ').strip(),
            'music_dir': Query.MUSIC_URI,
            'artist_sort': Query._order_by_statement("?artist_presort"),
            'album_order': Query._order_by_statement("?title_lower")
        }

        return query

    @staticmethod
    def songs(where_clause):
        query = """
    SELECT DISTINCT
        rdf:type(?song)
        tracker:id (?song) AS ?id
        ?url
        nie:title(?song) AS ?title
        nmm:artistName(nmm:performer(?song)) AS ?artist
        nie:title(nmm:musicAlbum(?song)) AS ?album
        nfo:duration(?song) AS ?duration
        IF (BOUND(?tag), 'b', '') AS ?lyrics
    {
        %(where_clause)s
        ?song a nmm:MusicPiece ;
            nmm:musicAlbumDisc ?disc ;
            nmm:musicAlbum ?album ;
            nmm:performer ?performer ;
            nie:url ?url .
        OPTIONAL { ?song nao:hasTag ?tag .
                   FILTER (?tag = nao:predefined-tag-favorite) } .
        FILTER(STRSTARTS(?url, '%(music_dir)s/'))
    }
    ORDER BY ?artist ?album nmm:setNumber(?disc) nmm:trackNumber(?song)
    """.replace('\n', ' ').strip() % {
            'where_clause': where_clause.replace('\n', ' ').strip(),
            'music_dir': Query.MUSIC_URI
        }

        return query

    @staticmethod
    def playlists(where_clause):
        query = """
    SELECT DISTINCT
        rdf:type(?playlist)
        tracker:id(?playlist) AS ?id
        nie:title(?playlist) AS ?title
        nfo:entryCounter(?playlist) AS ?childcount
        {
            %(where_clause)s
            OPTIONAL { ?playlist nie:url ?url;
                       tracker:available ?available . }
            FILTER ( (STRSTARTS(?url, '%(music_dir)s/') && ?available)
                      || !BOUND(nfo:belongsToContainer(?playlist)) )
            OPTIONAL { ?playlist nao:hasTag ?tag }
        }
    ORDER BY !BOUND(?tag) LCASE(?title)
    """.replace('\n', ' ').strip() % {
            'where_clause': where_clause.replace('\n', ' ').strip(),
            'music_dir': Query.MUSIC_URI
        }

        return query

    @staticmethod
    def album_songs(album_id):
        query = """
    SELECT DISTINCT
        rdf:type(?song)
        tracker:id(?song) AS ?id
        nie:url(?song) AS ?url
        nie:title(?song) AS ?title
        nmm:artistName(nmm:performer(?song)) AS ?artist
        nie:title(nmm:musicAlbum(?song)) AS ?album
        nfo:duration(?song) AS ?duration
        nmm:trackNumber(?song) AS ?track_number
        nmm:setNumber(nmm:musicAlbumDisc(?song)) AS ?album_disc_number
        IF(bound(?tag), 'truth!', '') AS ?lyrics
    WHERE {
        ?song a nmm:MusicPiece ;
              a nfo:FileDataObject ;
              nmm:musicAlbum ?album .
        OPTIONAL { ?song nao:hasTag ?tag .
                   FILTER( ?tag = nao:predefined-tag-favorite ) } .
        FILTER (tracker:id(?album) = %(album_id)s &&
                (STRSTARTS(nie:url(?song), '%(music_dir)s/')))
    }
    ORDER BY
         ?album_disc_number
         ?track_number
         tracker:added(?song)
    """.replace('\n', ' ').strip() % {
            'album_id': album_id,
            'music_dir': Query.MUSIC_URI
        }

        return query

    @staticmethod
    def playlist_songs(playlist_id, filter_clause=None):
        query = """
    SELECT
        rdf:type(?song)
        tracker:id(?entry) AS ?id
        nie:url(?song) AS ?url
        nie:title(?song) AS ?title
        nmm:artistName(nmm:performer(?song)) AS ?artist
        nie:title(nmm:musicAlbum(?song)) AS ?album
        nfo:duration(?song) AS ?duration
        IF(bound(?tag), 'truth!', '') AS ?lyrics
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
    """.replace('\n', ' ').strip() % {
            'playlist_id': playlist_id,
            'filter_clause': filter_clause or 'tracker:id(?playlist) = ' + playlist_id,
            'music_dir': Query.MUSIC_URI
        }

        return query

    @staticmethod
    def get_album_for_album_id(album_id):
        # Even though we check for the album_artist, we fill
        # the artist key, since Grilo coverart plugins use
        # only that key for retrieval.
        query = """
    SELECT DISTINCT
        rdf:type(?album)
        tracker:id(?album) AS ?id
        nmm:artistName(?album_artist) AS ?artist
        nie:title(?album) AS ?album
    WHERE {
        ?album a nmm:MusicAlbum .
        ?song a nmm:MusicPiece ;
            nmm:musicAlbum ?album ;
            nmm:performer ?song_artist .
        OPTIONAL { ?album nmm:albumArtist ?album_artist . }
        FILTER (
            tracker:id(?album) = %(album_id)s
        )
    }
    """.replace("\n", " ").strip() % {
            'album_id': album_id,
            'music_dir': Query.MUSIC_URI
        }
        return query

    @staticmethod
    def get_album_for_song_id(song_id):
        # See get_album_for_album_id comment.
        query = """
    SELECT DISTINCT
        rdf:type(?album)
        tracker:id(?album) AS ?id
        nmm:artistName(?album_artist) AS ?artist
        nie:title(?album) AS ?album
    WHERE {
        ?song a nmm:MusicPiece ;
              nmm:musicAlbum ?album ;
              nmm:performer ?song_artist .
        OPTIONAL { ?album nmm:albumArtist ?album_artist . }
        FILTER (
            tracker:id(?song) = %(song_id)s
        )
        FILTER (
            STRSTARTS(nie:url(?song), '%(music_dir)s')
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
            'music_dir': Query.MUSIC_URI
        }
        return query

    @staticmethod
    def update_playcount(song_url):
        query = """
    INSERT OR REPLACE { ?song nie:usageCounter ?playcount . }
    WHERE {
        SELECT
            IF(bound(?usage), (?usage + 1), 1) AS ?playcount
            ?song
            WHERE {
                ?song a nmm:MusicPiece .
                OPTIONAL { ?song nie:usageCounter ?usage . }
                FILTER ( nie:url(?song) = "%(song_url)s" )
            }
        }
    """.replace("\n", " ").strip() % {
            'song_url': song_url
        }

        return query

    @staticmethod
    def update_last_played(song_url, time):
        query = """
    INSERT OR REPLACE { ?song nfo:fileLastAccessed '%(time)s' . }
    WHERE {
        SELECT
            ?song
            WHERE {
                ?song a nmm:MusicPiece .
                FILTER ( nie:url(?song) = "%(song_url)s" )
            }
        }
    """.replace("\n", " ").strip() % {
            'song_url': song_url,
            'time': time
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
    def create_tag(tag_text):
        query = """
    INSERT OR REPLACE {
        _:tag
            a nao:Tag ;
            rdfs:comment '%(tag_text)s'.
    }
    """.replace("\n", " ").strip() % {
            'tag_text': tag_text
        }
        return query

    @staticmethod
    def create_playlist_with_tag(title, tag_text):
        # TODO: make this an extension of 'create playlist' rather than its own func.?
        # TODO: CREATE TAG IF IT DOESN'T EXIST!
        query = """
    INSERT {
        _:playlist
            a nmm:Playlist ;
            a nfo:MediaList ;
            nie:title "%(title)s" ;
            nfo:entryCounter 0 ;
            nao:hasTag ?tag.
    }
    WHERE {
        SELECT ?tag
        WHERE {
            ?tag a nao:Tag ;
                rdfs:comment '%(tag_text)s'.
        }
    }
    """.replace("\n", " ").strip() % {
            'title': title,
            'tag_text': tag_text
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
            (?counter + 1) AS ?position
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
            (?old_position - 1) AS ?position
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
            (?counter - 1) AS ?new_counter
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
    def get_playlist_with_tag(playlist_tag):
        query = """
    ?playlist
        a nmm:Playlist ;
        nao:hasTag ?tag .
    ?tag rdfs:comment ?tag_text .
    FILTER ( ?tag_text = '%(playlist_tag)s' )
    """.replace('\n', ' ').strip() % {'playlist_tag': playlist_tag}

        return Query.playlists(query)

    @staticmethod
    def get_playlist_with_urn(playlist_urn):
        query = """
    SELECT DISTINCT
        tracker:id(<%(playlist_urn)s>) AS ?id
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
        tracker:id(<%(entry_urn)s>) AS ?id
    WHERE {
        <%(entry_urn)s> a nfo:MediaFileListEntry
    }
    """.replace('\n', ' ').strip() % {'entry_urn': entry_urn}
        return query

    @staticmethod
    def clear_playlist_with_id(playlist_id):
        query = """
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
                tracker:id(?playlist) = %(playlist_id)s
            )
        }
        """.replace('\n', ' ').strip() % {'playlist_id': playlist_id}

        return query

    @staticmethod
    def get_most_played_songs():
        # TODO: set playlist size somewhere? Currently default is 50.
        query = """
        SELECT ?url
        WHERE {
            ?song a nmm:MusicPiece ;
                nie:usageCounter ?count ;
                nie:isStoredAs ?as .
          ?as nie:url ?url .
          FILTER ( STRSTARTS(?url, '%(music_dir)s') )
        } ORDER BY DESC(?count) LIMIT 50
        """.replace('\n', ' ').strip() % {
            'music_dir': Query.MUSIC_URI
        }

        return query

    @staticmethod
    def get_never_played_songs():
        query = """
        SELECT ?url
        WHERE {
            ?song a nmm:MusicPiece ;
                nie:isStoredAs ?as .
            ?as nie:url ?url .
            FILTER ( NOT EXISTS { ?song nie:usageCounter ?count .}
                     && STRSTARTS(?url, '%(music_dir)s') )
        } ORDER BY nfo:fileLastAccessed(?song) LIMIT 50
        """.replace('\n', ' ').strip() % {
            'music_dir': Query.MUSIC_URI
        }

        return query

    @staticmethod
    def get_recently_played_songs():
            #TODO: or this could take comparison date as an argument so we don't need to make a date string in query.py...
            #TODO: set time interval somewhere? A settings file? (Default is maybe 2 weeks...?)

            days_difference = 7  # currently hardcoding time interval of 7 days
            seconds_difference = days_difference * SECONDS_PER_DAY
            compare_date = time.strftime(
                sparql_midnight_dateTime_format, time.gmtime(time.time() - seconds_difference))

            query = """
            SELECT ?url
            WHERE {
                ?song a nmm:MusicPiece ;
                    nie:isStoredAs ?as ;
                    nfo:fileLastAccessed ?last_played .
                ?as nie:url ?url .
                FILTER ( ?last_played > '%(compare_date)s'^^xsd:dateTime
                         && EXISTS { ?song nie:usageCounter ?count .}
                         && STRSTARTS(?url, '%(music_dir)s') )
            } ORDER BY DESC(?last_played) LIMIT 50
            """.replace('\n', ' ').strip() % {
                'compare_date': compare_date,
                'music_dir': Query.MUSIC_URI
            }

            return query

    @staticmethod
    def get_recently_added_songs():
        #TODO: or this could take comparison date as an argument so we don't need to make a date string in query.py...
        #TODO: set time interval somewhere? A settings file? (Default is maybe 2 weeks...?)

        days_difference = 7  # currently hardcoding time interval of 7 days
        seconds_difference = days_difference * SECONDS_PER_DAY
        compare_date = time.strftime(
            sparql_midnight_dateTime_format,
            time.gmtime(time.time() - seconds_difference))

        query = """
        SELECT ?url
        WHERE {
            ?song a nmm:MusicPiece ;
                nie:isStoredAs ?as ;
                tracker:added ?added .
            ?as nie:url ?url .
            FILTER ( ?added > '%(compare_date)s'^^xsd:dateTime
                     && STRSTARTS(?url, '%(music_dir)s') )
        } ORDER BY DESC(?added) LIMIT 50
        """.replace('\n', ' ').strip() % {
            'compare_date': compare_date,
            'music_dir': Query.MUSIC_URI
        }

        return query

    @staticmethod
    def get_favorite_songs():
        query = """
    SELECT ?url
    WHERE {
        ?song a nmm:MusicPiece ;
            nie:isStoredAs ?as ;
            nao:hasTag nao:predefined-tag-favorite .
        ?as nie:url ?url .
        FILTER ( STRSTARTS(?url, '%(music_dir)s') )
    } ORDER BY DESC(tracker:added(?song))
    """.replace('\n', ' ').strip() % {
            'music_dir': Query.MUSIC_URI,
        }

        return query

    # Functions for search
    # TODO: make those queries actually return something
    @staticmethod
    def get_albums_with_any_match(name):
        name = Tracker.sparql_escape_string(GLib.utf8_normalize(GLib.utf8_casefold(name, -1), -1, GLib.NormalizeMode.NFKD))
        query = """
            {
                SELECT DISTINCT
                    nmm:musicAlbum(?song) AS ?album
                {
                    ?song a nmm:MusicPiece .
                    BIND(tracker:normalize(nie:title(nmm:musicAlbum(?song)), 'nfkd') AS ?match1) .
                    BIND(tracker:normalize(nmm:artistName(nmm:performer(?song)), 'nfkd') AS ?match2) .
                    BIND(tracker:normalize(nie:title(?song), 'nfkd') AS ?match3) .
                    FILTER (
                        CONTAINS(tracker:case-fold(tracker:unaccent(?match1)), "%(name)s") ||
                        CONTAINS(tracker:case-fold(?match1), "%(name)s") ||
                        CONTAINS(tracker:case-fold(tracker:unaccent(?match2)), "%(name)s") ||
                        CONTAINS(tracker:case-fold(?match2), "%(name)s") ||
                        CONTAINS(tracker:case-fold(tracker:unaccent(?match3)), "%(name)s") ||
                        CONTAINS(tracker:case-fold(?match3), "%(name)s")
                    )
                }
            }
            """.replace('\n', ' ').strip() % {'name': name}

        return Query.albums(query)

    @staticmethod
    def get_albums_with_artist_match(name):
        name = Tracker.sparql_escape_string(name)
        query = """?performer fts:match '"nmm:artistName" : %(name)s*' . """.replace('\n', ' ').strip() % {'name': name}

        return Query.albums(query)

    @staticmethod
    def get_albums_with_album_match(name):
        name = Tracker.sparql_escape_string(name)
        query = """?album fts:match '"nie:title" : %(name)s*' . """.replace('\n', ' ').strip() % {'name': name}

        return Query.albums(query)

    @staticmethod
    def get_albums_with_composer_match(name):
        name = Tracker.sparql_escape_string(name)
        query = """
            ?song nmm:composer ?composer .
            ?composer fts:match '"nmm:artistName" : %(name)s*' .
        """.replace('\n', ' ').strip() % {
            'name': name
        }

        return Query.albums(query)

    @staticmethod
    def get_albums_with_track_match(name):
        name = Tracker.sparql_escape_string(name)
        query = """?song fts:match '"nie:title" : %(name)s*' . """.replace('\n', ' ').strip() % {'name': name}

        return Query.albums(query)

    @staticmethod
    def get_artists_with_any_match(name):
        name = Tracker.sparql_escape_string(GLib.utf8_normalize(GLib.utf8_casefold(name, -1), -1, GLib.NormalizeMode.NFKD))
        query = """
            {
                SELECT DISTINCT
                    nmm:musicAlbum(?song) AS ?album
                {
                    ?song a nmm:MusicPiece .
                    BIND(tracker:normalize(nie:title(nmm:musicAlbum(?song)), 'nfkd') AS ?match1) .
                    BIND(tracker:normalize(nmm:artistName(nmm:performer(?song)), 'nfkd') AS ?match2) .
                    BIND(tracker:normalize(nie:title(?song), 'nfkd') AS ?match3) .
                    FILTER (
                        CONTAINS(tracker:case-fold(tracker:unaccent(?match1)), "%(name)s") ||
                        CONTAINS(tracker:case-fold(?match1), "%(name)s") ||
                        CONTAINS(tracker:case-fold(tracker:unaccent(?match2)), "%(name)s") ||
                        CONTAINS(tracker:case-fold(?match2), "%(name)s") ||
                        CONTAINS(tracker:case-fold(tracker:unaccent(?match3)), "%(name)s") ||
                        CONTAINS(tracker:case-fold(?match3), "%(name)s")
                    )
                }
            }
            """.replace('\n', ' ').strip() % {'name': name}

        return Query.artists(query)

    @staticmethod
    def get_artists_with_artist_match(name):
        name = Tracker.sparql_escape_string(name)
        query = """?performer fts:match '"nmm:artistName" : %(name)s*' . """.replace('\n', ' ').strip() % {'name': name}

        return Query.artists(query)

    @staticmethod
    def get_artists_with_album_match(name):
        name = Tracker.sparql_escape_string(name)
        query = """?album fts:match '"nie:title" : %(name)s*' . """.replace('\n', ' ').strip() % {'name': name}

        return Query.artists(query)

    @staticmethod
    def get_artists_with_composer_match(name):
        name = Tracker.sparql_escape_string(name)
        query = """
            ?song nmm:composer ?composer .
            ?composer fts:match '"nmm:artistName" : %(name)s*' .
        """.replace('\n', ' ').strip() % {
            'name': name
        }

        return Query.artists(query)

    @staticmethod
    def get_artists_with_track_match(name):
        name = Tracker.sparql_escape_string(name)
        query = """?song fts:match '"nie:title" : %(name)s*' . """.replace('\n', ' ').strip() % {'name': name}

        return Query.artists(query)

    @staticmethod
    def get_songs_with_any_match(name):
        name = Tracker.sparql_escape_string(GLib.utf8_normalize(GLib.utf8_casefold(name, -1), -1, GLib.NormalizeMode.NFKD))
        query = """
            {
                SELECT DISTINCT
                    ?song
                WHERE {
                    ?song a nmm:MusicPiece .
                    BIND(tracker:normalize(nie:title(nmm:musicAlbum(?song)), 'nfkd') AS ?match1) .
                    BIND(tracker:normalize(nmm:artistName(nmm:performer(?song)), 'nfkd') AS ?match2) .
                    BIND(tracker:normalize(nie:title(?song), 'nfkd') AS ?match3) .
                    FILTER (
                        CONTAINS(tracker:case-fold(tracker:unaccent(?match1)), "%(name)s") ||
                        CONTAINS(tracker:case-fold(?match1), "%(name)s") ||
                        CONTAINS(tracker:case-fold(tracker:unaccent(?match2)), "%(name)s") ||
                        CONTAINS(tracker:case-fold(?match2), "%(name)s") ||
                        CONTAINS(tracker:case-fold(tracker:unaccent(?match3)), "%(name)s") ||
                        CONTAINS(tracker:case-fold(?match3), "%(name)s")
                    )
                }
            }
            """.replace('\n', ' ').strip() % {'name': name}

        return Query.songs(query)

    @staticmethod
    def get_songs_with_artist_match(name):
        name = Tracker.sparql_escape_string(name)
        query = """?performer fts:match '"nmm:artistName" : %(name)s*' . """.replace('\n', ' ').strip() % {'name': name}

        return Query.songs(query)

    @staticmethod
    def get_songs_with_album_match(name):
        name = Tracker.sparql_escape_string(name)
        query = """?album fts:match '"nie:title" : %(name)s*' . """.replace('\n', ' ').strip() % {'name': name}

        return Query.songs(query)

    @staticmethod
    def get_songs_with_composer_match(name):
        name = Tracker.sparql_escape_string(name)
        query = """
            ?song nmm:composer ?composer .
            ?composer fts:match '"nmm:artistName" : %(name)s*' .
        """.replace('\n', ' ').strip() % {
            'name': name
        }

        return Query.songs(query)

    @staticmethod
    def get_songs_with_track_match(name):
        name = Tracker.sparql_escape_string(name)
        query = """?song fts:match '"nie:title" : %(name)s*' . """.replace('\n', ' ').strip() % {'name': name}

        return Query.songs(query)

    @staticmethod
    def clear_playlist(playlist_id):
        # TODO is there a way to do this with only one FILTER statement?

        query = """
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
            tracker:id(?playlist) = %(playlist_id)s
        )
    }
    INSERT OR REPLACE {
        ?playlist nfo:entryCounter '0'
    }
    WHERE {
        ?playlist
            a nmm:Playlist ;
            a nfo:MediaList .
        FILTER (
            tracker:id(?playlist) = %(playlist_id)s
        )
    }
        """.replace("\n", " ").strip() % {
            'playlist_id': playlist_id
        }

        return query

    @staticmethod
    def add_favorite(song_url):
        query = """
            INSERT {
                ?song nao:hasTag nao:predefined-tag-favorite
            }
            WHERE {
                ?song a nmm:MusicPiece .
                FILTER ( nie:url(?song) = "%(song_url)s" )
            }
        """.replace("\n", " ").strip() % {
            'song_url': song_url

        }

        return query

    @staticmethod
    def remove_favorite(song_url):
        query = """
            DELETE {
                ?song nao:hasTag nao:predefined-tag-favorite
            }
            WHERE {
                ?song a nmm:MusicPiece .
                FILTER ( nie:url(?song) = "%(song_url)s" )
            }
        """.replace("\n", " ").strip() % {
            'song_url': song_url
        }

        return query

    @staticmethod
    def is_audio(media_id):
        query = """
            SELECT DISTINCT
            rdf:type
            nie:mimeType(?urn) AS mime_type
            {
                ?urn rdf:type nie:InformationElement .
                FILTER ( tracker:id(?urn) = "%(media_id)s" )
            }
        """.replace('\n', '').strip() % {
            'media_id' : media_id
        }

        return query
