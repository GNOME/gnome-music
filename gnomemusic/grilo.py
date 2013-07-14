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
        self.registry = Grl.Registry.get_default()
        try:
            self.registry.load_all_plugins()
        except GLib.GError:
            print('Failed to load plugins.')

        self.sources = {}
        self.tracker = None

        self.registry.connect('source_added', self._onSourceAdded)
        self.registry.connect('source_removed', self._onSourceRemoved)

    def _onSourceAdded(self, pluginRegistry, mediaSource):
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

    def _onSourceRemoved(self):
        print('source removed')

    def populateArtists(self, offset, callback):
        self.populateItems(Query.artist, offset, callback)

    def populateAlbums(self, offset, callback, count=50):
        self.populateItems(Query.album, offset, callback, count)

    def populateSongs(self, offset, callback):
        self.populateItems(Query.songs, offset, callback)

    def populateItems(self, query, offset, callback, count=50):
        options = Grl.OperationOptions(None)
        options.set_flags(Grl.ResolutionFlags.FULL |
                          Grl.ResolutionFlags.IDLE_RELAY)
        options.set_skip(offset)
        options.set_count(count)
        self.tracker.query(query, self.METADATA_KEYS, options, callback)

    def getAlbumSongs(self, album_id, callback):
        query = Query.album_songs(album_id)
        options = Grl.OperationOptions(None)
        options.set_flags(Grl.ResolutionFlags.FULL |
                          Grl.ResolutionFlags.IDLE_RELAY)
        self.tracker.query(query, self.METADATA_KEYS, options, callback)

    def _searchCallback(self):
        print("yeah")

    def search(self, q):
        for source in self.sources:
            print(source.get_name() + " - " + q)
            source.search(q, [Grl.METADATA_KEY_ID], 0, 10,
                          Grl.MetadataResolutionFlags.FULL |
                          Grl.MetadataResolutionFlags.IDLE_RELAY,
                          self._searchCallback, source)


Grl.init(None)

grilo = Grilo()
