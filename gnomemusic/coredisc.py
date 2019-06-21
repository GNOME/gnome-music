import gi
from gi.repository import Dazzle, GObject, Gio, Gfm, Grl, GLib
from gi._gi import pygobject_new_full

from gnomemusic.coregrilo import CoreGrilo
from gnomemusic.coresong import CoreSong


class CoreDisc(GObject.GObject):

    disc_nr = GObject.Property(type=int, default=0)
    duration = GObject.Property(type=int, default=None)
    media = GObject.Property(type=Grl.Media, default=None)
    model = GObject.Property(type=Gio.ListModel, default=None)

    def __init__(self, media, nr, coremodel):
        super().__init__()

        self._coremodel = coremodel
        self.props.disc_nr = nr

        filter_model = Dazzle.ListModelFilter.new(self._coremodel.get_model())
        filter_model.set_filter_func(lambda a: False)
        self._sort_model = Gfm.SortListModel.new(filter_model)
        self._sort_model.set_sort_func(self._wrap_sort_func(self._disc_sort))

        self.props.model = self._sort_model
        self.update(media)

        self.props.model.connect("items-changed", self._on_list_items_changed)

        self._coremodel._get_album_disc(
            self.props.media, self.props.disc_nr, filter_model)

    def update(self, media):
        self.props.media = media

    def _on_list_items_changed(self, model, pos, removed, added):
        duration = 0

        for coresong in model:
            duration += coresong.props.duration

        self.props.duration = duration

    def _disc_sort(self, song_a, song_b):
        return song_a.props.track_number - song_b.props.track_number

    def _wrap_sort_func(self, func):

        def wrap(a, b, *user_data):
            a = pygobject_new_full(a, False)
            b = pygobject_new_full(b, False)
            return func(a, b, *user_data)

        return wrap
