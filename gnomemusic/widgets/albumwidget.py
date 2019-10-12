from gettext import ngettext
from gi.repository import GObject, Grl, Gtk

from gnomemusic import log
from gnomemusic.albumartcache import Art
from gnomemusic.player import PlayerPlaylist
from gnomemusic.utils import AdaptiveViewMode
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

    _album_widget = Gtk.Template.Child()
    _album_info = Gtk.Template.Child()

    adaptive_view = GObject.Property(type=int, default=AdaptiveViewMode.MOBILE)
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
        self._corealbum = None
        self._duration_signal_id = None
        self._model_signal_id = None

        self.connect("notify::adaptive-view", self._on_adaptive_view_changed)
        self._cover_stack.props.size = Art.Size.LARGE
        self._parent_view = parent_view
        self._player = player

    @log
    def update(self, corealbum):
        """Update the album widget.

        :param CoreAlbum album: The CoreAlbum object
        """
        if self._corealbum:
            self._corealbum.disconnect(self._duration_signal_id)
            self._corealbum.props.model.disconnect(self._model_signal_id)

        self._corealbum = corealbum

        self._cover_stack.update(self._corealbum)

        album_name = self._corealbum.props.title
        artist = self._corealbum.props.artist

        self._title_label.props.label = album_name
        self._title_label.props.tooltip_text = album_name

        self._artist_label.props.label = artist
        self._artist_label.props.tooltip_text = artist

        self._released_info_label.props.label = self._corealbum.props.year

        self._set_composer_label(corealbum)

        self._album = self._corealbum.props.media
        self._album_model = self._corealbum.props.model
        self._model_signal_id = self._album_model.connect_after(
            "items-changed", self._on_model_items_changed)
        self._listbox.bind_model(self._album_model, self._create_widget)

        self._on_duration_changed(self._corealbum, None)
        self._duration_signal_id = self._corealbum.connect(
            "notify::duration", self._on_duration_changed)

        self._album_model.items_changed(0, 0, 0)

    def _on_adaptive_view_changed(self, widget, param):
        if self.props.adaptive_view == AdaptiveViewMode.MOBILE:
            self._album_widget.set_orientation(Gtk.Orientation.VERTICAL)
            self._album_widget.set_margin_top(32)
            self._album_widget.set_margin_right(0)
            self._album_widget.set_margin_left(0)
        else:
            self._album_widget.set_orientation(Gtk.Orientation.HORIZONTAL)
            self._album_widget.set_margin_top(32)
            self._album_widget.set_margin_right(32)
            self._album_widget.set_margin_left(32)

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

        def _on_playlist_loaded(klass, playlist_type):
            self._player.play(song_widget.props.coresong)
            coremodel.disconnect(signal_id)

        signal_id = coremodel.connect("playlist-loaded", _on_playlist_loaded)
        coremodel.set_player_model(
            PlayerPlaylist.Type.ALBUM, self._album_model)

        return True

    @log
    def select_all(self):
        self._listbox.select_all()

    @log
    def select_none(self):
        self._listbox.select_none()

    @GObject.Property(
        type=Grl.Media, default=False, flags=GObject.ParamFlags.READABLE)
    def album(self):
        """Get the current album.

        :returns: the current album
        :rtype: Grl.Media
        """
        return self._album
