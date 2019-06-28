from gi.repository import Gfm, Gio, GObject, Gtk, GdkPixbuf
from gi._gi import pygobject_new_full


class SongListStore(Gtk.ListStore):

    def __init__(self, model):
        super().__init__()

        self._model = Gfm.SortListModel.new(model)
        self._model.set_sort_func(
            self._wrap_list_store_sort_func(self._songs_sort))

        self.set_column_types([
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,    # title
            GObject.TYPE_STRING,    # artist
            GdkPixbuf.Pixbuf,       # album art
            GObject.TYPE_OBJECT,    # Grl.Media
            GObject.TYPE_BOOLEAN,   # selected
            GObject.TYPE_INT,
            GObject.TYPE_STRING,    # play icon (?)
            GObject.TYPE_INT,       # favorite
            GObject.TYPE_BOOLEAN,   # iter_to_clean
            GObject.TYPE_INT        # validation
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
                coresong = model[position]
                self.insert_with_valuesv(
                    position, [2, 3, 5, 9],
                    [coresong.props.title, coresong.props.artist, coresong,
                     int(coresong.props.favorite)])

    @GObject.Property(
        type=Gio.ListStore, default=None, flags=GObject.ParamFlags.READABLE)
    def model(self):
        return self._model
