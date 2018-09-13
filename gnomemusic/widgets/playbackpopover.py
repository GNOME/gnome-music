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

from __future__ import annotations
import typing

from gi.repository import Gfm, Gtk

from gnomemusic.utils import SongState
from gnomemusic.widgets.twolinewidget import TwoLineWidget
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.coremodel import CoreModel
    from gnomemusic.coresong import CoreSong
    from gnomemusic.player import Player


@Gtk.Template(resource_path="/org/gnome/Music/ui/LinearPlaybackWidget.ui")
class LinearPlaybackWidget(Gtk.ScrolledWindow):

    __gtype_name__ = "LinearPlaybackWidget"

    _listbox = Gtk.Template.Child()

    _current_index: int = 0
    _window_height: float = 0.0
    _row_height: float = 0.0

    def __init__(self, application: Application) -> None:
        """Instantiate LinearPlaybackWidget

        :param Application application: Application object
        """
        super().__init__()

        self._player: Player = application.props.player

        coremodel: CoreModel = application.props.coremodel
        self._model: Gfm.SliceListModel = coremodel.props.recent_playlist
        self._listbox.bind_model(self._model, self._create_twoline_widget)

        self.props.vadjustment.connect(
            "changed", self._vertical_adjustment_changed)

    def _create_twoline_widget(self, coresong: CoreSong) -> TwoLineWidget:
        row: TwoLineWidget = TwoLineWidget(coresong)
        return row

    def _vertical_adjustment_changed(self, klass: Gtk.Adjustment) -> None:
        v_adjust: Gtk.Adjustment = self.props.vadjustment
        if v_adjust.props.upper != self._window_height:
            self._window_height = v_adjust.props.upper
            self._row_height = self._window_height / len(self._listbox)
            v_adjust.props.value = (self._current_index * self._row_height
                                    + self._row_height / 2
                                    - v_adjust.props.page_size / 2)

    @Gtk.Template.Callback()
    def _on_row_activated(
            self, klass: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        coresong: CoreSong = row.props.coresong
        current_coresong: CoreSong = self._player.props.current_song
        self._player.play(coresong)
        current_coresong.props.state = SongState.PLAYED
        coresong.props.state = SongState.PLAYING
