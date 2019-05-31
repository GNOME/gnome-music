import gi
gi.require_version('Grl', '0.3')
from gi.repository import Grl, GObject

from gnomemusic import log
from gnomemusic.corealbum import CoreAlbum
from gnomemusic.coresong import CoreSong
from gnomemusic.grilowrappers.grltrackersource import GrlTrackerSource


class CoreGrilo(GObject.GObject):

    def __repr__(self):
        return "<CoreGrilo>"

    def __init__(self, model, _hash, url_hash, albums_model, artists_model):
        super().__init__()

        self._model = model
        self._albums_model = albums_model
        self._artists_model = artists_model
        self._hash = _hash
        # Only way to figure out removed items
        self._url_table = url_hash

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
            self._tracker_source = GrlTrackerSource(
                source, self._hash, self._model, self._albums_model,
                self._artists_model)
            self._tracker_source = source
            print(self._tracker_source, "added")

    def _on_source_removed(self, registry, source):
        print("removed,", source.props.source_id)
