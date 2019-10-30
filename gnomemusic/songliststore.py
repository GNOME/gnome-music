from gi.repository import Gio, GObject, Gtk
from gi._gi import pygobject_new_full

import gnomemusic.utils as utils


class SongListStore(Gtk.ListStore):

    def __init__(self, model):
        """Initialize SongListStore.

        :param Gio.ListStore model: The songs model to use
        """
        super().__init__()

        self._model = Gtk.SortListModel.new(model)
        self._model.set_sort_func(
            self._wrap_list_store_sort_func(self._songs_sort))

        self.set_column_types([
            GObject.TYPE_STRING,    # play or invalid icon
            GObject.TYPE_BOOLEAN,   # selected
            GObject.TYPE_STRING,    # title
            GObject.TYPE_STRING,    # artist
            GObject.TYPE_STRING,    # album
            GObject.TYPE_STRING,    # duration
            GObject.TYPE_INT,       # favorite
            GObject.TYPE_OBJECT,    # coresong
            GObject.TYPE_INT,       # validation
            GObject.TYPE_BOOLEAN,   # iter_to_clean
        ])

        self._model.connect("items-changed", self._on_items_changed)

    def _wrap_list_store_sort_func(self, func):

        def wrap(a, b, *user_data):
            a = pygobject_new_full(a, False)
            b = pygobject_new_full(b, False)
            return func(a, b, *user_data)

        return wrap

    def _songs_sort(self, song_a, song_b):
        title_a = song_a.props.title.casefold()
        title_b = song_b.props.title.casefold()
        song_cmp = title_a == title_b
        if not song_cmp:
            return title_a > title_b

        artist_a = song_a.props.artist.casefold()
        artist_b = song_b.props.artist.casefold()
        artist_cmp = artist_a == artist_b
        if not artist_cmp:
            return artist_a > artist_b

        return song_a.props.album.casefold() > song_b.props.album.casefold()

    def _on_items_changed(self, model, position, removed, added):
        if removed > 0:
            for i in list(range(removed)):
                path = Gtk.TreePath.new_from_string("{}".format(position))
                iter_ = self.get_iter(path)
                self.remove(iter_)

        if added > 0:
            for i in list(range(added)):
                coresong = model[position + i]
                time = utils.seconds_to_string(coresong.props.duration)
                self.insert_with_valuesv(
                    position + i, [2, 3, 4, 5, 6, 7],
                    [coresong.props.title, coresong.props.artist,
                     coresong.props.album, time,
                     int(coresong.props.favorite), coresong])
                coresong.connect(
                    "notify::favorite", self._on_favorite_changed)
                coresong.connect(
                    "notify::validation", self._on_validation_state_changed)

    def _on_favorite_changed(self, coresong, value):
        for row in self:
            if coresong == row[7]:
                row[6] = coresong.props.favorite
                break

    def _on_validation_state_changed(self, coresong, value):
        for row in self:
            if coresong == row[7]:
                row[8] = coresong.props.validation
                break

    @GObject.Property(
        type=Gio.ListStore, default=None, flags=GObject.ParamFlags.READABLE)
    def model(self):
        """Gets the model of songs sorted.

        :returns: a list model of sorted songs
        :rtype: Gfm.SortListModel
        """
        return self._model
