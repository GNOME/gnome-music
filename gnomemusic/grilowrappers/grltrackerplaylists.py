import time

from gettext import gettext as _

import gi
gi.require_versions({"Grl": "0.3", 'Tracker': "2.0"})
from gi.repository import Gio, Grl, GLib, GObject

from gnomemusic.coresong import CoreSong
import gnomemusic.utils as utils


class GrlTrackerPlaylists(GObject.GObject):

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
        return "<GrlTrackerPlaylists>"

    def __init__(self, source, coremodel, coreselection, grilo):
        super().__init__()

        self._coremodel = coremodel
        self._coreselection = coreselection
        self._grilo = grilo
        self._source = source
        self._model = self._coremodel.props.playlists

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self._initial_playlists_fill()

    def _initial_playlists_fill(self):
        args = {
            "source": self._source,
            "coreselection": self._coreselection,
            "grilo": self._grilo
        }

        smart_playlists = {
            "MostPlayed": MostPlayed(**args),
            "NeverPlayed": NeverPlayed(**args),
            "RecentlyPlayed": RecentlyPlayed(**args),
            "RecentlyAdded": RecentlyAdded(**args),
            "Favorites": Favorites(**args)
        }

        for playlist in smart_playlists.values():
            self._model.append(playlist)

        query = """
        SELECT DISTINCT
            rdf:type(?playlist)
            tracker:id(?playlist) AS ?id
            nie:title(?playlist) AS ?title
            tracker:added(?playlist) AS ?creation_date
            nfo:entryCounter(?playlist) AS ?childcount
        WHERE
        {
            ?playlist a nmm:Playlist .
            OPTIONAL { ?playlist nie:url ?url;
                       tracker:available ?available . }
            FILTER ( !STRENDS(LCASE(?url), '.m3u')
                     && !STRENDS(LCASE(?url), '.m3u8')
                     && !STRENDS(LCASE(?url), '.pls')
                     || !BOUND(nfo:belongsToContainer(?playlist)) )
            FILTER ( !BOUND(?tag) )
            OPTIONAL { ?playlist nao:hasTag ?tag }
        }
        """.replace('\n', ' ').strip()

        options = self._fast_options.copy()

        self._source.query(
            query, self.METADATA_KEYS, options, self._add_user_playlist)

    def _add_user_playlist(self, source, param, media, data, error):
        if error:
            print("ERROR", error)
            return
        if not media:
            return

        playlist = Playlist(
            media=media, source=self._source, coremodel=self._coremodel,
            coreselection=self._coreselection, grilo=self._grilo)

        self._model.append(playlist)


class Playlist(GObject.GObject):
    """ Base class of all playlists """

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

    count = GObject.Property(type=int, default=0)
    creation_date = GObject.Property(type=GLib.DateTime, default=None)
    is_smart = GObject.Property(type=bool, default=False)
    pl_id = GObject.Property(type=str, default=None)
    query = GObject.Property(type=str, default=None)
    tag_text = GObject.Property(type=str, default=None)
    title = GObject.Property(type=str, default=None)

    def __repr__(self):
        return "<Playlist>"

    def __init__(
            self, media=None, query=None, tag_text=None, source=None,
            coremodel=None, coreselection=None, grilo=None):
        super().__init__()

        if media:
            self.props.pl_id = media.get_id()
            self.props.title = utils.get_media_title(media)
            self.props.creation_date = media.get_creation_date()

        self.props.query = query
        self.props.tag_text = tag_text
        self._model = None
        self._source = source
        self._coremodel = coremodel
        self._coreselection = coreselection
        self._grilo = grilo

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

    @GObject.Property(type=Gio.ListStore, default=None)
    def model(self):
        if self._model is None:
            self._model = Gio.ListStore()

            self._populate_model()

        return self._model

    @model.setter
    def model(self, value):
        self._model = value

    def _populate_model(self):
        query = """
        SELECT
            rdf:type(?song)
            ?song AS ?tracker_urn
            tracker:id(?entry) AS ?id
            nie:url(?song) AS ?url
            nie:title(?song) AS ?title
            nmm:artistName(nmm:performer(?song)) AS ?artist
            nie:title(nmm:musicAlbum(?song)) AS ?album
            nfo:duration(?song) AS ?duration
            ?tag AS ?favourite
            nie:contentAccessed(?song) AS ?last_played_time
            nie:usageCounter(?song) AS ?play_count
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
                NOT EXISTS { ?song a nmm:Video }
                && NOT EXISTS { ?song a nmm:Playlist }
            )
        }
        ORDER BY nfo:listPosition(?entry)
        """.replace('\n', ' ').strip() % {
            'filter_clause': 'tracker:id(?playlist) = ' + self.props.pl_id
        }

        def _add_to_playlist_cb(
                source, op_id, media, remaining, user_data, error):
            if not media:
                self.props.count = self._model.get_n_items()
                return

            coresong = CoreSong(media, self._coreselection, self._grilo)
            self._model.append(coresong)

        options = Grl.OperationOptions()
        options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self._source.query(
            query, self.METADATA_KEYS, options, _add_to_playlist_cb, None)


class SmartPlaylist(Playlist):
    """Base class for smart playlists"""

    def __repr__(self):
        return "<SmartPlaylist>"

    def __init__(self, **args):
        super().__init__(**args)

        self.props.is_smart = True

    @GObject.Property(type=Gio.ListStore, default=None)
    def model(self):
        if self._model is None:
            self._model = Gio.ListStore.new(CoreSong)

            def _add_to_model(source, op_id, media, remaining, error):
                if error:
                    print("ERROR", error)
                    return

                if not media:
                    self.props.count = self._model.get_n_items()
                    return

                coresong = CoreSong(media, self._coreselection, self._grilo)
                self._model.append(coresong)

            options = self._fast_options.copy()

            self._source.query(
                self.props.query, self.METADATA_KEYS, options, _add_to_model)

        return self._model


class MostPlayed(SmartPlaylist):
    """Most Played smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "MOST_PLAYED"
        # TRANSLATORS: this is a playlist name
        self.props.title = _("Most Played")
        self.props.query = """
        SELECT
            rdf:type(?song)
            tracker:id(?song) AS ?id
            ?song AS ?tracker_urn
            nie:title(?song) AS ?title
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
            ?song a nmm:MusicPiece ;
                    nie:usageCounter ?count .
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        }
        ORDER BY DESC(?count) LIMIT 50
        """.replace('\n', ' ').strip()


class NeverPlayed(SmartPlaylist):
    """Never Played smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "NEVER_PLAYED"
        # TRANSLATORS: this is a playlist name
        self.props.title = _("Never Played")
        self.props.query = """
        SELECT
            rdf:type(?song)
            tracker:id(?song) AS ?id
            ?song AS ?tracker_urn
            nie:title(?song) AS ?title
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
            ?song a nmm:MusicPiece ;
            FILTER ( NOT EXISTS { ?song nie:usageCounter ?count .} )
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        } ORDER BY nfo:fileLastAccessed(?song) LIMIT 50
        """.replace('\n', ' ').strip()


class RecentlyPlayed(SmartPlaylist):
    """Recently Played smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "RECENTLY_PLAYED"
        # TRANSLATORS: this is a playlist name
        self.props.title = _("Recently Played")

        sparql_midnight_dateTime_format = "%Y-%m-%dT00:00:00Z"
        days_difference = 7
        seconds_difference = days_difference * 86400
        compare_date = time.strftime(
            sparql_midnight_dateTime_format,
            time.gmtime(time.time() - seconds_difference))
        self.props.query = """
        SELECT
            rdf:type(?song)
            tracker:id(?song) AS ?id
            ?song AS ?tracker_urn
            nie:title(?song) AS ?title
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
            ?song a nmm:MusicPiece ;
                    nie:contentAccessed ?last_played .
            FILTER ( ?last_played > '%(compare_date)s'^^xsd:dateTime
                     && EXISTS { ?song nie:usageCounter ?count .} )
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        } ORDER BY DESC(?last_played) LIMIT 50
        """.replace('\n', ' ').strip() % {
            'compare_date': compare_date
        }


class RecentlyAdded(SmartPlaylist):
    """Recently Added smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "RECENTLY_ADDED"
        # TRANSLATORS: this is a playlist name
        self.props.title = _("Recently Added")

        sparql_midnight_dateTime_format = "%Y-%m-%dT00:00:00Z"
        days_difference = 7
        seconds_difference = days_difference * 86400
        compare_date = time.strftime(
            sparql_midnight_dateTime_format,
            time.gmtime(time.time() - seconds_difference))
        self.props.query = """
        SELECT
            rdf:type(?song)
            tracker:id(?song) AS ?id
            ?song AS ?tracker_urn
            nie:title(?song) AS ?title
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
            ?song a nmm:MusicPiece ;
                    tracker:added ?added .
            FILTER ( tracker:added(?song) > '%(compare_date)s'^^xsd:dateTime )
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }
        } ORDER BY DESC(tracker:added(?song)) LIMIT 50
        """.replace('\n', ' ').strip() % {
            'compare_date': compare_date,
        }


class Favorites(SmartPlaylist):
    """Favorites smart playlist"""

    def __init__(self, **args):
        super().__init__(**args)

        self.props.tag_text = "FAVORITES"
        # TRANSLATORS: this is a playlist name
        self.props.title = _("Favorite Songs")
        self.props.query = """
            SELECT
                rdf:type(?song)
                tracker:id(?song) AS ?id
                ?song AS ?tracker_urn
                nie:title(?song) AS ?title
                nie:url(?song) AS ?url
                nie:title(?song) AS ?title
                nmm:artistName(nmm:performer(?song)) AS ?artist
                nie:title(nmm:musicAlbum(?song)) AS ?album
                nfo:duration(?song) AS ?duration
                nie:usageCounter(?song) AS ?play_count
                nmm:trackNumber(?song) AS ?track_number
                nmm:setNumber(nmm:musicAlbumDisc(?song)) AS ?album_disc_number
                nao:predefined-tag-favorite AS ?favourite
            WHERE {
                ?song a nmm:MusicPiece ;
                        nie:isStoredAs ?as ;
                        nao:hasTag nao:predefined-tag-favorite .
                ?as nie:url ?url .
            OPTIONAL { ?song nao:hasTag ?tag .
                       FILTER (?tag = nao:predefined-tag-favorite) }

            } ORDER BY DESC(tracker:added(?song))
        """.replace('\n', ' ').strip()
