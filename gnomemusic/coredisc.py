import gi
from gi.repository import GObject, Gio, Gfm, Grl, GLib
from gi._gi import pygobject_new_full

from gnomemusic.coregrilo import CoreGrilo
from gnomemusic.coresong import CoreSong


class CoreDisc(GObject.GObject):

    duration = GObject.Property(type=int, default=None)
    media = GObject.Property(type=Grl.Media, default=None)
    model = GObject.Property(type=Gio.ListModel, default=None)

    def __init__(self, media, model):
        super().__init__()

        self.props.model = model
        self.update(media)

        self.props.model.connect("items-changed", self._on_list_items_changed)

    def update(self, media):
        self.props.media = media

    def _on_list_items_changed(self, model, pos, removed, added):
        print("items changed")
        duration = 0

        for coresong in model:
            duration += coresong.props.duration

        self.props.duration = duration
