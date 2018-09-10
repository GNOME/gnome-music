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

from gnomemusic.player import RepeatMode


@Gtk.Template(resource_path="/org/gnome/Music/ui/RepeatBox.ui")
class RepeatBox(Gtk.Box):

    __gtype_name__ = "RepeatBox"

    _linear_mode_button = Gtk.Template.Child()
    _shuffle_mode_button = Gtk.Template.Child()
    _repeat_all_mode_button = Gtk.Template.Child()
    _repeat_song_mode_button = Gtk.Template.Child()

    def __init__(self, player):
        """Initialize the object

        :param Player player: Player object
        """
        super().__init__()

        self._player = player
        self._player.connect(
            "notify::repeat-mode", self._on_repeat_mode_changed)

        self._buttons = {
            self._linear_mode_button: RepeatMode.NONE,
            self._shuffle_mode_button: RepeatMode.SHUFFLE,
            self._repeat_all_mode_button: RepeatMode.ALL,
            self._repeat_song_mode_button: RepeatMode.SONG
        }
        self._on_repeat_mode_changed(self._player)

    def _on_repeat_mode_changed(self, klass, param=None):
        repeat_mode = self._player.props.repeat_mode
        button_index = list(self._buttons.values()).index(repeat_mode)
        button = list(self._buttons.keys())[button_index]
        self._activate_button(button)

    @Gtk.Template.Callback()
    def _repeat_button_clicked(self, klass):
        self._activate_button(klass)
        self._player.props.repeat_mode = self._buttons[klass]

    def _activate_button(self, button_to_activate):
        for button in self._buttons:
            button.handler_block_by_func(self._repeat_button_clicked)
            if (button != button_to_activate
                    and button.props.active):
                button.props.active = False

        button_to_activate.props.active = True

        for button in self._buttons:
            button.handler_unblock_by_func(self._repeat_button_clicked)
