import gi
gi.require_version('Grl', '0.3')
from gi.repository import Grl, GObject

from gnomemusic.corealbum import CoreAlbum
from gnomemusic.coreartist import CoreArtist
from gnomemusic.coresong import CoreSong


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
        Grl.METADATA_KEY_LYRICS,
        Grl.METADATA_KEY_PLAY_COUNT,
        Grl.METADATA_KEY_THUMBNAIL,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_TRACK_NUMBER,
        Grl.METADATA_KEY_URL
    ]

    def __repr__(self):
        return "<GrlTrackerSource>"

    def __init__(
            self, source, _hash, model, albums_model, artists_model, coremodel,
            core_selection):
        super().__init__()

        self._coremodel = coremodel
        self._core_selection = core_selection
        self._source = source
        self._model = model
        self._albums_model = albums_model
        self._artists_model = artists_model
        self._hash = _hash
        # self._table = table
        # Only way to figure out removed items
        # self._url_table = url_hash

        Grl.init(None)

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self._full_options = Grl.OperationOptions()
        self._full_options.set_resolution_flags(
            Grl.ResolutionFlags.FULL | Grl.ResolutionFlags.IDLE_RELAY)

        self._initial_fill(self._source)
        self._initial_albums_fill(self._source)
        self._initial_artists_fill(self._source)

        self._source.connect("content-changed", self._on_content_changed)

    def _on_content_changed(self, source, medias, change_type, loc_unknown):
        for media in medias:
            if change_type == Grl.SourceChangeType.ADDED:
                self._add_media(media)
            if change_type == Grl.SourceChangeType.CHANGED:
                self._requery_media(media.get_id())
            if change_type == Grl.SourceChangeType.REMOVED:
                self.emit("media-removed", media)

    def _requery_media(self, grilo_id):
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

        self._source.query(
            query, self.METADATA_KEYS, options, self._update_media)

    def _add_media(self, media):
        song = CoreSong(media)
        self._model.append(song)
        self._requery_media(media.get_id())

    def _update_media(self, source, op_id, media, user_data, error):
        if error:
            print("ERROR", error)
            return

        if not media:
            print("NO MEDIA", source, op_id, media, error)
            return

        self._hash[media.get_id()].update(media)

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
            print("NO MEDIA", source, op_id, media, error)
            return

        song = CoreSong(media)
        self._model.append(song)
        self._hash[media.get_id()] = song

        song.connect("notify::selected", self._core_selection.blah)
        # self._url_table[media.get_url()] = song

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

    def _initial_artists_fill(self, source):
        query = """
        SELECT
            rdf:type(?artist_class)
            tracker:id(?artist_class) AS ?id
            nmm:artistName(?artist_class) AS ?artist
        {
            ?artist_class a nmm:Artist .
        }
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
            return

        artist = CoreArtist(media)
        self._artists_model.append(artist)

    def get_artist_albums(self, artist):
        artist_id = artist.props.media.get_id()
        print("ID", artist_id)

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

        albums = self._source.query_sync(query, self.METADATA_KEYS, options)

        print("ALBUMS", albums)

        return albums

    def get_album_disc_numbers(self, media):
        album_id = media.get_id()
        print("album id ", album_id)

        query = """
        SELECT DISTINCT
            rdf:type(?song)
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

        discs = self._source.query_sync(query, self.METADATA_KEYS, options)

        print("DISCS", discs)

        return discs

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
                     && nmm:setNumber(nmm:musicAlbumDisc(?song)) = %(disc_nr)s )
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
