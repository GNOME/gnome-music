from gi.repository import Grl, GLib, GObject

from gnomemusic.query import Query


class Grilo(GObject.GObject):

    __gsignals__ = {
        'ready': (GObject.SIGNAL_RUN_FIRST, None, ())
    }

    METADATA_KEYS = [
        Grl.METADATA_KEY_ID, Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_ARTIST, Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_DURATION, Grl.METADATA_KEY_THUMBNAIL,
        Grl.METADATA_KEY_CREATION_DATE]

    def __init__(self):
        GObject.GObject.__init__(self)

        self.options = Grl.OperationOptions()
        self.options.set_flags(Grl.ResolutionFlags.FULL |
                               Grl.ResolutionFlags.IDLE_RELAY)

        self.registry = Grl.Registry.get_default()
        try:
            self.registry.load_all_plugins()
        except GLib.GError:
            print('Failed to load plugins.')

        self.sources = {}
        self.tracker = None

        self.registry.connect('source_added', self._on_source_added)
        self.registry.connect('source_removed', self._on_source_removed)

    def _on_source_added(self, pluginRegistry, mediaSource):
        id = mediaSource.get_id()
        if id == "grl-tracker-source":
            ops = mediaSource.supported_operations()
            if ops & Grl.SupportedOps.SEARCH:
                print('Detected new source availabe: \'' +
                      mediaSource.get_name() + '\' and it supports search')

                self.sources[id] = mediaSource
                self.tracker = mediaSource

                if self.tracker is not None:
                    self.emit('ready')

    def _on_source_removed(self, pluginRegistry, mediaSource):
        print('source removed')

    def populate_artists(self, offset, callback):
        self.populate_items(Query.ARTISTS, offset, callback)

    def populate_albums(self, offset, callback, count=50):
        self.populate_items(Query.ALBUMS, offset, callback, count)

    def populate_songs(self, offset, callback, count=50):
        self.populate_items(Query.SONGS, offset, callback)

    def populate_album_songs(self, album_id, callback):
        self.populate_items(Query.album_songs(album_id), 0, callback)

    def populate_items(self, query, offset, callback, count=50):
        options = self.options.copy()
        options.set_skip(offset)
        options.set_count(count)

        def _callback(source, param, item, count, data, offset):
            callback(source, param, item)
        self.tracker.query(query, self.METADATA_KEYS, options, _callback, None)

    def _search_callback(self):
        print("yeah")

    def search(self, q):
        options = self.options.copy()
        for source in self.sources:
            print(source.get_name() + " - " + q)
            source.search(q, [Grl.METADATA_KEY_ID], 0, 10,
                          options, self._search_callback, source)


Grl.init(None)

grilo = Grilo()
