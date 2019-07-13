import gi
gi.require_versions({"Grl": "0.3"})
from gi.repository import Gfm, Gio, Grl, GObject

from gnomemusic.coresong import CoreSong


class GrlSearchWrapper(GObject.GObject):

    METADATA_KEYS = [
        Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_ALBUM_ARTIST,
        Grl.METADATA_KEY_ALBUM_DISC_NUMBER,
        Grl.METADATA_KEY_ARTIST,
        Grl.METADATA_KEY_CREATION_DATE,
        Grl.METADATA_KEY_COMPOSER,
        Grl.METADATA_KEY_DURATION,
        Grl.METADATA_KEY_FAVOURITE,
        Grl.METADATA_KEY_ID,
        Grl.METADATA_KEY_PLAY_COUNT,
        Grl.METADATA_KEY_THUMBNAIL,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_TRACK_NUMBER,
        Grl.METADATA_KEY_URL
    ]

    def __repr__(self):
        return "<GrlSearchWrapper>"

    def __init__(self, source, coremodel, coreselection, grilo):
        super().__init__()

        self._coremodel = coremodel
        self._coreselection = coreselection
        self._grilo = grilo
        self._source = source

        self._song_search_proxy = self._coremodel.props.songs_search_proxy

        self._song_search_store = Gio.ListStore.new(CoreSong)
        # FIXME: Workaround for adding the right list type to the proxy
        # list model.
        self._song_search_model = Gfm.FilterListModel.new(
            self._song_search_store)
        self._song_search_model.set_filter_func(lambda a: True)
        self._song_search_proxy.append(self._song_search_model)

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_count(25)
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

    def search(self, text):
        with self._song_search_store.freeze_notify():
            self._song_search_store.remove_all()

        def _search_result_cb(source, op_id, media, remaining, error):
            if error:
                print("error")
                return
            if media is None:
                return

            coresong = CoreSong(media, self._coreselection, self._grilo)
            coresong.props.title = (
                coresong.props.title + " (" + source.props.source_id + ")")

            self._song_search_store.append(coresong)

        self._source.search(
            text, self.METADATA_KEYS, self._fast_options, _search_result_cb)
