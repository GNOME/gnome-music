# Copyright (c) 2016 The GNOME Music Developers
#
# GNOME Music is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# GNOME Music is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with GNOME Music; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# The GNOME Music authors hereby grant permission for non-GPL compatible
# GStreamer plugins to be used and distributed together with GStreamer
# and GNOME Music.  This permission is above and beyond the permissions
# granted by the GPL license by which GNOME Music is covered.  If you
# modify this code, you may extend this exception to your version of the
# code, but you are not obligated to do so.  If you do not wish to do so,
# delete this exception statement from your version.

from gettext import ngettext
from gi.repository import GdkPixbuf, GLib, GObject, Gtk

from gnomemusic import log
from gnomemusic.albumartcache import Art, ArtImage
from gnomemusic.grilo import grilo
from gnomemusic.gstplayer import Playback
from gnomemusic.widgets.disclistboxwidget import DiscBox
from gnomemusic.widgets.disclistboxwidget import DiscListBox  # noqa: F401
from gnomemusic.widgets.songwidget import SongWidget
import gnomemusic.utils as utils


@Gtk.Template(resource_path='/org/gnome/Music/AlbumWidget.ui')
class AlbumWidget(Gtk.EventBox):
    """Album widget.

    The album widget consists of an image with the album art
    on the left and a list of songs on the right.
    """

    __gtype_name__ = 'AlbumWidget'

    _artist_label = Gtk.Template.Child()
    _composer_label = Gtk.Template.Child()
    _composer_info_label = Gtk.Template.Child()
    _cover = Gtk.Template.Child()
    _disc_listbox = Gtk.Template.Child()
    _released_info_label = Gtk.Template.Child()
    _running_info_label = Gtk.Template.Child()
    _title_label = Gtk.Template.Child()

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

        self._songs = []

        self._parent_view = parent_view
        self._player = player
        self._iter_to_clean = None

        self._selection_mode = False

        self._create_model()
        self._album = None
        self._header_bar = None

        # FIXME: Assigned to appease searchview
        # _get_selected_songs
        self.view = self._disc_listbox

        self.show_all()

    @log
    def _on_selection_mode_request(self, *args):
        """Selection mode toggled."""
        self._header_bar._select_button.clicked()

    @log
    def _create_model(self):
        """Create the ListStore model for this widget."""
        self._model = Gtk.ListStore(
            GObject.TYPE_STRING,  # title
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GdkPixbuf.Pixbuf,    # icon
            GObject.TYPE_OBJECT,  # song object
            GObject.TYPE_BOOLEAN,  # item selected
            GObject.TYPE_STRING,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT,  # icon shown
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT
        )

    @log
    def update(self, item, header_bar, selection_toolbar):
        """Update the album widget.

        :param item: The grilo media item
        :param header_bar: The header bar object
        :param selection_toolbar: The selection toolbar object
        """
        # reset view
        self._songs = []
        self._create_model()
        for widget in self._disc_listbox.get_children():
            self._disc_listbox.remove(widget)

        self.selection_toolbar = selection_toolbar
        self._header_bar = header_bar
        self._duration = 0
        art = ArtImage(Art.Size.LARGE, item)
        art.image = self._cover

        GLib.idle_add(grilo.populate_album_songs, item, self.add_item)
        header_bar._select_button.connect(
            'toggled', self._on_header_select_button_toggled)
        header_bar._cancel_button.connect(
            'clicked', self._on_header_cancel_button_clicked)

        self._album = utils.get_album_title(item)
        self._artist_label.props.label = utils.get_artist_name(item)
        self._title_label.props.label = self._album

        year = utils.get_media_year(item)
        if not year:
            year = '----'
        self._released_info_label.props.label = year

        self._set_composer_label(item)

        self._player.connect('song-changed', self._update_model)

    @log
    def _set_composer_label(self, item):
        composer = item.get_composer()
        show = False

        if composer:
            self._composer_info_label.props.label = composer
            show = True

        self._composer_label.props.visible = show
        self._composer_info_label.props.visible = show

    @log
    def _set_duration_label(self):
        mins = (self._duration // 60) + 1
        self._running_info_label.props.label = ngettext(
            "{} minute", "{} minutes", mins).format(mins)

    @Gtk.Template.Callback()
    @log
    def _on_selection_changed(self, widget):
        n_items = len(self._disc_listbox.get_selected_items())
        self.selection_toolbar.props.items_selected = n_items
        self._header_bar.items_selected = n_items

    @log
    def _on_header_cancel_button_clicked(self, button):
        """Cancel selection mode callback."""
        self._disc_listbox.props.selection_mode = False
        self._header_bar.props.selection_mode = False
        self._header_bar.props.title = self._album

    @log
    def _on_header_select_button_toggled(self, button):
        """Selection mode button clicked callback."""
        if button.get_active():
            self._selection_mode = True
            self._disc_listbox.props.selection_mode = True
            self._header_bar.props.selection_mode = True
            self._parent_view.set_player_visible(False)
        else:
            self._selection_mode = False
            self._disc_listbox.props.selection_mode = False
            self._header_bar.props.selection_mode = False
            if self._player.get_playback_status() != Playback.STOPPED:
                self._parent_view.set_player_visible(True)

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
        disc_box.connect('selection-toggle', self._selection_mode_toggled)

        return disc_box

    @log
    def _selection_mode_toggled(self, widget):
        self._selection_mode = not self._selection_mode
        self._on_selection_mode_request()

    @log
    def _song_activated(self, widget, song_widget):
        if self._selection_mode:
            song_widget.props.selected = not song_widget.props.selected
            return

        self._player.stop()
        self._player.set_playlist(
            'Album', self._album, song_widget.model, song_widget.itr)
        self._player.set_playing(True)
        return True

    @log
    def add_item(self, source, prefs, song, remaining, data=None):
        """Add a song to the item to album list.

        :param source: The grilo source
        :param prefs:
        :param song: The grilo media object
        :param remaining: Remaining number of items to add
        :param data: User data
        """
        if song:
            self._songs.append(song)

            self._duration = self._duration + song.get_duration()
            return

        discs = {}
        for song in self._songs:
            disc_nr = song.get_album_disc_number()
            if disc_nr not in discs.keys():
                discs[disc_nr] = [song]
            else:
                discs[disc_nr].append(song)
        for disc_nr in discs:
            disc = self._create_disc_box(disc_nr, discs[disc_nr])
            self._disc_listbox.add(disc)
            if len(discs) == 1:
                disc.props.show_disc_label = False

        if remaining == 0:
            self._set_duration_label()

            self.show_all()

    @log
    def _update_model(self, player, playlist, current_iter):
        """Player changed callback.

        :param player: The player object
        :param playlist: The current playlist
        :param current_iter: The current iter of the playlist model
        """
        if not player.running_playlist('Album', self._album):
            return True

        current_song = playlist[current_iter][player.Field.SONG]

        self._duration = 0

        song_passed = False
        _iter = playlist.get_iter_first()

        while _iter:
            song = playlist[_iter][player.Field.SONG]
            song_widget = song.song_widget
            self._duration += song.get_duration()

            if (song == current_song):
                song_widget.props.state = SongWidget.State.PLAYING
                song_passed = True
            elif (song_passed):
                # Counter intuitive, but this is due to call order.
                song_widget.props.state = SongWidget.State.UNPLAYED
            else:
                song_widget.props.state = SongWidget.State.PLAYED

            _iter = playlist.iter_next(_iter)

        self._set_duration_label()

        return True

    @log
    def select_all(self):
        self._disc_listbox.select_all()

    @log
    def select_none(self):
        self._disc_listbox.select_none()
