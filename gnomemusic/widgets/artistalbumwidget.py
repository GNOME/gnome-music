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
from gnomemusic.widgets.disclistboxwidget import DiscBox
from gnomemusic.widgets.songwidget import SongWidget
import gnomemusic.utils as utils


@Gtk.Template(resource_path='/org/gnome/Music/ui/ArtistAlbumWidget.ui')
class ArtistAlbumWidget(Gtk.Box):

    __gtype_name__ = 'ArtistAlbumWidget'

    _album_box = Gtk.Template.Child()
    _cover_stack = Gtk.Template.Child()
    _disc_list_box = Gtk.Template.Child()
    _title = Gtk.Template.Child()
    _year = Gtk.Template.Child()

    selection_mode = GObject.Property(type=bool, default=False)

    __gsignals__ = {
        "song-activated": (GObject.SignalFlags.RUN_FIRST, None, (SongWidget, )),
    }

    def __repr__(self):
        return '<ArtistAlbumWidget>'

    def __init__(
            self, corealbum, selection_mode_allowed, size_group=None,
            cover_size_group=None, window=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)

        self._size_group = size_group
        self._cover_size_group = cover_size_group

        self._selection_mode = False
        self._selection_mode_allowed = selection_mode_allowed

        self._cover_stack.props.size = Art.Size.MEDIUM
        self._cover_stack.update(corealbum.props.media)

        allowed = self._selection_mode_allowed
        self._disc_list_box.props.selection_mode_allowed = allowed

        self.bind_property(
            'selection-mode', self._disc_list_box, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        self._title.props.label = corealbum.props.title
        year = corealbum.props.year
        if year:
            self._year.props.label = year

        if self._size_group:
            self._size_group.add_widget(self._album_box)

        if self._cover_size_group:
            self._cover_size_group.add_widget(self._cover_stack)

        self._disc_list_box.bind_model(
            corealbum.props.model, self._create_widget)

        def non_selectable(child):
            child.props.selectable = False

        self._disc_list_box.forall(non_selectable)

    def _create_widget(self, disc):
        disc_box = self._create_disc_box(disc.props.disc_nr, disc.model)

        return disc_box

    def _create_disc_box(self, disc_nr, album_model):
        disc_box = DiscBox(None, album_model)
        disc_box.set_disc_number(disc_nr)
        disc_box.props.show_durations = False
        disc_box.props.show_favorites = False
        disc_box.props.show_song_numbers = True
        disc_box.connect('song-activated', self._song_activated)

        return disc_box

    def _song_activated(self, widget, song_widget):
        if self.props.selection_mode:
            return

        self.emit("song-activated", song_widget)

    @log
    def select_all(self):
        """Select all items"""
        self._disc_list_box.select_all()

    @log
    def select_none(self):
        """Deselect all items"""
        self._disc_list_box.select_none()

    @log
    def get_selected_songs(self):
        """Return a list of selected songs."""
        items = self._disc_list_box.get_selected_items()
        return items
