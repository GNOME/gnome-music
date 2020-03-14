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

from gi.repository import GObject, Gtk

from gnomemusic.albumartcache import Art
from gnomemusic.coresong import CoreSong
from gnomemusic.utils import SongState


@Gtk.Template(resource_path="/org/gnome/Music/ui/TwoLineWidget.ui")
class TwoLineWidget(Gtk.ListBoxRow):

    __gtype_name__ = "TwoLineWidget"

    coresong = GObject.Property(type=CoreSong, default=None)

    _cover_stack = Gtk.Template.Child()
    _main_label = Gtk.Template.Child()
    _play_icon = Gtk.Template.Child()
    _secondary_label = Gtk.Template.Child()

    def __init__(self, coresong):
        """Instantiate a TwoLineWidget

        :param Corsong coresong: song associated with the widget
        """
        super().__init__()

        self.props.coresong = coresong

        self._main_label.props.label = coresong.props.title
        self._secondary_label.props.label = coresong.props.artist

        self._cover_stack.props.size = Art.Size.SMALL
        self._cover_stack.update(coresong)

        self.props.coresong.bind_property(
            "state", self, "state",
            GObject.BindingFlags.SYNC_CREATE)

    @GObject.Property
    def state(self):
        """State of the widget

        :returns: Widget state
        :rtype: SongState
        """
        return self._state

    @state.setter
    def state(self, value):
        """Set state of the of widget

        This influences the look of the widgets label and if there is a
        song play indicator being shown.

        :param SongState value: Song state
        """
        self._state = value

        main_style_ctx = self._main_label.get_style_context()
        secondary_style_ctx = self._secondary_label.get_style_context()

        main_style_ctx.remove_class("dim-label")
        main_style_ctx.remove_class("playing-song-label")
        secondary_style_ctx.remove_class("dim-label")
        self._play_icon.props.icon_name = ""

        if value == SongState.PLAYED:
            main_style_ctx.add_class("dim-label")
            secondary_style_ctx.add_class("dim-label")
        elif value == SongState.PLAYING:
            self._play_icon.props.icon_name = "media-playback-start-symbolic"
            main_style_ctx.add_class("playing-song-label")
