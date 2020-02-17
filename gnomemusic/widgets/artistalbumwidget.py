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

from gnomemusic.albumartcache import Art
from gnomemusic.musiclogger import MusicLogger
from gnomemusic.widgets.disclistboxwidget import DiscBox
from gnomemusic.widgets.songwidget import SongWidget


@Gtk.Template(resource_path='/org/gnome/Music/ui/ArtistAlbumWidget.ui')
class ArtistAlbumWidget(Gtk.Box):
    """"Widget containing one album by an artist

    The album cover and some information on one side and a
    DiscListBox (list of all discs of the album) on the other side.
    """

    __gtype_name__ = 'ArtistAlbumWidget'

    _album_box = Gtk.Template.Child()
    _cover_stack = Gtk.Template.Child()
    _disc_list_box = Gtk.Template.Child()
    _title_year = Gtk.Template.Child()

    selection_mode = GObject.Property(type=bool, default=False)

    __gsignals__ = {
        "song-activated": (
            GObject.SignalFlags.RUN_FIRST, None, (SongWidget, )
        ),
    }

    def __init__(self, corealbum, size_group=None, cover_size_group=None):
        """Initialize the ArtistAlbumWidget

        :param CoreAlbum corealbum: The CoreAlbum object
        :param GtkSizeGroup size_group: SizeGroup for the discs
        :param GtkSizeGroup cover_size_group: SizeGroup for the cover
        """
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)

        self._corealbum = corealbum

        self._log = MusicLogger()

        self._size_group = size_group
        self._cover_size_group = cover_size_group

        self._selection_mode = False

        self._cover_stack.props.size = Art.Size.MEDIUM
        self._cover_stack.update(corealbum)

        self.bind_property(
            'selection-mode', self._disc_list_box, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        self._title_year.props.label = corealbum.props.title
        year = corealbum.props.year
        if year != "----":
            self._title_year.props.label += " ({})".format(year)

        if self._size_group:
            self._size_group.add_widget(self._album_box)

        if self._cover_size_group:
            self._cover_size_group.add_widget(self._cover_stack)

        self._disc_list_box.bind_model(
            corealbum.props.model, self._create_widget)
        corealbum.props.model.connect_after(
            "items-changed", self._on_model_items_changed)

        corealbum.props.model.items_changed(0, 0, 0)

    def _create_widget(self, disc):
        disc_box = self._create_disc_box(disc.props.disc_nr, disc.model)

        self._disc_list_box.bind_property(
            "selection-mode", disc_box, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        self._log.message(
            "Creating disc_box '{}' for disc '{}' in model {}".format(
                self._corealbum.props.title, disc.props.disc_nr,
                self._corealbum.props.model))
        return disc_box

    def _create_disc_box(self, disc_nr, album_model):
        disc_box = DiscBox(album_model)
        disc_box.set_disc_number(disc_nr)
        disc_box.props.show_durations = True
        disc_box.props.show_favorites = True
        disc_box.props.show_song_numbers = True
        disc_box.connect('song-activated', self._song_activated)

        return disc_box

    def _on_model_items_changed(self, model, position, removed, added):
        self._log.message("items-changed for model {}: {} {} {}".format(
            model, position, removed, added))
        n_items = model.get_n_items()
        self._log.message("n-items {} for '{}' by '{}'".format(
            n_items, self._corealbum.props.title,
            self._corealbum.props.artist))
        for i in range(n_items):
            discbox = self._disc_list_box.get_row_at_index(i)
            discbox.props.show_disc_label = (n_items > 1)

    def _song_activated(self, widget, song_widget):
        if self.props.selection_mode:
            return

        self.emit("song-activated", song_widget)

    def select_all(self):
        """Select all items"""
        self._disc_list_box.select_all()

    def deselect_all(self):
        """Deselect all items"""
        self._disc_list_box.deselect_all()
