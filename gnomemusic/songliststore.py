from gi.repository import GObject, Gtk, GdkPixbuf


class SongListStore(Gtk.ListStore):

    model = GObject.Property(type=Gtk.ListStore, default=None)

    def __init__(self, model):
        super().__init__()

        self._model = model

        self.props.model = Gtk.ListStore(
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GdkPixbuf.Pixbuf,
            GObject.TYPE_OBJECT,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT,
            GObject.TYPE_STRING,
            GObject.TYPE_INT,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT
        )

        self._model.connect("items-changed", self._on_items_changed)

    def _on_items_changed(self, model, position, removed, added):
        if removed > 0:
            for i in list(range(removed)):
                path = Gtk.TreePath.new_from_string("{}".format(position))
                iter_ = self._gtk_model.get_iter(path)
                self._gtk_model.remove(iter_)

        if added > 0:
            for i in list(range(added)):
                coresong = self._model[position]
                self.props.model.insert_with_valuesv(
                    position, [2, 3, 5, 9],
                    [coresong.props.title, coresong.props.artist, coresong,
                     int(coresong.props.favorite)])
