from gettext import ngettext
from gi.repository import GdkPixbuf, GObject, Grl, Gtk

from gnomemusic import log
from gnomemusic.albumartcache import Art
from gnomemusic.grilo import grilo
from gnomemusic.player import PlayerPlaylist
from gnomemusic.widgets.disclistboxwidget import DiscBox
from gnomemusic.widgets.disclistboxwidget import DiscListBox  # noqa: F401
from gnomemusic.widgets.songwidget import SongWidget
import gnomemusic.utils as utils


@Gtk.Template(resource_path='/org/gnome/Music/ui/AlbumWidget2.ui')
class AlbumWidget2(Gtk.EventBox):
    """Album widget.

    The album widget consists of an image with the album art
    on the left and a list of songs on the right.
    """

    __gtype_name__ = 'AlbumWidget2'

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

        self._cover_stack.props.size = Art.Size.LARGE
        self._parent_view = parent_view
        self._player = player

        self._album_name = None

        self._listbox.connect("row-activated", self._on_row_activated)

    @log
    def update(self, album):
        """Update the album widget.

        :param Grl.Media album: The grilo media album
        """
        self._cover_stack.update(album)

        self._duration = 0

        self._album_name = utils.get_album_title(album)
        artist = utils.get_artist_name(album)

        self._title_label.props.label = self._album_name
        self._title_label.props.tooltip_text = self._album_name

        self._artist_label.props.label = artist
        self._artist_label.props.tooltip_text = artist

        year = utils.get_media_year(album)
        if not year:
            year = '----'
        self._released_info_label.props.label = year

        self._set_composer_label(album)

        self._album = album

        self._listbox.bind_model(
            self._parent_view._window._app._coremodel.get_album_model(album),
            self._create_widget)

    @log
    def _create_widget(self, song):
        song_widget = SongWidget(song._media)

        song.bind_property(
            "favorite", song_widget, "favorite",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        return song_widget

    @log
    def _set_composer_label(self, album):
        composer = album.get_composer()
        show = False

        if composer:
            self._composer_info_label.props.label = composer
            self._composer_info_label.props.max_width_chars = 10
            self._composer_info_label.props.tooltip_text = composer
            show = True

        self._composer_label.props.visible = show
        self._composer_info_label.props.visible = show

    @log
    def _set_duration_label(self):
        mins = (self._duration // 60) + 1
        self._running_info_label.props.label = ngettext(
            "{} minute", "{} minutes", mins).format(mins)

    # @Gtk.Template.Callback()
    @log
    def _on_selection_changed(self, widget):
        n_items = len(self._disc_listbox.get_selected_items())
        self.props.selected_items_count = n_items

    @log
    def _create_disc_box(self, disc_nr, disc_songs):
        disc_box = DiscBox(self._model)
        disc_box.set_songs(disc_songs)
        disc_box.set_disc_number(disc_nr)
        disc_box.props.columns = 1
        disc_box.props.show_durations = True
        disc_box.props.show_favorites = True
        disc_box.props.show_song_numbers = False
        disc_box.connect('song-activated', self._song_activated)

        return disc_box

    @log
    def _song_activated(self, widget, song_widget):
        if self.props.selection_mode:
            song_widget.props.selected = not song_widget.props.selected
            return

        self._player.set_playlist(
            PlayerPlaylist.Type.ALBUM, self._album_name, song_widget.model,
            song_widget.itr)
        self._player.play()
        return True

    @log
    def select_all(self):
        pass

    @log
    def select_none(self):
        pass

    @log
    def get_selected_songs(self):
        """Return a list of selected songs.

        :returns: selected songs
        :rtype: list
        """
        return []

    @GObject.Property(
        type=Grl.Media, default=False, flags=GObject.ParamFlags.READABLE)
    def album(self):
        """Get the current album.

        :returns: the current album
        :rtype: Grl.Media
        """
        return self._album
