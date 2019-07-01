import gi
gi.require_version('Grl', '0.3')
from gi.repository import Gio, Grl, GObject

from gnomemusic import log
import gnomemusic.utils as utils


class CoreArtist(GObject.GObject):
    """Exposes a Grl.Media with relevant data as properties
    """

    artist = GObject.Property(type=str)
    media = GObject.Property(type=Grl.Media)

    @log
    def __init__(self, media, coremodel):
        super().__init__()

        self._coremodel = coremodel
        self._model = None
        self._selected = False

        self.update(media)

    @log
    def update(self, media):
        self.props.media = media
        self.props.artist = utils.get_artist_name(media)

    @GObject.Property(type=Gio.ListModel, default=None)
    def model(self):
        if self._model is None:
            self._model = self._coremodel.get_artist_album_model(
                self.props.media)
            self._model.connect("items-changed", self._on_items_changed)

        self._on_items_changed(self._model, None, None, None)

        return self._model

    def _on_items_changed(self, model, pos, removed, added):
        with self.freeze_notify():
            for corealbum in self._model:
                corealbum.props.selected = self.props.selected

    @GObject.Property(type=bool, default=False)
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        self._selected = value

        # The model is loaded on-demand, so the first time the model is
        # returned it can still be empty. This is problem for returning
        # a selection. Trigger loading of the model here if a selection
        # is requested, it will trigger the filled model update as
        # well.
        self.props.model
