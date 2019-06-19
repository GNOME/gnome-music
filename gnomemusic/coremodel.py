import gi
gi.require_version('Dazzle', '1.0')
from gi.repository import Dazzle, GObject, Gio, Gfm, Grl
from gi._gi import pygobject_new_full

from gnomemusic import log
from gnomemusic.coreartist import CoreArtist
from gnomemusic.coregrilo import CoreGrilo
from gnomemusic.coresong import CoreSong
from gnomemusic.grilo import grilo
from gnomemusic.player import PlayerPlaylist
from gnomemusic.widgets.songwidget import SongWidget

# The basic premisis is that an album (CoreArtistAlbum) consist of a
# number of discs (CoreDisc) which contain a number of songs
# (CoreSong). All discs are a filtered Gio.Listmodel of all the songs
# available in the master Gio.ListModel.
#
# CoreArtistAlbum and CoreDisc contain a Gio.ListModel of the child
# object.
#
# CoreArtistAlbum(s) => CoreDisc(s) => CoreSong(s)
#
# For the playlist model, the CoreArtist or CoreAlbum derived discs are
# flattened and recreated as a new model. This is to allow for multiple
# occurences of the same song: same grilo id, but unique object.

class CoreDisc(GObject.GObject):

    media = GObject.Property(type=Grl.Media, default=None)
    model = GObject.Property(type=Gio.ListModel, default=None)


class CoreArtistAlbum(GObject.GObject):

    media = GObject.Property(type=Grl.Media, default=None)
    model = GObject.Property(type=Gio.ListModel, default=None)


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

        self._playlist_model = Gio.ListStore.new(CoreSong)
        self._playlist_model_sort = Gfm.SortListModel.new(self._playlist_model)

        self._album_store = None
        self._hash = {}
        self._url_hash = {}
        print("PLAYLIST_MODEL", self._playlist_model)
        self._grilo = CoreGrilo(
            self._model, self._hash, self._url_hash, self._album_model,
            self._artist_model)

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
            self._get_album_disc(media, nr, model_filter)

            model_sort = Gfm.SortListModel.new(model_filter)
            model_sort.set_sort_func(
                self._wrap_list_store_sort_func(_disc_sort))

            coredisc = CoreDisc()
            coredisc.props.media = disc
            coredisc.props.model = model_sort

            disc_model.append(coredisc)

        def _disc_order_sort(disc_a, disc_b):
            return (disc_a.media.get_album_disc_number()
                    - disc_b.media.get_album_disc_number())

        disc_model_sort.set_sort_func(
            self._wrap_list_store_sort_func(_disc_order_sort))

        return disc_model_sort

    def get_artists_model_full(self, artist_media):
        albums = self._grilo.get_artist_albums(artist_media)

        albums_model = Gio.ListStore()
        albums_model_sort = Gfm.SortListModel.new(albums_model)

        for album in albums:
            album_model = self.get_album_model(album)

            artist_album = CoreArtistAlbum()
            artist_album.props.model = album_model
            artist_album.props.media = album

            albums_model.append(artist_album)

        return albums_model


    def get_playlist_model(self):
        return self._playlist_model_sort

    def set_playlist_model(self, playlist_type, album_media, coresong, model):
        with model.freeze_notify():

            if playlist_type == PlayerPlaylist.Type.ALBUM:
                self._playlist_model.remove_all()

                for disc in model:
                    for model_song in disc.model:
                        song = CoreSong(model_song.props.media)

                        self._playlist_model.append(song)
                        song.bind_property(
                            "state", model_song, "state",
                            GObject.BindingFlags.SYNC_CREATE)

                        media_id = model_song.props.media.get_id()

                        if song.props.media.get_id() == coresong.get_id():
                            song.props.state = SongWidget.State.PLAYING

                self.emit("playlist-loaded")
            elif playlist_type == PlayerPlaylist.Type.PLAYLIST:
                self._playlist_model.remove_all()

                for artist_album in model:
                    for disc in artist_album.model:
                        for model_song in disc.model:
                            song = CoreSong(model_song.props.media)

                            self._playlist_model.append(song)
                            song.bind_property(
                                "state", model_song, "state",
                                GObject.BindingFlags.SYNC_CREATE)

                            media_id = model_song.props.media.get_id()
                            if song.props.media.get_id() == coresong.get_id():
                                song.props.state = SongWidget.State.PLAYING

                self.emit("playlist-loaded")


    def _get_album_disc(self, media, discnr, model):
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
