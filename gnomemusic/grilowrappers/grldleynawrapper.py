import gi
gi.require_versions({"Grl": "0.3"})
from gi.repository import Grl, GObject

from gnomemusic.corealbum import CoreAlbum
from gnomemusic.coreartist import CoreArtist
from gnomemusic.coredisc import CoreDisc
from gnomemusic.coresong import CoreSong


class GrlDleynaWrapper(GObject.GObject):
    """Wrapper for the Grilo Dleyna source.
    """
    _SPLICE_SIZE = 100
    METADATA_KEYS = [
        Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_ALBUM_ARTIST,
        Grl.METADATA_KEY_ARTIST,
        Grl.METADATA_KEY_CREATION_DATE,
        Grl.METADATA_KEY_COMPOSER,
        Grl.METADATA_KEY_DURATION,
        Grl.METADATA_KEY_ID,
        Grl.METADATA_KEY_PLAY_COUNT,
        Grl.METADATA_KEY_THUMBNAIL,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_TRACK_NUMBER,
        Grl.METADATA_KEY_URL
    ]

    def __init__(self, source, application):
        super().__init__()

        self._application = application
        self._coremodel = application.props.coremodel
        self._log = application.props.log
        self._songs_model = self._coremodel.props.songs
        self._source = source
        self._albums_model = self._coremodel.props.albums
        self._album_ids = {}
        self._artists_model = self._coremodel.props.artists
        self._artist_ids = {}
        self._hash = {}
        self._window = application.props.window

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self.props.source = source

        self._initial_songs_fill(self.props.source)
        self._initial_albums_fill(self.props.source)
        self._initial_artists_fill(self.props.source)

    @GObject.Property(type=Grl.Source, default=None)
    def source(self):
        return self._source

    def _initial_songs_fill(self, source):
        self._window.notifications_popup.push_loading()
        songs_added = []

        def _add_to_model(source, op_id, media, remaining, error):
            if error:
                self._log.warning("Error: {}".format(error))
                self._window.notifications_popup.pop_loading()
                return

            song = CoreSong(self._application, media)
            song.props.title = (
                song.props.title + " (" + source.props.source_name + ")")
            songs_added.append(song)
            self._hash[media.get_id()] = song
            if len(songs_added) == self._SPLICE_SIZE:
                self._songs_model.splice(
                    self._songs_model.get_n_items(), 0, songs_added)
                songs_added.clear()

            if remaining == 0:
                self._songs_model.splice(
                    self._songs_model.get_n_items(), 0, songs_added)
                self._window.notifications_popup.pop_loading()

                return

        query = """upnp:class derivedfrom 'object.item.audioItem'
        """.replace("\n", " ").strip()

        options = self._fast_options.copy()
        self._source.query(query, self.METADATA_KEYS, options, _add_to_model)

    def _initial_albums_fill(self, source):
        self._window.notifications_popup.push_loading()
        albums_added = []

        options = self._fast_options.copy()

        def _add_to_albums_model(source, op_id, media, remaining, error):
            if error:
                self._log.warning("Error: {}".format(error))
                self._window.notifications_popup.pop_loading()
                return

            album = CoreAlbum(self._application, media)

            def _get_album_url(source, op_id, media, remaining, error):
                if media:
                    album.props.url = media.get_url()

            album_name = media.get_title()
            url_query = """
                upnp:class derivedfrom 'object.item.audioItem.musicTrack'
                and (upnp:album contains '%(album_name)s')
            """.replace("\n", " ").strip() % {
                "album_name": album_name
            }

            source.query(
                url_query, self.METADATA_KEYS, options, _get_album_url)

            self._album_ids[media.get_id()] = album
            albums_added.append(album)
            if len(albums_added) == self._SPLICE_SIZE:
                self._albums_model.splice(
                    self._albums_model.get_n_items(), 0, albums_added)
                albums_added.clear()

            if remaining == 0:
                self._albums_model.splice(
                    self._albums_model.get_n_items(), 0, albums_added)
                self._window.notifications_popup.pop_loading()

        query = """upnp:class = 'object.container.album.musicAlbum'
        """.replace("\n", " ").strip()

        source.query(query, self.METADATA_KEYS, options, _add_to_albums_model)

    def _initial_artists_fill(self, source):
        self._window.notifications_popup.push_loading()
        artists_added = []

        def _add_to_artists_model(source, op_id, media, remaining, error):
            if error:
                self._log.warning("Error: {}".format(error))
                self._window.notifications_popup.pop_loading()
                return

            artist = CoreArtist(self._application, media)
            self._artist_ids[media.get_id()] = artist
            artists_added.append(artist)
            if len(artists_added) == self._SPLICE_SIZE:
                self._artists_model.splice(
                    self._artists_model.get_n_items(), 0, artists_added)
                artists_added.clear()

            if remaining == 0:
                self._artists_model.splice(
                    self._artists_model.get_n_items(), 0, artists_added)
                self._window.notifications_popup.pop_loading()

        query = """upnp:class = 'object.container.person.musicArtist'
        """.replace("\n", " ").strip()

        options = self._fast_options.copy()

        source.query(
            query, self.METADATA_KEYS, options, _add_to_artists_model)

    def get_album_discs(self, media, disc_model):
        disc_nr = 1
        coredisc = CoreDisc(self._application, media, disc_nr)
        disc_model.append(coredisc)

    def populate_album_disc_songs(self, media, disc_nr, callback):
        album_name = media.get_title()

        query = """
            upnp:class derivedfrom 'object.item.audioItem.musicTrack'
            and (upnp:album contains '%(album_name)s')
        """.replace("\n", " ").strip() % {
            "album_name": album_name
        }
        options = self._fast_options.copy()

        self.props.source.query(query, self.METADATA_KEYS, options, callback)

    def get_artist_albums(self, coreartist, model):
        self._window.notifications_popup.push_loading()
        artist_name = coreartist.get_title()

        query = """
            upnp:artist = '%(artist_name)s'
            derviedfrom (upnp:class = 'object.container.person.musicArtist')
        """.replace("\n", " ").strip() % {
            "artist_name": artist_name
        }

        albums = []

        def query_cb(source, op_id, media, remaining, error):
            if error:
                self._log.warning("Error: {}".format(error))
                self._window.notifications_popup.pop_loading()
                return

            if media.get_album() not in albums:
                albums.append(media.get_album())

            if remaining == 0:
                model.set_filter_func(albums_filter, albums)
                self._window.notifications_popup.pop_loading()
                return

        def albums_filter(corealbum, albums):
            for media in albums:
                if (media == corealbum.props.title
                        and corealbum.props.source
                        == self._source.props.source_id):
                    return True

            return False

        options = self._fast_options.copy()
        self.props.source.query(
            query, self.METADATA_KEYS, options, query_cb)

    def search(self, text):
        pass
