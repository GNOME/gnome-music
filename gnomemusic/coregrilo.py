import gi
gi.require_version('Grl', '0.3')
from gi.repository import Grl, GLib, GObject

# from gnomemusic.grilowrappers.grldleynasource import GrlDLeynaSource
from gnomemusic.grilowrappers.grltrackersource import GrlTrackerSource


class CoreGrilo(GObject.GObject):

    def __repr__(self):
        return "<CoreGrilo>"

    def __init__(self, coremodel, coreselection):
        super().__init__()

        self._coremodel = coremodel
        self._coreselection = coreselection
        self._search_sources = {}
        self._wrappers = {}

        Grl.init(None)

        self._registry = Grl.Registry.get_default()
        self._registry.connect('source-added', self._on_source_added)
        self._registry.connect('source-removed', self._on_source_removed)

        self._registry.load_all_plugins(False)

    def _on_source_added(self, registry, source):
        new_wrapper = None

        if (source.props.source_id == "grl-tracker-source"
                and source.props.source_id not in self._wrappers.keys()):
            new_wrapper = GrlTrackerSource(
                source, self._coremodel, self._coreselection, self)
            self._wrappers[source.props.source_id] = new_wrapper
        # elif source.props.source_id[:10] == "grl-dleyna":
        #     new_wrapper = GrlDLeynaSource(
        #         source, self._coremodel, self._coreselection, self)
        #     self._wrappers.append(new_wrapper)
            print("wrapper", new_wrapper)
        elif (source.supported_operations() & Grl.SupportedOps.SEARCH
                and source.get_supported_media() & Grl.MediaType.AUDIO
                and source.props.source_id not in self._search_sources.keys()):
            self._search_sources[source.props.source_id] = source
            print("search source", source)

    def _on_source_removed(self, registry, source):
        # FIXME: Handle removing sources.
        print("removed,", source.props.source_id)

        # FIXME: Only removes search sources atm.
        self._search_sources.pop(source.props.source_id, None)

    def get_artist_albums(self, artist, filter_model):
        for wrapper in self._wrappers.values():
            wrapper.get_artist_albums(artist, filter_model)

    def get_album_discs(self, media, disc_model):
        for wrapper in self._wrappers.values():
            wrapper.get_album_discs(media, disc_model)

    def populate_album_disc_songs(self, media, discnr, callback):
        for wrapper in self._wrappers.values():
            wrapper.populate_album_disc_songs(media, discnr, callback)

    def populate_album_songs(self, media, callback):
        for wrapper in self._wrappers.values():
            wrapper.populate_album_songs(media, callback)

    def _store_metadata(self, source, media, key):
        """Convenience function to store metadata

        Wrap the metadata store call in a idle_add compatible form.
        :param source: A Grilo source object
        :param media: A Grilo media item
        :param key: A Grilo metadata key
        """
        # FIXME: Doing this async crashes.
        try:
            source.store_metadata_sync(
                media, [key], Grl.WriteFlags.NORMAL)
        except GLib.Error as error:
            # FIXME: Do not print.
            print("Error {}: {}".format(error.domain, error.message))

        return GLib.SOURCE_REMOVE

    def writeback(self, media, key):
        for wrapper in self._wrappers.values():
            if media.get_source() == wrapper.source.props.source_id:
                GLib.idle_add(
                    self._store_metadata, wrapper.props.source, media, key)
                break

    def search(self, text):
        for wrapper in self._wrappers.values():
            wrapper.search(text)
