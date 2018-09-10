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

from gi.repository import GObject, Gtk
from gettext import gettext as _

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.player import PlayerPlaylist
from gnomemusic.widgets.albumwidget import AlbumWidget
from gnomemusic.widgets.repeatbox import RepeatBox
from gnomemusic.widgets.songwidget import WidgetState, TwoLineWidget
import gnomemusic.utils as utils


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

        # new_index = -1
        # for index, row in enumerate(self._listbox):
        #     if row.props.song_id == current_song.get_id():
        #         new_index = index
        #         break

        # # Recent PlayerPlaylist has completely changed.
        # # Completely refresh it.
        # if new_index == -1:
        #     self.update()
        #     return

        # playing_row.props.state = WidgetState.PLAYED
        # new_row = self._listbox.get_row_at_index(new_index)
        # new_row.props.state = WidgetState.PLAYING

        # new_songs = self._player.get_mpris_playlist()
        # for song in new_songs[10-new_index:]:
        #     row = TwoLineWidget(song, WidgetState.UNPLAYED)
        #     self._listbox.add(row)

        # self._current_index = new_index

    @log
    def _on_repeat_changed(self, klass, param):
        self.update()

    @log
    def _on_row_activated(self, klass, row):
        index = row.get_index()
        self._player.play(index - self._current_index)


@Gtk.Template(resource_path='/org/gnome/Music/ui/PlaybackPopover.ui')
class PlaybackPopover(Gtk.Popover):
    """Popover showing the following tracks in the current playlist"""

    __gtype_name__ = 'PlaybackPopover'

    __gsignals__ = {
        'current-changed':
        (GObject.SignalFlags.RUN_FIRST, None, (Gtk.TreeIter,)),
    }

    _headerbar = Gtk.Template.Child()
    _main_box = Gtk.Template.Child()

    def __repr__(self):
        return '<PlaybackPopover>'

    @log
    def __init__(self, player, button):
        super().__init__(relative_to=button)

        self._player = player
        button.connect('toggled', self._on_button_toggled)
        self._player.connect('playlist-changed', self._on_playlist_changed)

        self._album_playback = AlbumWidget(
            player, self, AlbumWidget.Mode.PLAYBACK)
        self._main_box.add(self._album_playback)

        self._linear_playback = LinearPlaybackWindow(self._player)
        self._main_box.add(self._linear_playback)

        repeat_box = RepeatBox(self._player)
        self._main_box.add(repeat_box)

    @log
    def _on_button_toggled(self, klass):
        self.popup()

    @log
    def _set_title(self, title_suffix):
        header = _("Playing")
        self._headerbar.props.title = header + " " + title_suffix

    @log
    def _display_album_widget(self, source, param, item, count, error, data):
        if not item:
            return

        self._album_playback.update(item)
        self._set_title(utils.get_album_title(item))
        self._linear_playback.hide()
        self._album_playback.show()

    @log
    def _update_playlist_title(self, source, param, item, count, error, data):
        if not item:
            return
        self._set_title(utils.get_media_title(item))

    @log
    def _update_linear_mode_title(self):
        playlist_type = self._player.get_playlist_type()
        if playlist_type == PlayerPlaylist.Type.PLAYLIST:
            pl_id = self._player.get_playlist_id()
            grilo.get_playlist_with_id(pl_id, self._update_playlist_title)
        elif playlist_type == PlayerPlaylist.Type.ARTIST:
            self._set_title(self._player.get_playlist_id())
        else:
            self._set_title(_("Songs"))

    @log
    def _on_playlist_changed(self, klass, data=None):
        playlist_type = self._player.get_playlist_type()
        linear_playlists = [
                            PlayerPlaylist.Type.ARTIST,
                            PlayerPlaylist.Type.PLAYLIST,
                            PlayerPlaylist.Type.SONGS]

        if playlist_type == PlayerPlaylist.Type.ALBUM:
            album_id = self._player.get_playlist_id()
            grilo.get_album_with_id(album_id, self._display_album_widget)

        elif playlist_type in linear_playlists:
            self._album_playback.hide()
            self._linear_playback.update()
            self._update_linear_mode_title()
            self._linear_playback.show()

        else:
            self._album_playback.hide()
            self._linear_playback.hide()
