import gi
gi.require_version('Grl', '0.3')
from gi.repository import Gio, Grl, GObject

from gnomemusic import log
from gnomemusic.grilo import grilo
import gnomemusic.utils as utils


class CoreAlbum(GObject.GObject):
    """Exposes a Grl.Media with relevant data as properties
    """

    artist = GObject.Property(type=str)
    composer = GObject.Property(type=str, default=None)
    model = GObject.Property(type=Gio.ListModel, default=None)
    media = GObject.Property(type=Grl.Media)
    selected = GObject.Property(type=bool, default=False)
    title = GObject.Property(type=str)
    year = GObject.Property(type=str, default="----")

    @log
    def __init__(self, media):
        super().__init__()

        self.update(media)

    @log
    def update(self, media):
        self.props.media = media
        self.props.artist = utils.get_artist_name(media)
        self.props.composer = media.get_composer()
        self.props.title = utils.get_media_title(media)
        self.props.year = utils.get_media_year(media)
