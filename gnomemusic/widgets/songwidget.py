# Copyright © 2018 The GNOME Music developers
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

from enum import IntEnum

from gi.repository import Gdk, GObject, Gtk

from gnomemusic import log
from gnomemusic import utils
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists, StaticPlaylists
from gnomemusic.widgets.starimage import StarImage  # noqa: F401


@Gtk.Template(resource_path='/org/gnome/Music/SongWidget.ui')
class SongWidget(Gtk.EventBox):
    """The single song widget used in DiscListBox

    Contains
     * play icon (depending on state)
     * selection check box (optional)
     * song number on disc (optional)
     * song title
     * song duration (optional)
     * favorite/star picker (optional)
    """

    __gtype_name__ = 'SongWidget'

    __gsignals__ = {
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    selected = GObject.Property(type=bool, default=False)

    _playlists = Playlists.get_default()

    _select_button = Gtk.Template.Child()
    _number_label = Gtk.Template.Child()
    _title_label = Gtk.Template.Child()
    _duration_label = Gtk.Template.Child()
    _star_eventbox = Gtk.Template.Child()
    _star_image = Gtk.Template.Child()
    _play_icon = Gtk.Template.Child()

    class State(IntEnum):
        """The state of the SongWidget
        """
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

        self.bind_property(
            'selected', self._select_button, 'active',
            GObject.BindingFlags.BIDIRECTIONAL)

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
        self._star_image.hover = True

    @Gtk.Template.Callback()
    @log
    def _on_star_unhover(self, widget, event):
        self._star_image.hover = False

    @GObject.Property(type=bool, default=False)
    @log
    def selection_mode(self):
        """Selection mode

        :returns: Selection mode
        :rtype: bool
        """
        return self._selection_mode

    @selection_mode.setter
    @log
    def selection_mode(self, value):
        """Set the selection mode

        :param bool value: Selection mode
        """
        self._selection_mode = value
        self._select_button.set_visible(value)

        if not value:
            self.selected = False

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
    def show_song_number(self):
        return self._number_label.get_visible()

    @show_song_number.setter
    @log
    def show_song_number(self, value):
        self._number_label.set_visible(value)

    @GObject.Property(type=bool, default=False)
    @log
    def show_favorite(self):
        return self._star_eventbox.get_visible()

    @show_favorite.setter
    @log
    def show_favorite(self, value):
        self._star_eventbox.set_visible(value)
        # TODO: disconnect signal handling?

    @GObject.Property(type=bool, default=False)
    @log
    def show_duration(self):
        return self._duration_label.get_visible()

    @show_duration.setter
    @log
    def show_duration(self, value):
        self._duration_label.set_visible(value)
