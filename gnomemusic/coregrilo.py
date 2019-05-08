import gi
gi.require_version('Grl', '0.3')
from gi.repository import Grl, GObject


class CoreGrilo(GObject.GObject):

    def __repr__(self):
        return "<CoreGrilo>"

    def __init__(self):
        super().__init__()

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
            print(self._tracker_source, "added")

    def _on_source_removed(self, registry, source):
        print("removed", source.props.source_id)
