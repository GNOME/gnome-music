import gi
gi.require_version('Grl', '0.3')
from gi.repository import Grl, GObject

from gnomemusic import log
from gnomemusic.grilo import grilo
import gnomemusic.utils as utils


class CoreArtist(GObject.GObject):
    """Exposes a Grl.Media with relevant data as properties
    """

    artist = GObject.Property(type=str)
    media = GObject.Property(type=Grl.Media)
    selected = GObject.Property(type=bool, default=False)

    @log
    def __init__(self, media):
        super().__init__()

        self.update(media)

    @log
    def update(self, media):
        self.props.media = media
        self.props.artist = utils.get_artist_name(media)
