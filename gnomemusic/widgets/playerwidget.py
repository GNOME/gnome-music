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
from gnomemusic.player import RepeatType
from gnomemusic.widgets.coverstack import CoverStack
from gnomemusic.widgets.smoothscale import SmoothScale  # noqa: F401
import gnomemusic.utils as utils


class PlayerWidget(GObject.GObject):
    """Main Player widget object

    Contains the ui of playing a song with Music.
    """

    __gsignals__ = {
        'thumbnail-updated': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __repr__(self):
        return '<PlayerWidget>'

    @log
    def __init__(self, player):
        super().__init__()

        self._player = player

        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Music/PlayerToolbar.ui')
        self.actionbar = self._ui.get_object('actionbar')
        self._prev_button = self._ui.get_object('previous_button')
        self._play_button = self._ui.get_object('play_button')
        self._next_button = self._ui.get_object('next_button')
        self._play_image = self._ui.get_object('play_image')
        self._pause_image = self._ui.get_object('pause_image')

        self._progress_scale = self._ui.get_object('smooth_scale')
        self._progress_scale.player = self._player

        self._progress_scale.connect('seek-finished', self._on_seek_finished)
        self._progress_scale.connect(
            'value-changed', self._on_progress_value_changed)

        self._progress_time_label = self._ui.get_object('playback')
        self._total_time_label = self._ui.get_object('duration')
        self._title_label = self._ui.get_object('title')
        self._artist_label = self._ui.get_object('artist')

        stack = self._ui.get_object('cover')
        self._cover_stack = CoverStack(stack, Art.Size.XSMALL)
        self._cover_stack.connect('updated', self._on_cover_stack_updated)

        self._repeat_button_image = self._ui.get_object('playlistRepeat')

        self._sync_repeat_image()

        self._prev_button.connect('clicked', self._on_prev_button_clicked)
        self._play_button.connect('clicked', self._on_play_button_clicked)
        self._next_button.connect('clicked', self._on_next_button_clicked)

        self._player.connect('clock-tick', self._on_clock_tick)
        self._player.connect('current-song-changed', self._update_view)
        self._player.connect('prev-next-invalidated', self._sync_prev_next)
        self._player.connect('repeat-mode-changed', self._sync_repeat_image)
        self._player.connect('state-changed', self._sync_playing)

    @log
    def _on_seek_finished(self, klass, time):
        self._player.play()

    @log
    def _on_progress_value_changed(self, progress_scale):
        seconds = int(progress_scale.get_value() / 60)
        self._progress_time_label.set_label(utils.seconds_to_string(seconds))

    @log
    def _on_cover_stack_updated(self, klass):
        self.emit('thumbnail-updated')

    @log
    def _on_prev_button_clicked(self, button):
        self._player.previous()

    @log
    def _on_play_button_clicked(self, button):
        if self._player.get_playback_status() == Playback.PLAYING:
            self._player.pause()
        else:
            self._player.play()

    @log
    def _on_next_button_clicked(self, button):
        self._player.next()

    @log
    def _sync_repeat_image(self, player=None):
        icon = None
        if self._player.repeat == RepeatType.NONE:
            icon = 'media-playlist-consecutive-symbolic'
        elif self._player.repeat == RepeatType.SHUFFLE:
            icon = 'media-playlist-shuffle-symbolic'
        elif self._player.repeat == RepeatType.ALL:
            icon = 'media-playlist-repeat-symbolic'
        elif self._player.repeat == RepeatType.SONG:
            icon = 'media-playlist-repeat-song-symbolic'

        self._repeat_button_image.set_from_icon_name(icon, Gtk.IconSize.MENU)

    @log
    def _sync_playing(self, player):
        self.actionbar.show()

        if self._player.get_playback_status() == Playback.PLAYING:
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
        self._next_button.set_sensitive(self._player.has_next())
        self._prev_button.set_sensitive(self._player.has_previous())

    @log
    def _update_view(self, player, playlist, current_iter):
        media = playlist[current_iter][player.Field.SONG]
        self._total_time_label.set_label(
            utils.seconds_to_string(media.get_duration()))

        self._play_button.set_sensitive(True)
        self._sync_prev_next()

        self._artist_label.set_label(utils.get_artist_name(media))
        self._title_label.set_label(utils.get_media_title(media))
        self._cover_stack.update(media)

    @log
    def _on_clock_tick(self, player, seconds):
        self._progress_time_label.set_label(utils.seconds_to_string(seconds))
