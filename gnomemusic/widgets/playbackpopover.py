# Copyright 2020 The GNOME Music developers
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
from gettext import gettext as _

from gi.repository import GObject, Gtk

from gnomemusic.coreartist import CoreArtist
from gnomemusic.coresong import CoreSong
from gnomemusic.player import PlayerPlaylist
from gnomemusic.widgets.albumwidget import AlbumWidget
from gnomemusic.widgets.repeatbox import RepeatBox
from gnomemusic.widgets.songwidget import WidgetState
from gnomemusic.widgets.twolinewidget import TwoLineWidget


@Gtk.Template(resource_path="/org/gnome/Music/ui/LinearPlaybackWidget.ui")
class LinearPlaybackWidget(Gtk.ScrolledWindow):

    __gtype_name__ = "LinearPlaybackWidget"

    _listbox = Gtk.Template.Child()

    _current_index = 0
    _playlist_type = None
    _playlist_id = None
    _window_height = 0.0
    _row_height = 0.0

    def __init__(self, application):
        """Instantiate LinearPlaybackWidget

        :param Application application: Application object
        """
        super().__init__()

        self._player = application.props.player

        coremodel = application.props.coremodel
        self._model = coremodel.props.playlist_recent
        self._listbox.bind_model(self._model, self._create_twoline_widget)

        self.props.vadjustment.connect(
            "changed", self._vertical_adjustment_changed)

    def _create_twoline_widget(self, coresong):
        row = TwoLineWidget(coresong)
        return row

    def _vertical_adjustment_changed(self, klass):
        v_adjust = self.props.vadjustment
        if v_adjust.props.upper != self._window_height:
            self._window_height = v_adjust.props.upper
            self._row_height = self._window_height / len(self._listbox)
            v_adjust.props.value = (self._current_index * self._row_height
                                    + self._row_height / 2
                                    - v_adjust.props.page_size / 2)

    @Gtk.Template.Callback()
    def _on_row_activated(self, klass, row):
        coresong = row.props.coresong
        current_coresong = self._player.props.current_song
        self._player.play(coresong)
        current_coresong.props.state = WidgetState.PLAYED
        coresong.props.state = WidgetState.PLAYING


@Gtk.Template(resource_path="/org/gnome/Music/ui/PlaybackPopover.ui")
class PlaybackPopover(Gtk.Popover):
    """Popover showing the following tracks in the current playlist"""

    __gtype_name__ = "PlaybackPopover"

    _headerbar = Gtk.Template.Child()
    _main_box = Gtk.Template.Child()

    class Mode(IntEnum):
        """Playback mode"""
        LINEAR = 0
        ALBUM = 1

    def __init__(self, application):
        """Instantiate LinearPlaybackWidget

        :param Application application: Application object
        """
        super().__init__()

        self._coremodel = application.props.coremodel
        self._coremodel.connect("playlist-loaded", self._on_playlist_changed)

        player = application.props.player
        self._album_wiget = AlbumWidget(application, AlbumWidget.Mode.PLAYBACK)
        self._main_box.add(self._album_wiget)

        self._linear_playback = LinearPlaybackWidget(application)
        self._main_box.add(self._linear_playback)

        repeat_box = RepeatBox(player)
        self._main_box.add(repeat_box)

        self._playlist_type = None
        self._mode = PlaybackPopover.Mode.LINEAR
        self._set_linear_mode()

    @GObject.Property(type=int, default=0, minimum=0, maximum=1)
    def mode(self):
        """Get the playback mode

        :returns: The view state
        :rtype: int
        """
        return self._mode

    @mode.setter
    def mode(self, value):
        """Set the playback mode

        :param int value: new playback mode
        """
        self._mode = value
        if self._mode == PlaybackPopover.Mode.LINEAR:
            self._set_linear_mode()
        elif self._mode == PlaybackPopover.Mode.ALBUM:
            self._set_album_mode()

    def _set_linear_mode(self):
        self._album_wiget.hide()
        self._linear_playback.show()

    def _set_album_mode(self):
        self._linear_playback.hide()
        self._album_wiget.update(self._coremodel.props.active_media)
        self._album_wiget.show()

    def _on_playlist_changed(self, coremodel, playlist_type):
        self._playlist_type = playlist_type
        if playlist_type == PlayerPlaylist.Type.ALBUM:
            self.props.mode = PlaybackPopover.Mode.ALBUM
        else:
            self.props.mode = PlaybackPopover.Mode.LINEAR

        active_media = self._coremodel.props.active_media
        if isinstance(active_media, CoreSong):
            pl_title = _("Songs")
        elif isinstance(active_media, CoreArtist):
            pl_title = active_media.props.artist
        else:
            pl_title = active_media.props.title

        title = _("Playing {}".format(pl_title))
        self._headerbar.props.title = title
