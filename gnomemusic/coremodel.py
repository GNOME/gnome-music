import gi
gi.require_version('Dazzle', '1.0')
from gi.repository import Dazzle, GObject, Gio, Gfm
from gi._gi import pygobject_new_full

from gnomemusic import log
from gnomemusic.coreartist import CoreArtist
from gnomemusic.coregrilo import CoreGrilo
from gnomemusic.coresong import CoreSong
from gnomemusic.grilo import grilo
from gnomemusic.widgets.songwidget import SongWidget


class CoreDisc(GObject.GObject):
        media = None
        model = None


class CoreModel(GObject.GObject):

    __gsignals__ = {
        "playlist-loaded": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    @log
    def __init__(self):
        super().__init__()

        self._test = Gfm.FilterListModel()
        self._model = Gio.ListStore.new(CoreSong)
        self._album_model = Gio.ListStore()
        self._artist_model = Gio.ListStore.new(CoreArtist)

        self._playlist_model = Dazzle.ListModelFilter.new(self._model)
        self._playlist_model_sort = Gfm.SortListModel.new(self._playlist_model)

        self._album_store = None
        self._hash = {}
        self._url_hash = {}
        print("PLAYLIST_MODEL", self._playlist_model)
        self._grilo = CoreGrilo(
            self._model, self._hash, self._url_hash, self._album_model,
            self._artist_model)
        # self._grilo.connect("media-removed", self._on_media_removed)

    @log
    def get_model(self):
        return self._model

    def _wrap_list_store_sort_func(self, func):

        def wrap(a, b, *user_data):
            a = pygobject_new_full(a, False)
            b = pygobject_new_full(b, False)
            return func(a, b, *user_data)

        return wrap

    @log
    def get_album_model(self, media):
        discs = self._grilo.get_album_disc_numbers(media)

        disc_model = Gio.ListStore()
        disc_model_sort = Gfm.SortListModel.new(disc_model)

        def _disc_sort(song_a, song_b):
            return song_a.props.track_number - song_b.props.track_number

        for disc in discs:
            model_filter = Dazzle.ListModelFilter.new(self._model)
            model_filter.set_filter_func(lambda a: False)
            nr = disc.get_album_disc_number()
            self.get_album_disc(media, nr, model_filter)

            model_sort = Gfm.SortListModel.new(model_filter)
            model_sort.set_sort_func(
                self._wrap_list_store_sort_func(_disc_sort))

            coredisc = CoreDisc()
            coredisc.media = disc
            coredisc.model = model_sort

            disc_model.append(coredisc)

        def _disc_order_sort(disc_a, disc_b):
            return (disc_a.media.get_album_disc_number()
                    - disc_b.media.get_album_disc_number())

        disc_model_sort.set_sort_func(
            self._wrap_list_store_sort_func(_disc_order_sort))

        return disc_model_sort

    def get_playlist_model(self):
        return self._playlist_model_sort

    def set_playlist_model(self, type, album_media, coresong):
        song_ids = []

        def _filter_func(core_song):
            return core_song.props.media.get_id() in song_ids

        def _sort_func(song_a, song_b):
            sort_disc = (song_a.props.media.get_album_disc_number()
                          - song_b.props.media.get_album_disc_number())
            if sort_disc == 0:
                return song_a.props.track_number - song_b.props.track_number

            return sort_disc

        def _callback(source, dunno, media, something, something2):
            if media is None:
                self._playlist_model.set_filter_func(_filter_func)
                self._playlist_model_sort.set_sort_func(
                    self._wrap_list_store_sort_func(_sort_func))
                for song in self._playlist_model:
                    if song.props.media.get_id() == coresong.get_id():
                        song.props.state = SongWidget.State.PLAYING
                        break
                self.emit("playlist-loaded")
                return

            song_ids.append(media.get_id())

        self._grilo.populate_album_songs(album_media, _callback)


        # albums_ids = []

        # model_filter = Dazzle.ListModelFilter.new(self._model)
        # model_filter = Gfm.FilterListModel.new(self._model)
        # model_filter.set_filter_func(lambda a: False)
        # model_sort = Gfm.SortListModel.new_for_type(CoreSong)

        # def _filter_func(core_song):
        #     return core_song.props.media.get_id() in albums_ids

        # def _reverse_sort(song_a, song_b, data=None):
        #     return song_b.props.track_number - song_a.props.track_number

        # def _callback(source, dunno, media, something, something2):
        #     if media is None:
        #         model_filter.set_filter_func(_filter_func)
        #         model_sort.set_model(model_filter)
        #         model_sort.set_sort_func(
        #             self._wrap_list_store_sort_func(_reverse_sort))
        #         return

        #     albums_ids.append(media.get_id())

        # For POC sake, use old grilo
        # grilo.populate_album_songs(media, _callback)

        # return model_sort

    def get_album_disc(self, media, discnr, model):
        albums_ids = []
        model_filter = model

        def _filter_func(core_song):
            return core_song.props.media.get_id() in albums_ids

        def _reverse_sort(song_a, song_b, data=None):
            return song_a.props.track_number - song_b.props.track_number

        def _callback(source, dunno, media, something, something2):
            if media is None:
                model_filter.set_filter_func(_filter_func)
                # model_sort.set_model(model_filter)
                # model_sort.set_sort_func(
                #     self._wrap_list_store_sort_func(_reverse_sort))
                return

            albums_ids.append(media.get_id())

        # For POC sake, use old grilo
        self._grilo.populate_album_disc_songs(media, discnr, _callback)

        return model_filter

    @log
    def get_albums_model(self):
        return self._album_model

    def get_artists_model(self):
        return self._artist_model

    def get_artist_albums(self, artist):
        albums = self._grilo.get_artist_albums(artist)

        return albums

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
