from gi.repository import GObject, Grl, Gtk

from gnomemusic import log
from gnomemusic import utils

@Gtk.Template(resource_path='/org/gnome/Music/TrackWidget.ui')
class SongWidget(Gtk.EventBox):

    __gtype_name__ = 'SongWidget'

    _select_button = Gtk.Template.Child()
    _number_label = Gtk.Template.Child()
    _title_label = Gtk.Template.Child()
    _duration_label = Gtk.Template.Child()
    _star_eventbox = Gtk.Template.Child()
    _star_image = Gtk.Template.Child()

    @log
    def __init__(self, media):
        super().__init__()

        self._media = media
        self._selection_mode = False

        song_number = media.get_track_number()
        if song_number == 0:
            song_number = ""
        self._number_label.set_text(str(song_number))

        title = utils.get_media_title(media)
        self._title_label.set_max_width_chars(50)
        self._title_label.set_text(title)

        time = utils.seconds_to_string(media.get_duration())
        self._duration_label.set_text(time)

        self._star_image.set_favorite(media.get_favourite())

        self._select_button.set_visible(False)

    @GObject.Property(type=bool, default=False)
    @log
    def selection_mode(self):
        return self._selection_mode

    @selection_mode.setter
    @log
    def selection_mode(self, value):
        self._selection_mode = value
        self._select_button.set_visible(value)

        if not value:
            self.selected = False

    @GObject.Property(type=bool, default=False)
    @log
    def selected(self):
        return self._select_button.get_active()

    @selected.setter
    @log
    def selected(self, value):
        self._select_button.set_active(value)