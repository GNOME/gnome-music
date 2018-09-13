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

from gi.repository import Gtk

from gnomemusic.utils import SongState
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
        self._model = coremodel.props.recent_playlist
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
        current_coresong.props.state = SongState.PLAYED
        coresong.props.state = SongState.PLAYING
