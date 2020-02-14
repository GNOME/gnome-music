# Copyright 2020 The GNOME Music Developers
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

from gnomemusic.albumartcache import Art
from gnomemusic.grilowrappers.grltrackerplaylists import SmartPlaylist
from gnomemusic.player import PlayerPlaylist


@Gtk.Template(resource_path="/org/gnome/Music/ui/SmartPlaylistCover.ui")
class SmartPlaylistCover(Gtk.FlowBoxChild):
    """ A smart playlist cover is a widget which displays
        the playlist name and its icon.
        A play or pause icon is displayed if the playlist
        is playing or if the pointer is above it.
    """

    __gtype_name__ = "SmartPlaylistCover"

    _play_icon = "media-playback-start-symbolic"
    _pause_icon = "media-playback-pause-symbolic"

    class State(IntEnum):
        STOPPED = 0
        PAUSED = 1
        PLAYING = 2

    _click_ctrlr = Gtk.Template.Child()
    _overlay = Gtk.Template.Child()
    _bg_image = Gtk.Template.Child()
    _fg_image = Gtk.Template.Child()
    _title = Gtk.Template.Child()
    _motions_ctrlr = Gtk.Template.Child()

    state = GObject.Property(type=int, default=0)

    def __init__(self, smart_playlist, coremodel, player):
        """Initialize the cover.

        :param SmartPlaylit smart_playlist: the smart playlist to use
        :param CoreModel coremodel: the CoreModel object
        :param Player player: The Player object
        """
        super().__init__()

        self._coremodel = coremodel
        self._player = player

        self._playlist = smart_playlist

        self._title.props.label = smart_playlist.props.title

        self._overlay.add_events(
            Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)

        self._bg_image.override_background_color(
            Gtk.StateType.NORMAL, smart_playlist.props.color)
        self._bg_image.props.width_request = Art.Size.MEDIUM.width
        self._bg_image.props.height_request = Art.Size.MEDIUM.height
        self._bg_image.props.icon_name = smart_playlist.props.icon_name

        self._fg_image.override_background_color(
            Gtk.StateType.NORMAL, Gdk.RGBA(0., 0., 0., 1.))
        self._fg_image.props.width_request = Art.Size.MEDIUM.width / 2
        self._fg_image.props.height_request = Art.Size.MEDIUM.height / 2

        self._hover = False
        self.connect("notify::state", self._on_state_changed)

        self._playlist.props.model.connect(
            "items-changed", self._on_model_items_changed)
        self.stop()

    def _on_model_items_changed(self, model, position, removed, added):
        self.set_visibility()

    def set_visibility(self):
        """Display the playlist if has some songs."""
        self.props.visible = self._playlist.props.model.get_n_items() > 0

    @Gtk.Template.Callback()
    def _on_smartplaylist_enter(self, ctrlr, x, y):
        self._hover = True
        self._on_state_changed(self)

    @Gtk.Template.Callback()
    def _on_smartplaylist_leave(self, ctrlr):
        self._hover = False
        self._on_state_changed(self)

    def _on_state_changed(self, klass, value=None):
        if self._hover is True:
            self._fg_image.props.opacity = 0.8
            if self.props.state == SmartPlaylistCover.State.PLAYING:
                self._fg_image.props.icon_name = self._pause_icon
            elif self.props.state == SmartPlaylistCover.State.PAUSED:
                self._fg_image.props.icon_name = self._play_icon
        else:
            if self.props.state == SmartPlaylistCover.State.PLAYING:
                self._fg_image.props.opacity = 0.8
                self._fg_image.props.icon_name = self._play_icon
            elif self.props.state == SmartPlaylistCover.State.PAUSED:
                self._fg_image.props.opacity = 0.8
                self._fg_image.props.icon_name = self._pause_icon
            else:
                self._fg_image.props.opacity = 0.0

    @Gtk.Template.Callback()
    def _on_smartplaylist_pressed(self, gesture, n_press, x, y):
        if self.props.state == SmartPlaylistCover.State.PAUSED:
            self._player.play()
            self.props.state = SmartPlaylistCover.State.PLAYING
            return
        elif self.props.state == SmartPlaylistCover.State.PLAYING:
            self._player.pause()
            self.props.state = SmartPlaylistCover.State.PAUSED
            return

        def _on_playlist_loaded(klass, playlist_type):
            self._player.play()
            self.props.state = SmartPlaylistCover.State.PLAYING
            self._coremodel.disconnect(signal_id)

        signal_id = self._coremodel.connect(
            "playlist-loaded", _on_playlist_loaded)
        self._coremodel.set_player_model(
            PlayerPlaylist.Type.PLAYLIST, self._playlist.props.model)

    @GObject.Property(
        type=SmartPlaylist, default=None, flags=GObject.ParamFlags.READABLE)
    def playlist(self):
        return self._playlist

    def stop(self):
        self.props.state = SmartPlaylistCover.State.STOPPED
        self._fg_image.props.icon_name = self._play_icon
        self._fg_image.props.opacity = 0.0
