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
        self._wrappers = []

        Grl.init(None)

        self._registry = Grl.Registry.get_default()
        self._registry.connect('source-added', self._on_source_added)
        self._registry.connect('source-removed', self._on_source_removed)

    def _on_source_added(self, registry, source):
        new_wrapper = None

        if source.props.source_id == "grl-tracker-source":
            new_wrapper = GrlTrackerSource(
                source, self._coremodel, self._coreselection, self)
            self._wrappers.append(new_wrapper)
        # elif source.props.source_id[:10] == "grl-dleyna":
        #     new_wrapper = GrlDLeynaSource(
        #         source, self._coremodel, self._coreselection, self)
        #     self._wrappers.append(new_wrapper)
        print(new_wrapper, "added")

    def _on_source_removed(self, registry, source):
        # FIXME: Handle removing sources.
        print("removed,", source.props.source_id)

    def get_artist_albums(self, artist, filter_model):
        for wrapper in self._wrappers:
            wrapper.get_artist_albums(artist, filter_model)

    def get_album_discs(self, media, disc_model):
        for wrapper in self._wrappers:
            wrapper.get_album_discs(media, disc_model)

    def populate_album_disc_songs(self, media, discnr, callback):
        for wrapper in self._wrappers:
            wrapper.populate_album_disc_songs(media, discnr, callback)

    def populate_album_songs(self, media, callback):
        for wrapper in self._wrappers:
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
        for wrapper in self._wrappers:
            if media.get_source() == wrapper.source.props.source_id:
                GLib.idle_add(
                    self._store_metadata, wrapper.props.source, media, key)
                break

    def search(self, text):
        for wrapper in self._wrappers:
            wrapper.search(text)

    def stage_playlist_deletion(self, playlist):
        """Prepares playlist deletion.

        :param Playlist playlist: playlist
        """
        for wrapper in self._wrappers:
            if wrapper.source.props.source_id == "grl-tracker-source":
                wrapper.stage_playlist_deletion(playlist)
                break

    def finish_playlist_deletion(self, playlist, deleted):
        """Finishes playlist deletion.

        :param Playlist playlist: playlist
        :param bool deleted: indicates if the playlist has been deleted
        """
        for wrapper in self._wrappers:
            if wrapper.source.props.source_id == "grl-tracker-source":
                wrapper.finish_playlist_deletion(playlist, deleted)
                break

    def create_playlist(self, playlist_title, callback):
        """Creates a new user playlist.

        :param str playlist_title: playlist title
        :param callback: function to perform once, the playlist is created
        """
        for wrapper in self._wrappers:
            if wrapper.source.props.source_id == "grl-tracker-source":
                wrapper.create_playlist(playlist_title, callback)
                break
