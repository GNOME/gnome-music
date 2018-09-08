# Copyright © 2018 The GNOME Music Developers
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

from gettext import gettext as _
from gi.repository import GObject, Gtk

from gnomemusic import log
from gnomemusic.albumartcache import Art
from gnomemusic.gstplayer import Playback
from gnomemusic.player import RepeatMode
from gnomemusic.widgets.coverstack import CoverStack  # noqa: F401
from gnomemusic.widgets.smoothscale import SmoothScale  # noqa: F401
from gnomemusic.widgets.twolinetip import TwoLineTip
import gnomemusic.utils as utils


@Gtk.Template(resource_path='/org/gnome/Music/ui/PlayerToolbar.ui')
class PlayerToolbar(Gtk.ActionBar):
    """Main Player widget object

    Contains the ui of playing a song with Music.
    """

    __gsignals__ = {
        'thumbnail-updated': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    __gtype_name__ = 'PlayerToolbar'

    _artist_label = Gtk.Template.Child()
    _cover_stack = Gtk.Template.Child()
    _duration_label = Gtk.Template.Child()
    _next_button = Gtk.Template.Child()
    _pause_image = Gtk.Template.Child()
    _play_button = Gtk.Template.Child()
    _play_image = Gtk.Template.Child()
    _prev_button = Gtk.Template.Child()
    _progress_scale = Gtk.Template.Child()
    _progress_time_label = Gtk.Template.Child()
    _repeat_image = Gtk.Template.Child()
    _song_info_box = Gtk.Template.Child()
    _title_label = Gtk.Template.Child()

    def __repr__(self):
        return '<PlayerToolbar>'

    @log
    def __init__(self, player):
        super().__init__()

        self._player = player
        self._progress_scale.props.player = self._player

        self._cover_stack.props.size = Art.Size.XSMALL
        self._cover_stack.connect('updated', self._on_cover_stack_updated)

        self._tooltip = TwoLineTip()

        self._sync_repeat_image()

        self._player.connect('clock-tick', self._on_clock_tick)
        self._player.connect('song-changed', self._update_view)
        self._player.connect('prev-next-invalidated', self._sync_prev_next)
        self._player.connect('notify::repeat-mode', self._sync_repeat_image)
        self._player.connect('notify::state', self._sync_playing)

    @Gtk.Template.Callback()
    @log
    def _on_progress_value_changed(self, progress_scale):
        seconds = int(progress_scale.get_value() / 60)
        self._progress_time_label.set_label(utils.seconds_to_string(seconds))

    @log
    def _on_cover_stack_updated(self, klass):
        self.emit('thumbnail-updated')

    @Gtk.Template.Callback()
    @log
    def _on_prev_button_clicked(self, button):
        self._player.previous()

    @Gtk.Template.Callback()
    @log
    def _on_play_button_clicked(self, button):
        self._player.play_pause()

    @Gtk.Template.Callback()
    @log
    def _on_next_button_clicked(self, button):
        self._player.next()

    @log
    def _sync_repeat_image(self, player=None, param=None):
        icon = None
        repeat_mode = self._player.props.repeat_mode
        if repeat_mode == RepeatMode.NONE:
            icon = 'media-playlist-consecutive-symbolic'
        elif repeat_mode == RepeatMode.SHUFFLE:
            icon = 'media-playlist-shuffle-symbolic'
        elif repeat_mode == RepeatMode.ALL:
            icon = 'media-playlist-repeat-symbolic'
        elif repeat_mode == RepeatMode.SONG:
            icon = 'media-playlist-repeat-song-symbolic'

        self._repeat_image.set_from_icon_name(icon, Gtk.IconSize.MENU)

    @log
    def _sync_playing(self, player, state):
        self.show()

        if self._player.props.state == Playback.PLAYING:
            image = self._pause_image
            tooltip = _("Pause")
        else:
            image = self._play_image
            tooltip = _("Play")

        if self._play_button.get_image() != image:
            self._play_button.set_image(image)

        self._play_button.set_tooltip_text(tooltip)

    @log
    def _sync_prev_next(self, player=None):
        self._next_button.props.sensitive = self._player.props.has_next
        self._prev_button.props.sensitive = self._player.props.has_previous

    @log
    def _update_view(self, player, position):
        """Updates model when the song changes

        :param Player player: The main player object
        :param int position: current song position
        """
        current_song = player.props.current_song
        self._duration_label.set_label(
            utils.seconds_to_string(current_song.get_duration()))

        self._play_button.set_sensitive(True)
        self._sync_prev_next()

        artist = utils.get_artist_name(current_song)
        title = utils.get_media_title(current_song)

        self._title_label.props.label = title
        self._artist_label.props.label = artist

        self._tooltip.props.title = title
        self._tooltip.props.subtitle = artist

        self._cover_stack.update(current_song)

    @log
    def _on_clock_tick(self, player, seconds):
        self._progress_time_label.set_label(utils.seconds_to_string(seconds))

    @Gtk.Template.Callback()
    @log
    def _on_tooltip_query(self, widget, x, y, kb, tooltip, data=None):
        tooltip.set_custom(self._tooltip)

        return True
