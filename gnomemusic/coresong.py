import gi
gi.require_version('Grl', '0.3')
from gi.repository import Grl, GObject

import gnomemusic.utils as utils

class CoreSong(GObject.GObject):
    """Exposes a Grl.Media with relevant data as properties
    """

    url = GObject.Property(type=str)
    title = GObject.Property(type=str)

    def __init__(self, media):
        super().__init__()

        self._media = media

        self.props.url = self._media.get_url()
        self.props.title = utils.get_media_title(self._media)
