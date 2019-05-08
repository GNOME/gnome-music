from gi.repository import GObject

from gnomemusic import log


class CoreModel(GObject.GObject):

    @log
    def __init__(self):
        super().__init__()

