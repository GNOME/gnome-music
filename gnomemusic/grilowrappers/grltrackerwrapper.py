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

import gi
gi.require_versions({"Gfm": "0.1", "Grl": "0.3", 'Tracker': "2.0"})
from gi.repository import Gfm, Grl, GLib, GObject, Tracker

from gnomemusic.corealbum import CoreAlbum
from gnomemusic.coreartist import CoreArtist
from gnomemusic.coredisc import CoreDisc
from gnomemusic.coresong import CoreSong
from gnomemusic.grilowrappers.grltrackerplaylists import GrlTrackerPlaylists


class GrlTrackerWrapper(GObject.GObject):
    """Wrapper for the Grilo Tracker source.
    """

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

    METADATA_THUMBNAIL_KEYS = [
        Grl.METADATA_KEY_ID,
        Grl.METADATA_KEY_THUMBNAIL,
    ]

    def __repr__(self):
        return "<GrlTrackerWrapper>"

    def __init__(self, source, coremodel, coreselection, grilo):
        """Initialize the Tracker wrapper

        :param Grl.TrackerSource source: The Tracker source to wrap
        :param CoreModel coremodel: CoreModel instance to use models
        from
        :param CoreSelection coreselection: CoreSelection instance to
        use
        :param CoreGrilo grilo: The CoreGrilo instance
        """
        super().__init__()

        self._coremodel = coremodel
        self._coreselection = coreselection
        self._grilo = grilo
        self._source = source
        self._model = self._coremodel.props.songs
        self._albums_model = self._coremodel.props.albums
        self._album_ids = {}
        self._artists_model = self._coremodel.props.artists
        self._artist_ids = {}
        self._hash = {}
        self._song_search_proxy = self._coremodel.props.songs_search_proxy
        self._album_search_model = self._coremodel.props.albums_search
        self._artist_search_model = self._coremodel.props.artists_search

        self._song_search_tracker = Gfm.FilterListModel.new(self._model)
        self._song_search_tracker.set_filter_func(lambda a: False)
        self._song_search_proxy.append(self._song_search_tracker)

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self._initial_songs_fill(self._source)
        self._initial_albums_fill(self._source)
        self._initial_artists_fill(self._source)

        self._tracker_playlists = GrlTrackerPlaylists(
            source, coremodel, coreselection, grilo)

        self._source.notify_change_start()
        self._source.connect("content-changed", self._on_content_changed)

    @GObject.Property(
        type=Grl.Source, default=None, flags=GObject.ParamFlags.READABLE)
    def source(self):
        return self._source

    @staticmethod
    def _location_filter():
        try:
            music_dir = GLib.get_user_special_dir(
                GLib.UserDirectory.DIRECTORY_MUSIC)
            assert music_dir is not None
        except (TypeError, AssertionError):
            print("XDG Music dir is not set")
            return

        music_dir = Tracker.sparql_escape_string(
            GLib.filename_to_uri(music_dir))

        query = """
        FILTER (STRSTARTS(nie:url(?song), '%(music_dir)s/'))
        """.replace('\n', ' ').strip() % {
            'music_dir': music_dir
        }

        return query

    def _on_content_changed(self, source, medias, change_type, loc_unknown):
        for media in medias:
            if change_type == Grl.SourceChangeType.ADDED:
                print("ADDED", media.get_id())
                self._add_media(media)
                self._check_album_change(media)
                self._check_artist_change(media)
            elif change_type == Grl.SourceChangeType.CHANGED:
                print("CHANGED", media.get_id())
                self._changed_media(media)
            elif change_type == Grl.SourceChangeType.REMOVED:
                print("REMOVED", media.get_id())
                self._remove_media(media)
                self._check_album_change(media)
                self._check_artist_change(media)

    def _check_album_change(self, media):
        album_ids = {}

        query = """
        SELECT
            rdf:type(?album)
            tracker:id(?album) AS ?id
            nie:title(?album) AS ?title
            ?composer AS ?composer
            ?album_artist AS ?album_artist
            nmm:artistName(?performer) AS ?artist
            YEAR(MAX(nie:contentCreated(?song))) AS ?creation_date
        WHERE {
            ?album a nmm:MusicAlbum .
            ?song a nmm:MusicPiece ;
                    nmm:musicAlbum ?album ;
                    nmm:performer ?performer .
            OPTIONAL { ?song nmm:composer/nmm:artistName ?composer . }
            OPTIONAL { ?album nmm:albumArtist/nmm:artistName ?album_artist . }
            %(location_filter)s
        } GROUP BY ?album
        """.replace('\n', ' ').strip() % {
            'location_filter': self._location_filter()
        }

        def check_album_cb(source, op_id, media, user_data, error):
            if error:
                print("ERROR", error)
                return

            if not media:
                changed_ids = set(
                    album_ids.keys()) ^ set(self._album_ids.keys())
                print("ALBUMS CHANGED", changed_ids)

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

            album = CoreAlbum(media, self._coremodel)
            album_ids[media.get_id()] = album

        options = self._fast_options.copy()

        self._source.query(
            query, self.METADATA_KEYS, options, check_album_cb)

    def _check_artist_change(self, media):
        artist_ids = {}

        query = """
        SELECT
            rdf:type(?artist_class)
            tracker:id(?artist_class) AS ?id
            nmm:artistName(?artist_class) AS ?artist
        WHERE {
            ?artist_class a nmm:Artist .
            ?song a nmm:MusicPiece;
                    nmm:musicAlbum ?album;
                    nmm:performer ?artist_class .
            %(location_filter)s
        } GROUP BY ?artist_class
        """.replace('\n', ' ').strip() % {
            'location_filter': self._location_filter()
        }

        def check_artist_cb(source, op_id, media, user_data, error):
            if error:
                print("ERROR", error)
                return

            if not media:
                changed_ids = set(
                    artist_ids.keys()) ^ set(self._artist_ids.keys())
                print("ARTISTS CHANGED", changed_ids)

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

            artist = CoreArtist(media, self._coremodel)
            artist_ids[media.get_id()] = artist

        options = self._fast_options.copy()

        self._source.query(
            query, self.METADATA_KEYS, options, check_artist_cb)

    def _remove_media(self, media):
        try:
            coresong = self._hash.pop(media.get_id())
        except KeyError:
            print("Removal KeyError")
            return

        for idx, coresong_model in enumerate(self._model):
            if coresong_model is coresong:
                print(
                    "removing", coresong.props.media.get_id(),
                    coresong.props.title)
                self._model.remove(idx)
                break

    def _song_media_query(self, media_id):
        query = """
        SELECT DISTINCT
            rdf:type(?song)
            ?song AS ?tracker_urn
            nie:title(?song) AS ?title
            tracker:id(?song) AS ?id
            ?song
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
            ?song a nmm:MusicPiece .
            OPTIONAL {
                ?song nao:hasTag ?tag .
                FILTER (?tag = nao:predefined-tag-favorite)
            }
            FILTER ( tracker:id(?song) = %(media_id)s )
            %(location_filter)s
        }
        """.replace('\n', ' ').strip() % {
            'location_filter': self._location_filter(),
            'media_id': media_id
        }

        return query

    def _add_media(self, media):

        def _add_media(source, op_id, media, user_data, error):
            if error:
                print("ERROR", error)
                return

            if not media:
                return

            # FIXME: Figure out why we get double additions.
            if media.get_id() in self._hash.keys():
                print("ALREADY ADDED")
                return

            song = CoreSong(media, self._coreselection, self._grilo)
            self._model.append(song)
            self._hash[media.get_id()] = song

            print("UPDATE ID", media.get_id(), media.get_title())

        options = self._fast_options.copy()

        self._source.query(
            self._song_media_query(media.get_id()), self.METADATA_KEYS,
            options, _add_media)

    def _changed_media(self, media):

        def _update_changed_media(source, op_id, media, user_data, error):
            if error:
                print("ERROR", error)
                return

            if not media:
                return

            self._hash[media.get_id()].update(media)

        options = self._fast_options.copy()

        self._source.query(
            self._song_media_query(media.get_id()), self.METADATA_KEYS,
            options, _update_changed_media)

    def _initial_songs_fill(self, source):

        def _add_to_model(source, op_id, media, user_data, error):
            if error:
                print("ERROR", error)
                return

            if not media:
                return

            song = CoreSong(media, self._coreselection, self._grilo)
            self._model.append(song)
            self._hash[media.get_id()] = song

        query = """
        SELECT
            rdf:type(?song)
            ?song AS ?tracker_urn
            nie:title(?song) AS ?title
            tracker:id(?song) AS ?id
            ?song
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
            ?song a nmm:MusicPiece .
            OPTIONAL {
                ?song nao:hasTag ?tag .
                FILTER (?tag = nao:predefined-tag-favorite)
            }
            %(location_filter)s
        }
        """.replace('\n', ' ').strip() % {
            'location_filter': self._location_filter()
        }

        options = self._fast_options.copy()
        self._source.query(query, self.METADATA_KEYS, options, _add_to_model)

    def _initial_albums_fill(self, source):

        def _add_to_albums_model(source, op_id, media, user_data, error):
            if error:
                print("ERROR", error)
                return

            if not media:
                return

            album = CoreAlbum(media, self._coremodel)
            self._albums_model.append(album)
            self._album_ids[media.get_id()] = album

        query = """
        SELECT
            rdf:type(?album)
            tracker:id(?album) AS ?id
            nie:title(?album) AS ?title
            ?composer AS ?composer
            ?album_artist AS ?album_artist
            nmm:artistName(?performer) AS ?artist
            YEAR(MAX(nie:contentCreated(?song))) AS ?creation_date
        WHERE
        {
            ?album a nmm:MusicAlbum .
            ?song a nmm:MusicPiece ;
                    nmm:musicAlbum ?album ;
                    nmm:performer ?performer .
            OPTIONAL { ?song nmm:composer/nmm:artistName ?composer . }
            OPTIONAL { ?album nmm:albumArtist/nmm:artistName ?album_artist . }
            %(location_filter)s
        } GROUP BY ?album
        """.replace('\n', ' ').strip() % {
            'location_filter': self._location_filter()
        }

        options = self._fast_options.copy()

        source.query(query, self.METADATA_KEYS, options, _add_to_albums_model)

    def _initial_artists_fill(self, source):

        def _add_to_artists_model(source, op_id, media, user_data, error):
            if error:
                print("ERROR", error)
                return

            if not media:
                self._coremodel.emit("artists-loaded")
                return

            artist = CoreArtist(media, self._coremodel)
            self._artists_model.append(artist)
            self._artist_ids[media.get_id()] = artist

        query = """
        SELECT
            rdf:type(?artist)
            tracker:id(?artist) AS ?id
            nmm:artistName(?artist) AS ?artist
        WHERE {
            ?artist a nmm:Artist .
            ?song a nmm:MusicPiece;
                    nmm:musicAlbum ?album;
                    nmm:performer ?artist .
            %(location_filter)s
        } GROUP BY ?artist
        """.replace('\n', ' ').strip() % {
            'location_filter': self._location_filter()
        }

        options = self._fast_options.copy()

        source.query(
            query, [Grl.METADATA_KEY_ARTIST], options, _add_to_artists_model)

    def get_artist_albums(self, media, model):
        """Get all albums by an artist

        :param Grl.Media media: The media with the artist id
        :param Dazzle.ListModelFilter model: The model to fill
        """
        artist_id = media.get_id()

        query = """
        SELECT DISTINCT
            rdf:type(?album)
            tracker:id(?album) AS ?id
            nie:title(?album) AS ?title
        WHERE {
            ?album a nmm:MusicAlbum .
            OPTIONAL { ?album  nmm:albumArtist ?album_artist . }
            ?song a nmm:MusicPiece;
                    nmm:musicAlbum ?album;
                    nmm:performer ?artist .
            FILTER ( tracker:id(?album_artist) = %(artist_id)s
                     || tracker:id(?artist) = %(artist_id)s )
            %(location_filter)s
        }
        """.replace('\n', ' ').strip() % {
            'artist_id': int(artist_id),
            'location_filter': self._location_filter()
        }

        albums = []

        def query_cb(source, op_id, media, user_data, error):
            if error:
                print("ERROR", error)
                return

            if not media:
                model.set_filter_func(albums_filter, albums)
                return

            albums.append(media)

        def albums_filter(corealbum, albums):
            for media in albums:
                if media.get_id() == corealbum.props.media.get_id():
                    return True

            return False

        options = self._fast_options.copy()
        self._source.query(
            query, [Grl.METADATA_KEY_TITLE], options, query_cb)

    def get_album_discs(self, media, disc_model):
        """Get all discs of an album

        :param Grl.Media media: The media with the album id
        :param Gfm.SortListModel disc_model: The model to fill
        """
        album_id = media.get_id()

        query = """
        SELECT DISTINCT
            rdf:type(?song)
            tracker:id(?album) AS ?id
            nmm:setNumber(nmm:musicAlbumDisc(?song)) as ?album_disc_number
        WHERE {
            ?song a nmm:MusicPiece;
                    nmm:musicAlbum ?album .
            FILTER ( tracker:id(?album) = %(album_id)s )
            %(location_filter)s
        }
        """.replace('\n', ' ').strip() % {
            'album_id': int(album_id),
            'location_filter': self._location_filter()
        }

        def _disc_nr_cb(source, op_id, media, user_data, error):
            if error:
                print("ERROR", error)
                return

            if not media:
                return

            disc_nr = media.get_album_disc_number()
            coredisc = CoreDisc(media, disc_nr, self._coremodel)
            disc_model.append(coredisc)

        options = self._fast_options.copy()
        self._source.query(
            query, [Grl.METADATA_KEY_ALBUM_DISC_NUMBER], options, _disc_nr_cb)

    def populate_album_disc_songs(self, media, disc_nr, callback):
        # FIXME: Pass a model and fill it.
        # FIXME: The query is similar to the other song queries, reuse
        # if possible.
        """Get all songs of an album disc

        :param Grl.Media media: The media with the album id
        :param int disc_nr: The disc number
        :param callback: The callback to call for every song added
        """
        album_id = media.get_id()

        query = """
        SELECT DISTINCT
            rdf:type(?song)
            ?song AS ?tracker_urn
            tracker:id(?song) AS ?id
            nie:url(?song) AS ?url
            nie:title(?song) AS ?title
            nmm:artistName(nmm:performer(?song)) AS ?artist
            nie:title(nmm:musicAlbum(?song)) AS ?album
            nfo:duration(?song) AS ?duration
            nmm:trackNumber(?song) AS ?track_number
            nmm:setNumber(nmm:musicAlbumDisc(?song)) AS ?album_disc_number
            ?tag AS ?favourite
            nie:usageCounter(?song) AS ?play_count
        WHERE {
            ?song a nmm:MusicPiece ;
                    nmm:musicAlbum ?album .
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) } .
            FILTER ( tracker:id(?album) = %(album_id)s
                     && nmm:setNumber(nmm:musicAlbumDisc(?song)) = %(disc_nr)s
            )
            %(location_filter)s
        }
        """.replace('\n', ' ').strip() % {
            'album_id': album_id,
            'disc_nr': disc_nr,
            'location_filter': self._location_filter()
        }

        options = self._fast_options.copy()
        self._source.query(query, self.METADATA_KEYS, options, callback)

    def search(self, text):
        term = Tracker.sparql_escape_string(
            GLib.utf8_normalize(
                GLib.utf8_casefold(text, -1), -1, GLib.NormalizeMode.NFKD))

        query = """
        SELECT DISTINCT
            rdf:type(?song)
            tracker:id(?song) AS ?id
        WHERE {
            ?song a nmm:MusicPiece .
            BIND(tracker:normalize(
                nie:title(nmm:musicAlbum(?song)), 'nfkd') AS ?match1) .
            BIND(tracker:normalize(
                nmm:artistName(nmm:performer(?song)), 'nfkd') AS ?match2) .
            BIND(tracker:normalize(
                nie:title(?song), 'nfkd') AS ?match3) .
            BIND(
                tracker:normalize(nmm:composer(?song), 'nfkd') AS ?match4) .
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
        """.replace('\n', ' ').strip() % {
            'location_filter': self._location_filter(),
            'name': term
        }

        filter_ids = []

        def songs_filter(coresong):
            return coresong.media.get_id() in filter_ids

        def songs_search_cb(source, op_id, media, data, error):
            if error:
                print("ERROR", error)
                return

            if not media:
                self._song_search_tracker.set_filter_func(songs_filter)
                return

            filter_ids.append(media.get_id())

        options = self._fast_options.copy()

        self._source.query(query, self.METADATA_KEYS, options, songs_search_cb)

        # Album search

        query = """
        SELECT DISTINCT
            rdf:type(nmm:musicAlbum(?song))
            tracker:id(nmm:musicAlbum(?song)) AS ?id
        WHERE {
            ?song a nmm:MusicPiece .
            BIND(tracker:normalize(
                nie:title(nmm:musicAlbum(?song)), 'nfkd') AS ?match1) .
            BIND(tracker:normalize(
                nmm:artistName(nmm:performer(?song)), 'nfkd') AS ?match2) .
            BIND(tracker:normalize(nie:title(?song), 'nfkd') AS ?match3) .
            BIND(tracker:normalize(nmm:composer(?song), 'nfkd') AS ?match4) .
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
        """.replace('\n', ' ').strip() % {
            'location_filter': self._location_filter(),
            'name': term
        }

        album_filter_ids = []

        def album_filter(corealbum):
            return corealbum.media.get_id() in album_filter_ids

        def albums_search_cb(source, op_id, media, data, error):
            if error:
                print("ERROR", error)
                return

            if not media:
                self._album_search_model.set_filter_func(album_filter)
                return

            album_filter_ids.append(media.get_id())

        options = self._fast_options.copy()
        self._source.query(
            query, self.METADATA_KEYS, options, albums_search_cb)

        # Artist search

        query = """
        SELECT DISTINCT
            rdf:type(?artist)
            tracker:id(?artist) AS ?id
        WHERE {
            ?song a nmm:MusicPiece ;
                    nmm:musicAlbum ?album ;
                    nmm:performer ?artist .
            BIND(tracker:normalize(
                nie:title(nmm:musicAlbum(?song)), 'nfkd') AS ?match1) .
            BIND(tracker:normalize(
                nmm:artistName(nmm:performer(?song)), 'nfkd') AS ?match2) .
            BIND(tracker:normalize(nie:title(?song), 'nfkd') AS ?match3) .
            BIND(tracker:normalize(nmm:composer(?song), 'nfkd') AS ?match4) .
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
        """.replace('\n', ' ').strip() % {
            'location_filter': self._location_filter(),
            'name': term
        }

        artist_filter_ids = []

        def artist_filter(coreartist):
            return coreartist.media.get_id() in artist_filter_ids

        def artist_search_cb(source, op_id, media, data, error):
            if error:
                print("ERROR", error)
                return

            if not media:
                self._artist_search_model.set_filter_func(artist_filter)
                return

            artist_filter_ids.append(media.get_id())

        options = self._fast_options.copy()
        self._source.query(
            query, self.METADATA_KEYS, options, artist_search_cb)

    def get_album_art_for_item(self, coresong, callback):
        """Placeholder until we got a better solution
        """
        item_id = coresong.props.media.get_id()

        if coresong.props.media.is_audio():
            query = self._get_album_for_song_id(item_id)
        else:
            query = self._get_album_for_album_id(item_id)

        full_options = Grl.OperationOptions()
        full_options.set_resolution_flags(
            Grl.ResolutionFlags.FULL
            | Grl.ResolutionFlags.IDLE_RELAY)
        full_options.set_count(1)

        self.search_source.query(
            query, self.METADATA_THUMBNAIL_KEYS, full_options, callback)

    def _get_album_for_album_id(self, album_id):
        # Even though we check for the album_artist, we fill
        # the artist key, since Grilo coverart plugins use
        # only that key for retrieval.
        query = """
        SELECT DISTINCT
            rdf:type(?album)
            tracker:id(?album) AS ?id
            tracker:coalesce(nmm:artistName(?album_artist),
                             nmm:artistName(?song_artist)) AS ?artist
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
            %(location_filter)s
        }
        """.replace("\n", " ").strip() % {
                'album_id': album_id,
                'location_filter': self._location_filter()
        }

        return query

    def _get_album_for_song_id(self, song_id):
        # See get_album_for_album_id comment.
        query = """
        SELECT DISTINCT
            rdf:type(?album)
            tracker:id(?album) AS ?id
            tracker:coalesce(nmm:artistName(?album_artist),
                             nmm:artistName(?song_artist)) AS ?artist
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
                NOT EXISTS { ?song a nmm:Video }
                && NOT EXISTS { ?song a nmm:Playlist }
            )
            %(location_filter)s
        }
        """.replace("\n", " ").strip() % {
            'location_filter': self._location_filter(),
            'song_id': song_id
        }

        return query

    def stage_playlist_deletion(self, playlist):
        """Prepares playlist deletion.

        :param Playlist playlist: playlist
        """
        self._tracker_playlists.stage_playlist_deletion(playlist)

    def finish_playlist_deletion(self, playlist, deleted):
        """Finishes playlist deletion.

        :param Playlist playlist: playlist
        :param bool deleted: indicates if the playlist has been deleted
        """
        self._tracker_playlists.finish_playlist_deletion(playlist, deleted)

    def create_playlist(self, playlist_title, callback):
        """Creates a new user playlist.

        :param str playlist_title: playlist title
        :param callback: function to perform once, the playlist is created
        """
        self._tracker_playlists.create_playlist(playlist_title, callback)
