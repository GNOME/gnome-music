# Copyright 2019 The GNOME Music developers
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

from gi.repository import Gtk

from gnomemusic import log
from gnomemusic.widgets.songwidget import WidgetState, TwoLineWidget


@Gtk.Template(resource_path='/org/gnome/Music/ui/LinearPlaybackWindow.ui')
class LinearPlaybackWindow(Gtk.ScrolledWindow):

    __gtype_name__ = 'LinearPlaybackWindow'

    _listbox = Gtk.Template.Child()

    _current_index = 0
    _playlist_type = None
    _playlist_id = None
    _window_height = 0.0
    _row_height = 0.0

    def __repr__(self):
        return '<LinearPlaybackWindow>'

    @log
    def __init__(self, player):
        super().__init__()

        self._player = player
        self._player.connect('song-changed', self._on_song_changed)
        self._player.connect('notify::repeat-mode', self._on_repeat_changed)

        self._listbox.connect('row-activated', self._on_row_activated)

        self.props.vadjustment.connect(
            'changed', self._vertical_adjustment_changed)

    @log
    def _vertical_adjustment_changed(self, klass):
        v_adjust = self.props.vadjustment
        if v_adjust.props.upper != self._window_height:
            self._window_height = v_adjust.props.upper
            self._row_height = self._window_height / len(self._listbox)
            v_adjust.props.value = (self._current_index * self._row_height
                                    + self._row_height / 2
                                    - v_adjust.props.page_size / 2)

    @log
    def _init_listbox_rows(self):
        songs = self._player.get_mpris_playlist()
        for index, song in enumerate(songs):
            row = TwoLineWidget(song, WidgetState.UNPLAYED)
            self._listbox.add(row)

        last_song = songs[-1]
        for index in range(len(songs), 21):
            row = TwoLineWidget(last_song, WidgetState.UNPLAYED)
            self._listbox.add(row)
            row.hide()

    @log
    def update(self):
        self._playlist_type = self._player.get_playlist_type()
        self._playlist_id = self._player.get_playlist_id()

        if len(self._listbox) == 0:
            self._init_listbox_rows()

        current_song_id = self._player.props.current_song.get_id()
        songs = self._player.get_mpris_playlist()
        song_passed = False
        for index, song in enumerate(songs):
            state = WidgetState.PLAYED
            if song.get_id() == current_song_id:
                song_passed = True
                self._current_index = index
                state = WidgetState.PLAYING
            elif song_passed:
                # Counter intuitive, but this is due to call order.
                state = WidgetState.UNPLAYED
            row = self._listbox.get_row_at_index(index)
            row.update(song, state)
            row.show()

        for index in range(len(songs), 21):
            row = self._listbox.get_row_at_index(index)
            row.hide()

    @log
    def _on_song_changed(self, klass, position):
        if not self._player.playing_playlist(
                self._playlist_type, self._playlist_id):
            return

        current_song = self._player.props.current_song
        playing_row = self._listbox.get_row_at_index(self._current_index)
        if current_song.get_id() == playing_row.props.song_id:
            return

        self.update()

    @log
    def _on_repeat_changed(self, klass, param):
        self.update()

    @log
    def _on_row_activated(self, klass, row):
        index = row.get_index()
        self._player.play(index - self._current_index)
