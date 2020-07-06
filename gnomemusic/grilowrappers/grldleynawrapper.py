import gi
gi.require_version("Grl", "0.3")
from gi.repository import Gio, Grl, GObject

from gnomemusic.coresong import CoreSong


class GrlDleynaWrapper(GObject.GObject):
    """Wrapper for the Grilo Dleyna source.
    """
    _SPLICE_SIZE = 100
    METADATA_KEYS = [
        Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_ALBUM_ARTIST,
        Grl.METADATA_KEY_ARTIST,
        Grl.METADATA_KEY_CREATION_DATE,
        Grl.METADATA_KEY_COMPOSER,
        Grl.METADATA_KEY_DURATION,
        Grl.METADATA_KEY_ID,
        Grl.METADATA_KEY_PLAY_COUNT,
        Grl.METADATA_KEY_THUMBNAIL,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_TRACK_NUMBER,
        Grl.METADATA_KEY_URL
    ]

    def __init__(self, source, application):
        super().__init__()

        self._application = application
        coremodel = application.props.coremodel
        self._log = application.props.log
        self._songs_model = Gio.ListStore.new(CoreSong)
        coremodel.props.songs_proxy.append(self._songs_model)
        self._source = source
        self._hash = {}
        self._window = application.props.window

        self._fast_options = Grl.OperationOptions()
        self._fast_options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY | Grl.ResolutionFlags.IDLE_RELAY)

        self.props.source = source

        self._initial_songs_fill()

    @GObject.Property(type=Grl.Source, default=None)
    def source(self):
        return self._source

    def _initial_songs_fill(self):
        self._window.notifications_popup.push_loading()
        songs_added = []

        def _add_to_model(source, op_id, media, remaining, error):
            if error:
                self._log.warning("Error: {}".format(error))
                self._window.notifications_popup.pop_loading()
                return

            song = CoreSong(self._application, media)
            song.props.title = (
                song.props.title + " (" + self._source.props.source_name + ")")
            songs_added.append(song)
            self._hash[media.get_id()] = song
            if len(songs_added) == self._SPLICE_SIZE:
                self._songs_model.splice(
                    self._songs_model.get_n_items(), 0, songs_added)
                songs_added.clear()

            if remaining == 0:
                self._songs_model.splice(
                    self._songs_model.get_n_items(), 0, songs_added)
                self._window.notifications_popup.pop_loading()
                return

        query = """upnp:class derivedfrom 'object.item.audioItem'
        """.replace("\n", " ").strip()

        options = self._fast_options.copy()
        self._source.query(query, self.METADATA_KEYS, options, _add_to_model)

    def search(self, text):
        # Does not work yet
        """Searches for media items(songs/albums/artists in
        the dleyna source)

        :param str text: string to be searched
        """
        self._log.warning("Dleyna does not implement search yet.")
