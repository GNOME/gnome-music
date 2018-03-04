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

from gi.repository import GObject, Gtk

from gnomemusic import log
from gnomemusic.albumartcache import Art
from gnomemusic.grilo import grilo
from gnomemusic.widgets.coverstack import CoverStack
from gnomemusic.widgets.disclistboxwidget import DiscBox
import gnomemusic.utils as utils


class ArtistAlbumWidget(Gtk.Box):

    __gsignals__ = {
        'songs-loaded': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __repr__(self):
        return '<ArtistAlbumWidget>'

    @log
    def __init__(self, media, player, model, header_bar,
                 selection_mode_allowed, size_group=None,
                 cover_size_group=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)

        self._size_group = size_group
        self._cover_size_group = cover_size_group

        self._media = media
        self._player = player
        self._artist = utils.get_artist_name(self._media)
        self._album_title = utils.get_album_title(self._media)
        self._model = model
        self._header_bar = header_bar
        self._selection_mode = False
        self._selection_mode_allowed = selection_mode_allowed

        self._songs = []

        self._header_bar._select_button.connect(
            'toggled', self._on_header_select_button_toggled)

        ui = Gtk.Builder()
        ui.add_from_resource('/org/gnome/Music/ArtistAlbumWidget.ui')

        self.cover = ui.get_object('cover')

        self.cover_stack = CoverStack(self.cover, Art.Size.MEDIUM)
        self.cover_stack.update(self._media)

        self._disc_listbox = ui.get_object('disclistbox')
        self._disc_listbox.set_selection_mode_allowed(
            self._selection_mode_allowed)

        ui.get_object('title').set_label(self._album_title)
        creation_date = self._media.get_creation_date()
        if creation_date:
            year = creation_date.get_year()
            ui.get_object('year').set_markup(
                '<span color=\'grey\'>{}</span>'.format(year))

        if self._size_group:
            self._size_group.add_widget(ui.get_object('box1'))

        if self._cover_size_group:
            self._cover_size_group.add_widget(self.cover_stack._stack)

        self.pack_start(ui.get_object('ArtistAlbumWidget'), True, True, 0)

        grilo.populate_album_songs(self._media, self._add_item)

    def create_disc_box(self, disc_nr, disc_songs):
        disc_box = DiscBox(self._model)
        disc_box.set_songs(disc_songs)
        disc_box.set_disc_number(disc_nr)
        disc_box.set_columns(2)
        disc_box.show_duration(False)
        disc_box.show_favorites(False)
        disc_box.connect('song-activated', self._song_activated)
        disc_box.connect('selection-toggle', self._selection_mode_toggled)

        return disc_box

    def _selection_mode_toggled(self, widget):
        if not self._selection_mode_allowed:
            return

        self._selection_mode = not self._selection_mode
        self._on_selection_mode_request()

        return True

    def _on_selection_mode_request(self):
        self._header_bar._select_button.clicked()

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
    def _add_item(self, source, prefs, song, remaining, data=None):
        if song:
            self._songs.append(song)
            return

        discs = {}
        for song in self._songs:
            disc_nr = song.get_album_disc_number()
            if disc_nr not in discs.keys():
                discs[disc_nr] = [song]
            else:
                discs[disc_nr].append(song)

        for disc_nr in discs:
            disc = self.create_disc_box(disc_nr, discs[disc_nr])
            self._disc_listbox.add(disc)
            if len(discs) == 1:
                disc.show_disc_label(False)

        if remaining == 0:
            self.emit("songs-loaded")

    @log
    def _song_activated(self, widget, song_widget):
        if (not song_widget.can_be_played
                or self._selection_mode):
            return

        self._player.stop()
        self._player.set_playlist(
            'Artist', self._artist, song_widget.model, song_widget.itr)
        self._player.set_playing(True)

        return True

    @log
    def set_selection_mode(self, selection_mode):
        if self._selection_mode == selection_mode:
            return
        self._selection_mode = selection_mode

        self._disc_listbox.set_selection_mode(selection_mode)
