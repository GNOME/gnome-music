import gi
gi.require_versions({"Grl": "0.3", 'Tracker': "2.0"})
from gi.repository import Grl, GLib, GObject, Tracker

from gnomemusic.corealbum import CoreAlbum
from gnomemusic.coreartist import CoreArtist
from gnomemusic.coredisc import CoreDisc
from gnomemusic.coresong import CoreSong
from gnomemusic.grilowrappers.grltrackerplaylists import GrlTrackerPlaylists


class GrlTrackerSource(GObject.GObject):

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

    def __repr__(self):
        return "<GrlTrackerSource>"

    def __init__(self, source, coremodel, coreselection, grilo):
        super().__init__()

        self._coremodel = coremodel
        self._coreselection = coreselection
        self._grilo = grilo
        self._source = source
        self._model = self._coremodel.props.songs
        self._albums_model = self._coremodel.props.albums
        self._album_ids = {}
        self._artists_model = self._coremodel.props.artists
        self._hash = {}
        self._song_search_model = self._coremodel.props.songs_search
        self._album_search_model = self._coremodel.props.albums_search
        self._artist_search_model = self._coremodel.props.artists_search

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self._initial_fill(self._source)
        self._initial_albums_fill(self._source)
        self._initial_artists_fill(self._source)

        self._tracker_playlists = GrlTrackerPlaylists(
            source, coremodel, coreselection, grilo)

        self._source.connect("content-changed", self._on_content_changed)

    @GObject.Property(
        type=Grl.Source, default=None, flags=GObject.ParamFlags.READABLE)
    def source(self):
        return self._source

    def _on_content_changed(self, source, medias, change_type, loc_unknown):
        for media in medias:
            if change_type == Grl.SourceChangeType.ADDED:
                print("ADDED", media.get_id())
                self._add_media(media)
                self._check_album_change(media)
            elif change_type == Grl.SourceChangeType.CHANGED:
                print("CHANGED", media.get_id())
                self._requery_media(media.get_id(), True)
            elif change_type == Grl.SourceChangeType.REMOVED:
                print("REMOVED", media.get_id())
                self._remove_media(media)
                self._check_album_change(media)

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
        {
            ?album a nmm:MusicAlbum .
            ?song a nmm:MusicPiece ;
                    nmm:musicAlbum ?album ;
                    nmm:performer ?performer .
            OPTIONAL { ?song nmm:composer/nmm:artistName ?composer . }
            OPTIONAL { ?album nmm:albumArtist/nmm:artistName ?album_artist . }
        } GROUP BY ?album
        """.replace('\n', ' ').strip()

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

    def _remove_media(self, media):
        try:
            coresong = self._hash.pop(media.get_id())
        except KeyError:
            return

        for idx, coresong_model in enumerate(self._model):
            if coresong_model is coresong:
                print(
                    "removing", coresong.props.media.get_id(),
                    coresong.props.title)
                self._model.remove(idx)
                break

    def _requery_media(self, grilo_id, only_update=False):
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
                FILTER ( tracker:id(?song) = %(grilo_id)s )
            }
        """.replace('\n', ' ').strip() % {
            'grilo_id': grilo_id
        }

        options = self._fast_options.copy()

        if only_update:
            self._source.query(
                query, self.METADATA_KEYS, options, self._only_update_media)
        else:
            self._source.query(
                query, self.METADATA_KEYS, options, self._update_media)

    def _add_media(self, media):
        self._requery_media(media.get_id())

    def _only_update_media(self, source, op_id, media, user_data, error):
        if error:
            print("ERROR", error)
            return

        if not media:
            return

        print("ONLY UPDATE")
        self._hash[media.get_id()].update(media)
        print("UPDATE ID", media.get_id(), media.get_title())

    def _update_media(self, source, op_id, media, user_data, error):
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

    def _on_source_removed(self, registry, source):
        print("removed", source.props.source_id)

    def _initial_fill(self, source):
        options = self._fast_options.copy()
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
            }
        """.replace('\n', ' ').strip()

        self._source.query(
            query, self.METADATA_KEYS, options, self._add_to_model)

    def _add_to_model(self, source, op_id, media, user_data, error):
        if error:
            print("ERROR", error)
            return

        if not media:
            return

        song = CoreSong(media, self._coreselection, self._grilo)
        self._model.append(song)
        self._hash[media.get_id()] = song

    def _initial_albums_fill(self, source):
        query = """
        SELECT
            rdf:type(?album)
            tracker:id(?album) AS ?id
            nie:title(?album) AS ?title
            ?composer AS ?composer
            ?album_artist AS ?album_artist
            nmm:artistName(?performer) AS ?artist
            YEAR(MAX(nie:contentCreated(?song))) AS ?creation_date
        {
            ?album a nmm:MusicAlbum .
            ?song a nmm:MusicPiece ;
                    nmm:musicAlbum ?album ;
                    nmm:performer ?performer .
            OPTIONAL { ?song nmm:composer/nmm:artistName ?composer . }
            OPTIONAL { ?album nmm:albumArtist/nmm:artistName ?album_artist . }
        } GROUP BY ?album
        """.replace('\n', ' ').strip()

        options = self._fast_options.copy()

        source.query(
            query, self.METADATA_KEYS, options, self._add_to_albums_model)

    def _add_to_albums_model(self, source, op_id, media, user_data, error):
        if error:
            print("ERROR", error)
            return

        if not media:
            print("NO MEDIA", source, op_id, media, error)
            return

        album = CoreAlbum(media, self._coremodel)
        self._albums_model.append(album)
        self._album_ids[media.get_id()] = album

    def _initial_artists_fill(self, source):
        query = """
        SELECT
            rdf:type(?artist_class)
            tracker:id(?artist_class) AS ?id
            nmm:artistName(?artist_class) AS ?artist
        {
            ?artist_class a nmm:Artist .
            ?song a nmm:MusicPiece;
                    nmm:musicAlbum ?album;
                    nmm:performer ?artist_class .
        } GROUP BY ?artist_class
        """.replace('\n', ' ').strip()

        options = self._fast_options.copy()

        source.query(
            query, self.METADATA_KEYS, options, self._add_to_artists_model)

    def _add_to_artists_model(self, source, op_id, media, user_data, error):
        if error:
            print("ERROR", error)
            return

        if not media:
            print("NO MEDIA", source, op_id, media, error)
            self._coremodel.emit("artists-loaded")
            return

        artist = CoreArtist(media, self._coremodel)
        self._artists_model.append(artist)

    def get_artist_albums(self, media, model):
        artist_id = media.get_id()

        query = """
        SELECT DISTINCT
            rdf:type(?album)
            tracker:id(?album) AS ?id
            nie:title(?album) AS ?title
        WHERE
        {
            ?album a nmm:MusicAlbum .
            OPTIONAL { ?album  nmm:albumArtist ?album_artist . }
            ?song a nmm:MusicPiece;
                    nmm:musicAlbum ?album;
                    nmm:performer ?artist .
            FILTER ( tracker:id(?album_artist) = %(artist_id)s
                     || tracker:id(?artist) = %(artist_id)s )
        }
        """.replace('\n', ' ').strip() % {
            'artist_id': int(artist_id)
        }

        options = self._fast_options.copy()

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

        self._source.query(query, self.METADATA_KEYS, options, query_cb)

    def get_album_discs(self, media, disc_model):
        album_id = media.get_id()

        def _disc_nr_cb(source, op_id, media, user_data, error):
            if error:
                print("ERROR", error)
                return

            if not media:
                return

            disc_nr = media.get_album_disc_number()
            coredisc = CoreDisc(media, disc_nr, self._coremodel)
            disc_model.append(coredisc)

        query = """
        SELECT DISTINCT
            rdf:type(?song)
            tracker:id(?album) AS ?id
            nmm:setNumber(nmm:musicAlbumDisc(?song)) as ?album_disc_number
        WHERE
        {
            ?song a nmm:MusicPiece;
                    nmm:musicAlbum ?album .
            FILTER ( tracker:id(?album) = %(album_id)s )
        }
        """.replace('\n', ' ').strip() % {
            'album_id': int(album_id)
        }

        options = self._fast_options.copy()

        self._source.query(query, self.METADATA_KEYS, options, _disc_nr_cb)

    def populate_album_disc_songs(self, media, disc_nr, _callback):
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
        WHERE
        {
            ?song a nmm:MusicPiece ;
                    nmm:musicAlbum ?album .
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) } .
            FILTER ( tracker:id(?album) = %(album_id)s
                     && nmm:setNumber(nmm:musicAlbumDisc(?song)) = %(disc_nr)s
                   )
        }
        """.replace('\n', ' ').strip() % {
            'album_id': album_id,
            'disc_nr': disc_nr,
        }

        options = self._fast_options.copy()

        self._source.query(query, self.METADATA_KEYS, options, _callback)

    def populate_album_songs(self, media, _callback):
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
        WHERE
        {
            ?song a nmm:MusicPiece ;
                    nmm:musicAlbum ?album .
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) } .
            FILTER ( tracker:id(?album) = %(album_id)s )
        }
        """.replace('\n', ' ').strip() % {
            'album_id': album_id,
        }

        options = self._fast_options.copy()

        self._source.query(query, self.METADATA_KEYS, options, _callback)

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
        }
        """.replace('\n', ' ').strip() % {'name': term}

        filter_ids = []

        def songs_filter(coresong):
            return coresong.media.get_id() in filter_ids

        def search_cb(source, op_id, media, data, error):
            if error:
                print("ERROR", error)
                return

            if not media:
                self._song_search_model.set_filter_func(songs_filter)
                return

            filter_ids.append(media.get_id())

        options = self._fast_options.copy()

        self._source.query(query, self.METADATA_KEYS, options, search_cb)

        # Album search

        query = """
        SELECT DISTINCT
            rdf:type(nmm:musicAlbum(?song))
            tracker:id(nmm:musicAlbum(?song)) AS ?id
        {
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
        }
        """.replace('\n', ' ').strip() % {'name': term}

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
        {
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
        }
        """.replace('\n', ' ').strip() % {'name': term}

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
