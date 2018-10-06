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
from gi.repository import GdkPixbuf, GObject, Gtk

from gnomemusic import log
from gnomemusic.albumartcache import Art
from gnomemusic.grilo import grilo
from gnomemusic.player import PlayerPlaylist
from gnomemusic.widgets.disclistboxwidget import DiscBox
from gnomemusic.widgets.disclistboxwidget import DiscListBox  # noqa: F401
from gnomemusic.widgets.songwidget import SongWidget
import gnomemusic.utils as utils


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
    _disc_listbox = Gtk.Template.Child()
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

        self._songs = []

        self._cover_stack.props.size = Art.Size.LARGE
        self._parent_view = parent_view
        self._player = player
        self._iter_to_clean = None

        self._create_model()
        self._album_name = None

        self.bind_property(
            'selection-mode', self._disc_listbox, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL)

        self.bind_property(
            'selection-mode', self._parent_view, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL |
            GObject.BindingFlags.SYNC_CREATE)

        self.bind_property(
            'selected-items-count', self._parent_view, 'selected-items-count')

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
    def update(self, album):
        """Update the album widget.

        :param Grl.Media album: The grilo media album
        """
        # reset view
        self._songs = []
        self._create_model()
        for widget in self._disc_listbox.get_children():
            self._disc_listbox.remove(widget)

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

        self._player.connect('song-changed', self._update_model)

        grilo.populate_album_songs(album, self.add_item)

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

    @Gtk.Template.Callback()
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
    def add_item(self, source, prefs, song, remaining, data=None):
        """Add a song to the item to album list.

        If no song is remaining create DiscBox and display the widget.
        :param GrlTrackerSource source: The grilo source
        :param prefs: not used
        :param GrlMedia song: The grilo media object
        :param int remaining: Remaining number of items to add
        :param data: User data
        """
        if song:
            self._songs.append(song)
            self._duration += song.get_duration()
            return

        if remaining == 0:
            discs = {}
            for song in self._songs:
                disc_nr = song.get_album_disc_number()
                if disc_nr not in discs.keys():
                    discs[disc_nr] = [song]
                else:
                    discs[disc_nr].append(song)

            for disc_nr in discs:
                disc = self._create_disc_box(disc_nr, discs[disc_nr])
                if len(discs) == 1:
                    disc.props.show_disc_label = False
                self._disc_listbox.add(disc)

            self._set_duration_label()
            self._update_model(self._player)

    @log
    def _update_model(self, player, position=None):
        """Updates model when the song changes

        :param Player player: The main player object
        :param int position: current song position
        """
        if not player.playing_playlist(
                PlayerPlaylist.Type.ALBUM, self._album_name):
            return True

        current_song = player.props.current_song
        self._duration = 0
        song_passed = False

        for song in self._songs:
            song_widget = song.song_widget
            self._duration += song.get_duration()

            if (song.get_id() == current_song.get_id()):
                song_widget.props.state = SongWidget.State.PLAYING
                song_passed = True
            elif (song_passed):
                # Counter intuitive, but this is due to call order.
                song_widget.props.state = SongWidget.State.UNPLAYED
            else:
                song_widget.props.state = SongWidget.State.PLAYED

        self._set_duration_label()

        return True

    @log
    def select_all(self):
        self._disc_listbox.select_all()

    @log
    def select_none(self):
        self._disc_listbox.select_none()

    @log
    def get_selected_songs(self):
        """Return a list of selected songs.

        :returns: selected songs
        :rtype: list
        """
        return self._disc_listbox.get_selected_items()
