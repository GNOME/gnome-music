from gi.repository import Dazzle, GObject, Gio, Gfm, Grl
from gi._gi import pygobject_new_full


class CoreDisc(GObject.GObject):

    disc_nr = GObject.Property(type=int, default=0)
    duration = GObject.Property(type=int, default=None)
    media = GObject.Property(type=Grl.Media, default=None)

    def __init__(self, media, nr, coremodel):
        super().__init__()

        self._coremodel = coremodel
        self._filter_model = None
        self._model = None
        self._old_album_ids = []
        self._selected = False
        self._sort_model = None

        self.update(media)
        self.props.disc_nr = nr

    def update(self, media):
        self.props.media = media

    @GObject.Property(type=Gio.ListModel, default=None)
    def model(self):
        if self._model is None:
            self._filter_model = Dazzle.ListModelFilter.new(
                self._coremodel.get_model())
            self._filter_model.set_filter_func(lambda a: False)
            self._sort_model = Gfm.SortListModel.new(self._filter_model)
            self._sort_model.set_sort_func(
                self._wrap_sort_func(self._disc_sort))

            self._model = self._sort_model

            self._coremodel.get_model().connect(
                "items-changed", self._on_core_changed)
            self._model.connect("items-changed", self._on_disc_changed)

            self._get_album_disc(
                self.props.media, self.props.disc_nr, self._filter_model)

        self._on_disc_changed(self._model, None, None, None)

        return self._model

    def _on_core_changed(self, model, position, removed, added):
        self._get_album_disc(
            self.props.media, self.props.disc_nr, self._filter_model)

    def _on_disc_changed(self, model, position, removed, added):
        with self.freeze_notify():
            for coresong in model:
                coresong.props.selected = self._selected

    def _update_duration(self):
        duration = 0

        for coresong in self.props.model:
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

    def _get_album_disc(self, media, discnr, model):
        album_ids = []
        model_filter = model

        def _filter_func(core_song):
            return core_song.props.media.get_id() in album_ids

        def _reverse_sort(song_a, song_b, data=None):
            return song_a.props.track_number - song_b.props.track_number

        def _callback(source, dunno, media, something, something2):
            if media is None:
                if sorted(album_ids) == sorted(self._old_album_ids):
                    return
                model_filter.set_filter_func(_filter_func)
                self._old_album_ids = album_ids
                self._update_duration()
                return

            album_ids.append(media.get_id())

        self._coremodel._grilo.populate_album_disc_songs(
            media, discnr, _callback)

    @GObject.Property(
        type=bool, default=False, flags=GObject.BindingFlags.SYNC_CREATE)
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        self._selected = value

        # The model is loaded on-demand, so the first time the model is
        # returned it can still be empty. This is problem for returning
        # a selection. Trigger loading of the model here if a selection
        # is requested, it will trigger the filled model update as
        # well.
        self.props.model
