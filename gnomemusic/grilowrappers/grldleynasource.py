import gi
gi.require_version('Grl', '0.3')
from gi.repository import Grl, GObject

from gnomemusic.corealbum import CoreAlbum
from gnomemusic.coreartist import CoreArtist
from gnomemusic.coresong import CoreSong


class GrlDLeynaSource(GObject.GObject):

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
        return "<GrlDLeynaSource>"

    def __init__(
            self, source, _hash, model, albums_model, artists_model, coremodel,
            core_selection):
        super().__init__()

        self._coremodel = coremodel
        self._core_selection = core_selection
        self._source = source
        self._model = model
        self._albums_model = albums_model
        self._album_ids = {}
        self._artists_model = artists_model
        self._hash = _hash

        Grl.init(None)

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self._full_options = Grl.OperationOptions()
        self._full_options.set_resolution_flags(
            Grl.ResolutionFlags.FULL | Grl.ResolutionFlags.IDLE_RELAY)

        # self._initial_fill(self._source)
        # self._initial_albums_fill(self._source)
        self._initial_artists_fill(self._source)

        # self._source.connect("content-changed", self._on_content_changed)

    def _initial_artists_fill(self, source):
        query = """
        upnp:class derivedfrom 'object.container.person.musicArtist'
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

        artist = CoreArtist(media, self._coremodel)
        artist.props.artist = media.get_title() + " (upnp)"
        self._artists_model.append(artist)
        print(
            "ADDING DLNA ARTIST", media.get_title(), media.get_artist(),
            media.get_id())
