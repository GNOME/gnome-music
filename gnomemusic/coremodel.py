from gi.repository import GObject, Gio

from gnomemusic import log
from gnomemusic.coregrilo import CoreGrilo


class CoreModel(GObject.GObject):

    @log
    def __init__(self):
        super().__init__()

        self._model = Gio.ListStore()
        self._hash = {}

        self._grilo = CoreGrilo(self._model, self._hash)

    @log
    def get_model(self):
        return self._model
