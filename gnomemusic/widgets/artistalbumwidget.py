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


@Gtk.Template(resource_path='/org/gnome/Music/ArtistAlbumWidget.ui')
class ArtistAlbumWidget(Gtk.Box):

    __gtype_name__ = 'ArtistAlbumWidget'

    _album_box = Gtk.Template.Child()
    _cover = Gtk.Template.Child()
    _disc_list_box = Gtk.Template.Child()
    _title = Gtk.Template.Child()
    _year = Gtk.Template.Child()

    selection_mode = GObject.Property(type=bool, default=False)

    __gsignals__ = {
        'songs-loaded': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __repr__(self):
        return '<ArtistAlbumWidget>'

    @log
    def __init__(
            self, media, player, model, header_bar, selection_mode_allowed,
            size_group=None, cover_size_group=None):
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

        self.cover_stack = CoverStack(self._cover, Art.Size.MEDIUM)
        self.cover_stack.update(self._media)

        allowed = self._selection_mode_allowed
        self._disc_list_box.props.selection_mode_allowed = allowed

        self.bind_property(
            'selection-mode', self._disc_list_box, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL |
            GObject.BindingFlags.SYNC_CREATE)

        self._title.props.label = self._album_title
        year = utils.get_media_year(self._media)

        if year:
            self._year.props.label = year

        if self._size_group:
            self._size_group.add_widget(self._album_box)

        if self._cover_size_group:
            self._cover_size_group.add_widget(self.cover_stack._stack)

        grilo.populate_album_songs(self._media, self._add_item)

    @log
    def _create_disc_box(self, disc_nr, disc_songs):
        disc_box = DiscBox(self._model)
        disc_box.set_songs(disc_songs)
        disc_box.set_disc_number(disc_nr)
        disc_box.props.columns = 2
        disc_box.props.show_durations = False
        disc_box.props.show_favorites = False
        disc_box.props.show_song_numbers = True
        disc_box.connect('song-activated', self._song_activated)

        return disc_box

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
            disc = self._create_disc_box(disc_nr, discs[disc_nr])
            self._disc_list_box.add(disc)
            if len(discs) == 1:
                disc.props.show_disc_label = False

        if remaining == 0:
            self.emit("songs-loaded")

    @log
    def _song_activated(self, widget, song_widget):
        if self.props.selection_mode:
            return

        self._player.stop()
        self._player.set_playlist(
            'Artist', self._artist, song_widget.model, song_widget.itr)
        self._player.play()

        return True

    @log
    def select_all(self):
        """Select all items"""
        self._disc_list_box.select_all()

    @log
    def select_none(self):
        """Deselect all items"""
        self._disc_list_box.select_none()
