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

from gnomemusic import log
from gnomemusic.albumartcache import Art
import gnomemusic.utils as utils

TRACK_LIST_LENGTH = 10

class PlaybackItem(GObject.Object):
    """Metadata of a track"""

    def __repr__(self):
        return '<PlaybackItem>'

    @log
    def __init__(self, data, iter):
        super().__init__()

        self.media = data[5]
        self.iter = iter
        self.title = utils.get_media_title(self.media)
        self.artist = utils.get_artist_name(self.media)


class PlaybackEntry(Gtk.ListBoxRow):
    """Widget that shows track metadata"""

    def __repr__(self):
        return '<PlaybackEntry>'

    def __init__(self, item, popover):
        super().__init__()

        self.iter = item.iter

        grid = Gtk.Grid(border_width=5, column_spacing=5, row_spacing=2)
        self.add(grid)

        if (self.iter == popover.current_iter):
            indicator = Gtk.Image.new_from_icon_name('media-playback-start-symbolic', Gtk.IconSize.BUTTON)
            indicator.valign = Gtk.Align.CENTER
        else:
            indicator = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            indicator.set_size_request(16, 16)

        grid.attach(indicator, 0, 0, 1, 2)

        self._cover = Gtk.Image()
        artist_label = Gtk.Label(label=item.artist, halign=Gtk.Align.START)
        artist_label.get_style_context().add_class('dim-label')

        grid.attach(self._cover, 1, 0, 1, 2)
        grid.attach(Gtk.Label(label=item.title, halign=Gtk.Align.START), 2, 0, 1, 1)
        grid.attach(artist_label, 2, 1, 1, 1)

        art = Art(Art.Size.SMALL, item.media, grid.get_scale_factor())
        self._handler_id = art.connect('finished', self._on_cache_lookup)
        art.lookup()

        self.show_all()

    @log
    def _on_cache_lookup(self, klass):
        klass.disconnect(self._handler_id)
        self._cover.set_from_surface(klass.surface)

class PlaybackPopover(Gtk.Popover):
    """Popover showing the following tracks in the current playlist"""
    current_iter = None

    __gsignals__ = {
        'current-changed': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.TreeIter,)),
    }

    def __repr__(self):
        return '<PlaybackPopover>'

    @log
    def __init__(self, button, player):
        super().__init__(relative_to = button)

        self.player = player

        self._setup_view ()

        self.player.connect('playlist-item-changed', self._update_model)
        button.connect('toggled', self._on_button_toggled)

        self._previous_track = None

    @log
    def _setup_view(self):
        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Music/PlaybackPopover.ui')

        self.add(self._ui.get_object('playback_popover'))
        self._track_list = self._ui.get_object('playback_popover_list')
        self._model = Gio.ListStore()

        def create_popover_entry(item, user_data):
            return PlaybackEntry(item, user_data)

        self._track_list.bind_model(self._model, create_popover_entry, self)
        self._track_list.connect('row-activated', self._on_row_activated)

    @log
    def _on_row_activated(self, box, row):
        self.emit('current-changed', row.iter)

    @log
    def _update_model(self, player, playlist, current_iter):
        self._model.remove_all()

        self.current_iter = current_iter;
        if (self._previous_track is not None):
            self._model.insert(0, self._previous_track)

        iter = current_iter
        for count in range(0, TRACK_LIST_LENGTH):
            if iter == None:
                break

            item = PlaybackItem(playlist[iter], iter)
            self._model.append(item)
            iter = playlist.iter_next(iter)

        self._previous_track = PlaybackItem(playlist[current_iter], current_iter)

    @log
    def _on_button_toggled(self, button):
        self.popup()
