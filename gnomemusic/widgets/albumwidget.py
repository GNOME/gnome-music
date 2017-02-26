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

from gettext import gettext as _, ngettext
from gi.repository import Gd, Gdk, GdkPixbuf, GLib, GObject, Gtk, Pango

from gnomemusic import log
from gnomemusic.albumartcache import AlbumArtCache, DefaultIcon, ArtSize
from gnomemusic.grilo import grilo
from gnomemusic.player import DiscoveryStatus
from gnomemusic.playlists import Playlists
from gnomemusic.widgets.disclistboxwidget import DiscBox, DiscListBox
import gnomemusic.utils as utils


class AlbumWidget(Gtk.EventBox):
    """Album widget.

    The album widget consists of an image with the album art
    on the left and a list of songs on the right.
    """

    _duration = 0

    def __repr__(self):
        return '<AlbumWidget>'

    @log
    def __init__(self, player, parent_view):
        """Initialize the AlbumWidget.

        :param player: The player object
        :param parent_view: The view this widget is part of
        """
        Gtk.EventBox.__init__(self)

        self._songs = []

        scale = self.get_scale_factor()
        self._cache = AlbumArtCache(scale)
        self._loading_icon_surface = DefaultIcon(scale).get(
            DefaultIcon.Type.loading,
            ArtSize.large)

        self._player = player
        self._iter_to_clean = None

        self._selection_mode = False

        self._builder = Gtk.Builder()
        self._builder.add_from_resource('/org/gnome/Music/AlbumWidget.ui')
        self._create_model()
        self._album = None
        self._header_bar = None
        self._selection_mode_allowed = True

        self._composer_label = self._builder.get_object('composer_label')
        self._composer_info = self._builder.get_object('composer_info')

        view_box = self._builder.get_object('view')
        self._disc_listbox = DiscListBox()
        self._disc_listbox.set_selection_mode_allowed(True)
        # TODO: The top of the coverart is the same vertical
        # position as the top of the album songs, however
        # since we set a top margins for the discbox
        # subtract that margin here. A cleaner solution is
        # appreciated.
        self._disc_listbox.set_margin_top(64 - 16)
        self._disc_listbox.set_margin_bottom(64)
        self._disc_listbox.set_margin_end(32)
        self._disc_listbox.connect('selection-changed',
                                   self._on_selection_changed)
        view_box.add(self._disc_listbox)

        # FIXME: Assigned to appease searchview
        # _get_selected_songs
        self.view = self._disc_listbox

        self.add(self._builder.get_object('AlbumWidget'))
        self.get_style_context().add_class('view')
        self.get_style_context().add_class('content-view')

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
    def update(self, artist, album, item, header_bar, selection_toolbar):
        """Update the album widget.

        :param str artist: The artist name
        :param str album: The album name
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
        self._album = album
        self._builder.get_object('cover').set_from_surface(
            self._loading_icon_surface)
        self._cache.lookup(item, ArtSize.large, self._on_lookup, None)
        self._duration = 0

        GLib.idle_add(grilo.populate_album_songs, item, self.add_item)
        header_bar._select_button.connect(
            'toggled', self._on_header_select_button_toggled)
        header_bar._cancel_button.connect(
            'clicked', self._on_header_cancel_button_clicked)

        # FIXME: use utils
        escaped_artist = GLib.markup_escape_text(artist)
        escaped_album = GLib.markup_escape_text(album)
        self._builder.get_object('artist_label').set_markup(escaped_artist)
        self._builder.get_object('title_label').set_markup(escaped_album)

        if (item.get_creation_date()):
            self._builder.get_object('released_label_info').set_text(
                str(item.get_creation_date().get_year()))
        else:
            self._builder.get_object('released_label_info').set_text('----')

        self._set_composer_label(item)

        self._player.connect('playlist-item-changed', self._update_model)

    @log
    def _set_composer_label(self, item):
        composer = item.get_composer()
        show = False

        if composer:
            self._composer_info.set_text(composer)
            show = True

        self._composer_label.set_visible(show)
        self._composer_info.set_visible(show)

    @log
    def _on_selection_changed(self, widget):
        items = self._disc_listbox.get_selected_items()
        self.selection_toolbar._add_to_playlist_button.set_sensitive(
            len(items) > 0)
        if len(items) > 0:
            self._header_bar._selection_menu_label.set_text(
                ngettext("Selected %d item", "Selected %d items",
                         len(items)) % len(items))
        else:
            self._header_bar._selection_menu_label.set_text(
                _("Click on items to select them"))

    @log
    def _on_header_cancel_button_clicked(self, button):
        """Cancel selection mode callback."""
        self._disc_listbox.set_selection_mode(False)
        self._header_bar.set_selection_mode(False)
        self._header_bar.header_bar.title = self._album

    @log
    def _on_header_select_button_toggled(self, button):
        """Selection mode button clicked callback."""
        if button.get_active():
            self._selection_mode = True
            self._disc_listbox.set_selection_mode(True)
            self._header_bar.set_selection_mode(True)
            self._player.actionbar.set_visible(False)
            self._header_bar.header_bar.set_custom_title(
                self._header_bar._selection_menu_button)
        else:
            self._selection_mode = False
            self._disc_listbox.set_selection_mode(False)
            self._header_bar.set_selection_mode(False)
            if(self._player.get_playback_status() != 2):
                self._player.actionbar.set_visible(True)

    @log
    def _create_disc_box(self, disc_nr, disc_songs):
        disc_box = DiscBox(self._model)
        disc_box.set_songs(disc_songs)
        disc_box.set_disc_number(disc_nr)
        disc_box.set_columns(1)
        disc_box.show_song_numbers(False)
        disc_box.connect('song-activated', self._song_activated)
        disc_box.connect('selection-toggle', self._selection_mode_toggled)

        return disc_box

    @log
    def _selection_mode_toggled(self, widget):
        if not self._selection_mode_allowed:
            return

        self._selection_mode = not self._selection_mode
        self._on_selection_mode_request()


    @log
    def _song_activated(self, widget, song_widget):
        if not song_widget.can_be_played:
            return

        if self._selection_mode:
            song_widget.check_button.toggled()
            return

        self._player.stop()
        self._player.set_playlist('Artist', 'test', song_widget.model,
                                  song_widget.itr, 5, 11)
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
                disc.show_disc_label(False)

        if remaining == 0:
            self._builder.get_object('running_length_label_info').set_text(
                _("%d min") % (int(self._duration / 60) + 1))

            self.show_all()

    @log
    def _on_lookup(self, surface, data=None):
        """Albumart retrieved callback.

        :param surface: The Cairo surface retrieved
        :param path: The filesystem location the pixbuf
        :param data: User data
        """
        self._builder.get_object('cover').set_from_surface(surface)

    @log
    def _update_model(self, player, playlist, current_iter):
        """Player changed callback.

        :param player: The player object
        :param playlist: The current playlist
        :param current_iter: The current iter of the playlist model
        """
        if (playlist != self._model):
            return True

        current_song = playlist[current_iter][5]

        self._duration = 0

        song_passed = False
        _iter = playlist.get_iter_first()

        while _iter:
            song = playlist[_iter][5]
            song_widget = song.song_widget
            self._duration += song.get_duration()
            escaped_title = GLib.markup_escape_text(utils.get_media_title(song))

            if (song == current_song):
                song_widget.now_playing_sign.show()
                song_widget.title.set_markup("<b>{}</b>".format(escaped_title))
                song_passed = True
            elif (song_passed):
                song_widget.now_playing_sign.hide()
                song_widget.title.set_markup(
                    "<span>{}</span>".format(escaped_title))
            else:
                song_widget.now_playing_sign.hide()
                song_widget.title.set_markup(
                    "<span color=\'grey\'>{}</span>".format(escaped_title))

            _iter = playlist.iter_next(_iter)

        self._builder.get_object('running_length_label_info').set_text(
            _("%d min") % (int(self._duration / 60) + 1))

        return True

    @log
    def select_all(self):
        self._disc_listbox.select_all()

    @log
    def select_none(self):
        self._disc_listbox.select_none()
