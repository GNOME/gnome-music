# Copyright (C) 2018 Felipe Borges felipeborges@gnome.org
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

from gi.repository import Gio, GObject, Gtk

from gnomemusic.albumartcache import ArtSize
import gnomemusic.utils as utils

class PlaybackItem(GObject.Object):
    def __init__(self, data, iter):
        super().__init__()

        self.media = data[5]
        self.iter = iter
        self.title = utils.get_media_title(self.media)
        self.artist = utils.get_artist_name(self.media)


class PlaybackEntry(Gtk.ListBoxRow):
    def __init__(self, item, player):
        super().__init__()

        self.iter = item.iter

        grid = Gtk.Grid(border_width=5, column_spacing=5, row_spacing=2)
        self.add(grid)

        self.cover = Gtk.Image()
        artistLabel = Gtk.Label(label=item.artist, halign=Gtk.Align.START)
        artistLabel.get_style_context().add_class('dim-label')

        grid.attach(self.cover, 1, 0, 1, 2)
        grid.attach(Gtk.Label(label=item.title, halign=Gtk.Align.START), 2, 0, 1, 1)
        grid.attach(artistLabel, 2, 1, 1, 1)

        player.cache.lookup(item.media, ArtSize.SMALL, self._on_cache_lookup, None)

        self.show_all()

    def _on_cache_lookup(self, surface, data=None):
        self.cover.set_from_surface(surface)

class PlaybackPopover(Gtk.Popover):

    __gsignals__ = {
        'current-changed': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.TreeIter,)),
    }

    def __repr__(self):
        return '<PlaybackPopover>'

    def __init__(self, button, player):
        super().__init__(relative_to = button)

        self._player = player

        self._setup_view ()

        self._player.connect('playlist-item-changed', self._update_model)
        button.connect('toggled', self._on_button_toggled)

    def _setup_view(self):
        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Music/PlaybackPopover.ui')

        self.add(self._ui.get_object('playback_popover'))
        self._trackList = self._ui.get_object('playback_popover_list')
        self._model = Gio.ListStore()
        def create_popover_entry(item, user_data):
            return PlaybackEntry(item, user_data)
        self._trackList.bind_model(self._model, create_popover_entry, self._player)
        self._trackList.connect('row-activated', self._on_row_activated)

    def _on_row_activated(self, box, row):
        self.emit('current-changed', row.iter)

    def _update_model(self, player, playlist, current_iter):
        self._model.remove_all()
        while current_iter != None:
            item = PlaybackItem(playlist[current_iter], current_iter)
            self._model.append(item)
            current_iter = playlist.iter_next(current_iter)

    def _on_button_toggled(self, button):
        self.popup()
