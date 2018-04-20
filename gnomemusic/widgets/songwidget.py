from enum import IntEnum

from gi.repository import Gdk, GObject, Grl, Gtk

from gnomemusic import log
from gnomemusic import utils
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists, StaticPlaylists


@Gtk.Template(resource_path='/org/gnome/Music/TrackWidget.ui')
class SongWidget(Gtk.EventBox):

    __gtype_name__ = 'SongWidget'

    __gsignals__ = {
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    _playlists = Playlists.get_default()

    _select_button = Gtk.Template.Child()
    _number_label = Gtk.Template.Child()
    _title_label = Gtk.Template.Child()
    _duration_label = Gtk.Template.Child()
    _star_eventbox = Gtk.Template.Child()
    _star_image = Gtk.Template.Child()
    _play_icon = Gtk.Template.Child()

    class State(IntEnum):
        PLAYED = 0
        PLAYING = 1
        UNPLAYED = 2

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

        self._star_image.favorite = media.get_favourite()

        self._select_button.set_visible(False)

        self._play_icon.set_from_icon_name(
            'media-playback-start-symbolic', Gtk.IconSize.SMALL_TOOLBAR)
        self._play_icon.set_no_show_all(True)

    @Gtk.Template.Callback()
    @log
    def _on_selection_changed(self, klass):
        self.emit('selection-changed')

    @Gtk.Template.Callback()
    @log
    def _on_star_toggle(self, widget, event):
        if event.button != Gdk.BUTTON_PRIMARY:
            return False

        favorite = not self._star_image.favorite
        self._star_image.favorite = favorite

        # FIXME: This does not belong here.
        grilo.set_favorite(self._media, favorite)
        self._playlists.update_static_playlist(StaticPlaylists.Favorites)

        return True

    @Gtk.Template.Callback()
    @log
    def _on_star_hover(self, widget, event):
        self._star_image.hover()

    @Gtk.Template.Callback()
    @log
    def _on_star_unhover(self, widget, event):
        self._star_image.unhover()

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

    @GObject.Property
    @log
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        style_ctx = self._title_label.get_style_context()

        style_ctx.remove_class('dim-label')
        style_ctx.remove_class('playing-song-label')
        self._play_icon.set_visible(False)

        if value == SongWidget.State.PLAYED:
            style_ctx.add_class('dim-label')
        elif value == SongWidget.State.PLAYING:
            self._play_icon.set_visible(True)
            style_ctx.add_class('playing-song-label')

    @GObject.Property(type=bool, default=False)
    @log
    def song_number_visible(self):
        return self._number_label.get_visible()

    @song_number_visible.setter
    @log
    def song_number_visible(self, value):
        self._number_label.set_visible(value)

    @GObject.Property(type=bool, default=False)
    @log
    def favorite_visible(self):
        return self._star_eventbox.get_visible()

    @favorite_visible.setter
    @log
    def favorite_visible(self, value):
        self._star_eventbox.set_visible(value)
        # TODO: disconnect signal handling?

    @GObject.Property(type=bool, default=False)
    @log
    def duration_visible(self):
        return self._duration_label.get_visible()

    @duration_visible.setter
    @log
    def duration_visible(self, value):
        self._duration_label.set_visible(value)