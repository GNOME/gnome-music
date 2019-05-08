from gi.repository import GObject, Gio

from gnomemusic import log
from gnomemusic.coregrilo import CoreGrilo
from gnomemusic.grilo import grilo


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

    @log
    def get_album_model(self, media):
        store = Gio.ListStore()
        album_id = media.get_id()

        def _callback(source, dunno, media, something, something2):
            if media is None:
                return
            print("media", media)

            song = self._hash[media.get_id()]
            store.append(song)

        # For POC sake, use old grilo
        grilo.populate_album_songs(media, _callback)

        return store
