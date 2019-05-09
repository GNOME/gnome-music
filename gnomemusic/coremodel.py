import gi
gi.require_version('Dazzle', '1.0')
from gi.repository import Dazzle, GObject, Gio

from gnomemusic import log
from gnomemusic.coregrilo import CoreGrilo
from gnomemusic.grilo import grilo


class CoreModel(GObject.GObject):

    @log
    def __init__(self):
        super().__init__()

        self._model = Gio.ListStore()
        self._album_store = None
        self._hash = {}
        self._url_hash = {}

        self._grilo = CoreGrilo(self._model, self._hash, self._url_hash)
        self._grilo.connect("media-removed", self._on_media_removed)

    @log
    def get_model(self):
        return self._model

    @log
    def get_album_model(self, media):
        albums_ids = []

        model_filter = Dazzle.ListModelFilter.new(self._model)
        model_filter.set_filter_func(lambda a: False)

        def _filter_func(core_song):
            return core_song.props.media.get_id() in albums_ids

        def _reverse_sort(song_a, song_b):
            return song_b.props.track_number - song_a.props.track_number

        def _callback(source, dunno, media, something, something2):
            if media is None:
                model_filter.set_filter_func(_filter_func)
                return

            albums_ids.append(media.get_id())

        # For POC sake, use old grilo
        grilo.populate_album_songs(media, _callback)

        return model_filter

    @log
    def _on_media_removed(self, klass, media):
        try:
            old_song = self._url_hash[media.get_url()]
            print("SUCCES")
        except KeyError:
            print("KeyError", media.get_url())
            return

        for i in range(self._model.get_n_items()):
            if old_song == self._model[i]:
                print("REMOVING index", i)
                self._model.remove(i)
                break

        if self._album_store is not None:
            for i in range(self._album_store.get_n_items()):
                if old_song == self._album_store[i]:
                    print("REMOVING index", i)
                    self._album_store.remove(i)
                    break
        
        print("pop2", self._url_hash.pop(media.get_url()))
        print("pop1", self._hash.pop(old_song.props.media.get_id()))

                # print("ITEM IN MODEL", media.get_id(), self._url_hash[media.get_url()]._media.get_id())
