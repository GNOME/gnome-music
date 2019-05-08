import gi
gi.require_version('Grl', '0.3')
from gi.repository import Grl, GObject

from gnomemusic import log
import gnomemusic.utils as utils


class CoreSong(GObject.GObject):
    """Exposes a Grl.Media with relevant data as properties
    """

    album = GObject.Property(type=str)
    album_disc_number = GObject.Property(type=int)
    artist = GObject.Property(type=str)
    duration = GObject.Property(type=int)
    favorite = GObject.Property(type=int)
    play_count = GObject.Property(type=int)
    position = GObject.Property(type=int)
    title = GObject.Property(type=str)
    url = GObject.Property(type=str)

    @log
    def __init__(self, media):
        super().__init__()

        self._media = media

        self.props.album = utils.get_album_title(media)
        self.props.artist = utils.get_artist_name(media)
        self.props.play_count = self._media.get_play_count()
        self.props.title = utils.get_media_title(self._media)
        self.props.url = self._media.get_url()

