# Copyright 2018 The GNOME Music Developers
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

from gi.repository import Gdk, GObject, Gtk

from gnomemusic import log
from gnomemusic.albumartcache import Art
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists
import gnomemusic.utils as utils


@Gtk.Template(resource_path="/org/gnome/Music/SmartPlaylistWidget.ui")
class SmartPlaylistWidget(Gtk.Box):
    """

    """

    __gtype_name__ = "SmartPlaylistWidget"

    _flowbox = Gtk.Template.Child()

    def __repr__(self):
        return '<SmartPlaylistWidget>'

    @log
    def __init__(self):
        super().__init__()
        self.show_all()

    @log
    def add_playlist(self, playlist):
        child = SmartPlaylistCover(playlist)
        child.connect('play-request', self._on_play_request)
        self._flowbox.add(child)

    @log
    def _on_play_request(self, flowbox_child):
        for child in self._flowbox:
            if (child.props.playing
                    and child != flowbox_child):
                child.stop()
                break


@Gtk.Template(resource_path="/org/gnome/Music/SmartPlaylistCover.ui")
class SmartPlaylistCover(Gtk.FlowBoxChild):
    """

    """

    __gsignals__ = {
        'play-request': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    _play_icon = 'media-playback-start-symbolic'
    _pause_icon = 'media-playback-pause-symbolic'

    __gtype_name__ = "SmartPlaylistCover"

    _events = Gtk.Template.Child()
    _image = Gtk.Template.Child()
    _title = Gtk.Template.Child()

    playing = GObject.Property(type=bool, default=False)

    def __repr__(self):
        return '<SmartPlaylistCover>'

    @log
    def __init__(self, playlist):
        super().__init__()
        self._songs = []
        grilo.populate_playlist_songs(playlist, self._add_song)

        self._title.props.label = utils.get_media_title(playlist)

        self._image.override_background_color(
            Gtk.StateType.NORMAL, Gdk.RGBA(0., 0., 0., 1.))
        self._image.props.width_request = Art.Size.MEDIUM.width / 2
        self._image.props.height_request = Art.Size.MEDIUM.height / 2

        self._events.override_background_color(
            Gtk.StateType.NORMAL, Playlists.get_color(playlist.get_id()))
        self._events.props.width_request = Art.Size.MEDIUM.width
        self._events.props.height_request = Art.Size.MEDIUM.height
        self._events.add_events(Gdk.EventMask.TOUCH_MASK)

        self.stop()
        self.show_all()

    @log
    def _add_song(self, source, param, song, remaining=0, data=None):
        if remaining != 0:
            self._songs.append(song)

    @Gtk.Template.Callback()
    @log
    def _on_smartplaylist_hover(self, widget, event):
        if self.props.playing:
            self._image.props.icon_name = self._pause_icon
        self._image.props.opacity = 0.8

    @Gtk.Template.Callback()
    @log
    def _on_smartplaylist_unhover(self, widget, event):
        if self.props.playing:
            self._image.props.icon_name = self._play_icon
        else:
            self._image.props.opacity = 0.0

    @Gtk.Template.Callback()
    @log
    def _on_smartplaylist_pressed(self, widget, event):
        self.props.playing = True
        self.emit('play-request')

    @log
    def stop(self):
        self.props.playing = False
        self._image.props.icon_name = self._play_icon
        self._image.props.opacity = 0.0
