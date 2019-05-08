import gi
gi.require_version('Grl', '0.3')
from gi.repository import Grl, GObject


class CoreGrilo(GObject.GObject):

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
        return "<CoreGrilo>"

    def __init__(self, model, table):
        super().__init__()

        self._model = model
        self._table = table

        Grl.init(None)

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self._full_options = Grl.OperationOptions()
        self._full_options.set_resolution_flags(
            Grl.ResolutionFlags.FULL | Grl.ResolutionFlags.IDLE_RELAY)

        self._registry = Grl.Registry.get_default()
        self._registry.connect('source-added', self._on_source_added)
        self._registry.connect('source-removed', self._on_source_removed)

    def _on_source_added(self, registry, source):
        print(source.props.source_id)
        if source.props.source_id == "grl-tracker-source":
            self._tracker_source = source
            self._tracker_initial_fill(source)
            print(self._tracker_source, "added")

    def _on_source_removed(self, registry, source):
        print("removed", source.props.source_id)

    def _tracker_initial_fill(self, source):
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
            WHERE { ?song a nmm:MusicPiece . }
        """.replace('\n', ' ').strip()

        print(query)

        options = self._fast_options.copy()

        self._tracker_source.query(
            query, self.METADATA_KEYS, options, self._add_to_model)

    def _add_to_model(self, source, op_id, media, user_data, error):
        if error:
            print("ERROR", error)
            return

        if not media:
            print("NO MEDIA", source, op_id, media, error)
            return

        self._model.append(media)
        self._table[media.get_id()] = media

        # print(media.get_url(), media.get_title())
