from gettext import ngettext
from gi.repository import GObject, Grl, Gtk

from gnomemusic import log
from gnomemusic.albumartcache import Art
from gnomemusic.player import PlayerPlaylist
from gnomemusic.widgets.disclistboxwidget import DiscBox
from gnomemusic.widgets.disclistboxwidget import DiscListBox  # noqa: F401


@Gtk.Template(resource_path='/org/gnome/Music/ui/AlbumWidget.ui')
class AlbumWidget(Gtk.EventBox):
    """Album widget.

    The album widget consists of an image with the album art
    on the left and a list of songs on the right.
    """

    __gtype_name__ = 'AlbumWidget'

    _artist_label = Gtk.Template.Child()
    _composer_label = Gtk.Template.Child()
    _composer_info_label = Gtk.Template.Child()
    _cover_stack = Gtk.Template.Child()
    _listbox = Gtk.Template.Child()
    _released_info_label = Gtk.Template.Child()
    _running_info_label = Gtk.Template.Child()
    _title_label = Gtk.Template.Child()

    selected_items_count = GObject.Property(type=int, default=0, minimum=0)
    selection_mode = GObject.Property(type=bool, default=False)

    _duration = 0

    def __repr__(self):
        return '<AlbumWidget>'

    @log
    def __init__(self, player, parent_view):
        """Initialize the AlbumWidget.

        :param player: The player object
        :param parent_view: The view this widget is part of
        """
        super().__init__()

        self._album = None
        self._album_model = None
        self._signal_id = None

        self._cover_stack.props.size = Art.Size.LARGE
        self._parent_view = parent_view
        self._player = player

        self._album_name = None

    @log
    def update(self, corealbum):
        """Update the album widget.

        :param CoreAlbum album: The CoreAlbum object
        """
        if self._signal_id:
            self._album_model.disconnect(self._signal_id)

        self._cover_stack.update(corealbum.props.media)

        self._duration = 0

        self._album_name = corealbum.props.title
        artist = corealbum.props.artist

        self._title_label.props.label = self._album_name
        self._title_label.props.tooltip_text = self._album_name

        self._artist_label.props.label = artist
        self._artist_label.props.tooltip_text = artist

        self._released_info_label.props.label = corealbum.props.year

        self._set_composer_label(corealbum)

        self._album = corealbum.props.media
        self._album_model = corealbum.props.model
        self._signal_id = self._album_model.connect_after(
            "items-changed", self._on_model_items_changed)
        self._listbox.bind_model(self._album_model, self._create_widget)

        corealbum.connect("notify::duration", self._on_duration_changed)

        self._album_model.items_changed(0, 0, 0)

    def _create_widget(self, disc):
        disc_box = self._create_disc_box(
            disc.props.disc_nr, disc.model)

        self.bind_property(
            "selection-mode", disc_box, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        return disc_box

    def _create_disc_box(self, disc_nr, album_model):
        disc_box = DiscBox(album_model)
        disc_box.set_disc_number(disc_nr)
        disc_box.props.show_durations = False
        disc_box.props.show_favorites = False
        disc_box.props.show_song_numbers = True
        disc_box.connect('song-activated', self._song_activated)

        return disc_box

    def _on_model_items_changed(self, model, position, removed, added):
        n_items = model.get_n_items()
        if n_items == 1:
            row = self._listbox.get_row_at_index(0)
            row.props.selectable = False
            discbox = row.get_child()
            discbox.props.show_disc_label = False
        else:
            for i in range(n_items):
                row = self._listbox.get_row_at_index(i)
                row.props.selectable = False
                discbox = row.get_child()
                discbox.props.show_disc_label = True

    @log
    def _set_composer_label(self, corealbum):
        composer = corealbum.props.composer
        show = False

        if composer:
            self._composer_info_label.props.label = composer
            self._composer_info_label.props.max_width_chars = 10
            self._composer_info_label.props.tooltip_text = composer
            show = True

        self._composer_label.props.visible = show
        self._composer_info_label.props.visible = show

    def _on_duration_changed(self, coredisc, duration):
        mins = (coredisc.props.duration // 60) + 1
        self._running_info_label.props.label = ngettext(
            "{} minute", "{} minutes", mins).format(mins)

    @log
    def _on_selection_changed(self, klass, value):
        n_items = 0
        for song in self._model[0]:
            if song.props.selected:
                n_items += 1

        self.props.selected_items_count = n_items

    @log
    def _song_activated(self, widget, song_widget):
        if self.props.selection_mode:
            song_widget.props.selected = not song_widget.props.selected
            return

        signal_id = None
        coremodel = self._parent_view._window._app.props.coremodel

        def _on_playlist_loaded(klass):
            self._player.play(song_widget.props.coresong)
            coremodel.disconnect(signal_id)

        signal_id = coremodel.connect("playlist-loaded", _on_playlist_loaded)
        coremodel.set_playlist_model(
            PlayerPlaylist.Type.ALBUM, song_widget.props.coresong,
            self._album_model)

        return True

    @log
    def select_all(self):
        self._listbox.select_all()

    @log
    def select_none(self):
        self._listbox.select_none()

    @log
    def get_selected_songs(self):
        """Return a list of selected songs.

        :returns: selected songs
        :rtype: list
        """
        selected_songs = []

        for song in self._model:
            if song.props.selected:
                selected_songs.append(song.props.media)

        return selected_songs

    @GObject.Property(
        type=Grl.Media, default=False, flags=GObject.ParamFlags.READABLE)
    def album(self):
        """Get the current album.

        :returns: the current album
        :rtype: Grl.Media
        """
        return self._album
