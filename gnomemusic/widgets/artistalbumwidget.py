# Copyright (c) 2016 The GNOME Music Developers
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

import logging

from gettext import gettext as _
from gi.repository import Gdk, Gio, GLib, GObject, Gtk

from gnomemusic import log
from gnomemusic.albumartcache import AlbumArtCache, DefaultIcon, ArtSize
from gnomemusic.grilo import grilo
from gnomemusic.player import DiscoveryStatus
from gnomemusic.playlists import Playlists
import gnomemusic.utils as utils

logger = logging.getLogger(__name__)

NOW_PLAYING_ICON_NAME = 'media-playback-start-symbolic'
ERROR_ICON_NAME = 'dialog-error-symbolic'

try:
    settings = Gio.Settings.new('org.gnome.Music')
    MAX_TITLE_WIDTH = settings.get_int('max-width-chars')
except Exception as e:
    MAX_TITLE_WIDTH = 20
    logger.error("Error on setting widget max-width-chars: %s", str(e))

playlists = Playlists.get_default()


class ArtistAlbumWidget(Gtk.Box):

    __gsignals__ = {
        'tracks-loaded': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __repr__(self):
        return '<ArtistAlbumWidget>'

    @log
    def __init__(self, artist, album, player, model, header_bar, selectionModeAllowed):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)

        scale = self.get_scale_factor()
        self._cache = AlbumArtCache(scale)
        self._loading_icon_surface = DefaultIcon(scale).get(
            DefaultIcon.Type.loading,
            ArtSize.large)

        self.player = player
        self.album = album
        self.artist = artist
        self.model = model
        self.model.connect('row-changed', self._model_row_changed)
        self.header_bar = header_bar
        self.selectionMode = False
        self.selectionModeAllowed = selectionModeAllowed
        self.songs = []
        self.ui = Gtk.Builder()
        self.ui.add_from_resource('/org/gnome/Music/ArtistAlbumWidget.ui')

        GLib.idle_add(self._update_album_art)

        self.cover = self.ui.get_object('cover')
        self.cover.set_from_surface(self._loading_icon_surface)
        self.songsGrid = self.ui.get_object('grid1')
        self.ui.get_object('title').set_label(album.get_title())
        if album.get_creation_date():
            self.ui.get_object('year').set_markup(
                '<span color=\'grey\'>(%s)</span>' %
                str(album.get_creation_date().get_year())
            )
        self.tracks = []
        grilo.populate_album_songs(album, self.add_item)
        self.pack_start(self.ui.get_object('ArtistAlbumWidget'), True, True, 0)

    @log
    def add_item(self, source, prefs, track, remaining, data=None):
        if remaining == 0:
            self.songsGrid.show_all()
            self.emit("tracks-loaded")

        if track:
            self.tracks.append(track)
        else:
            for i, track in enumerate(self.tracks):
                ui = Gtk.Builder()
                ui.add_from_resource('/org/gnome/Music/TrackWidget.ui')
                song_widget = ui.get_object('eventbox1')
                self.songs.append(song_widget)
                ui.get_object('num')\
                    .set_markup('<span color=\'grey\'>%d</span>'
                                % len(self.songs))
                title = utils.get_media_title(track)
                ui.get_object('title').set_text(title)
                ui.get_object('title').set_alignment(0.0, 0.5)
                ui.get_object('title').set_max_width_chars(MAX_TITLE_WIDTH)

                self.songsGrid.attach(
                    song_widget,
                    int(i / (len(self.tracks) / 2)),
                    int(i % (len(self.tracks) / 2)), 1, 1
                )
                track.song_widget = song_widget
                itr = self.model.append(None)
                song_widget._iter = itr
                song_widget.model = self.model
                song_widget.title = ui.get_object('title')
                song_widget.checkButton = ui.get_object('select')
                song_widget.checkButton.set_visible(self.selectionMode)
                song_widget.checkButton.connect(
                    'toggled', self._check_button_toggled, song_widget
                )
                self.model.set(itr,
                               [0, 1, 2, 3, 5],
                               [title, '', '', False, track])
                song_widget.now_playing_sign = ui.get_object('image1')
                song_widget.now_playing_sign.set_from_icon_name(
                    NOW_PLAYING_ICON_NAME,
                    Gtk.IconSize.SMALL_TOOLBAR)
                song_widget.now_playing_sign.set_no_show_all('True')
                song_widget.now_playing_sign.set_alignment(1, 0.6)
                song_widget.can_be_played = True
                song_widget.connect('button-release-event',
                                    self.track_selected)

    @log
    def _update_album_art(self):
        self._cache.lookup(self.album, ArtSize.medium, self._get_album_cover,
                           None)

    @log
    def _get_album_cover(self, surface, data=None):
        self.cover.set_from_surface(surface)

    @log
    def track_selected(self, widget, event):
        if not widget.can_be_played:
            return

        if not self.selectionMode and \
            (event.button == Gdk.BUTTON_SECONDARY or
                (event.button == 1 and event.state & Gdk.ModifierType.CONTROL_MASK)):
            if self.selectionModeAllowed:
                self.header_bar._select_button.set_active(True)
            else:
                return

        if self.selectionMode:
            self.model[widget._iter][6] = not self.model[widget._iter][6]
            return

        self.player.stop()
        self.player.set_playlist('Artist', self.artist,
                                 widget.model, widget._iter, 5, 6)
        self.player.set_playing(True)

    @log
    def set_selection_mode(self, selectionMode):
        if self.selectionMode == selectionMode:
            return
        self.selectionMode = selectionMode
        for songWidget in self.songs:
            songWidget.checkButton.set_visible(selectionMode)
            if not selectionMode:
                songWidget.model[songWidget._iter][6] = False

    @log
    def _check_button_toggled(self, button, songWidget):
        if songWidget.model[songWidget._iter][6] != button.get_active():
            songWidget.model[songWidget._iter][6] = button.get_active()

    @log
    def _model_row_changed(self, model, path, _iter):
        if not self.selectionMode:
            return
        if not model[_iter][5]:
            return
        songWidget = model[_iter][5].song_widget
        selected = model[_iter][6]

        if model[_iter][11] == DiscoveryStatus.FAILED:
            songWidget.now_playing_sign.set_from_icon_name(
                ERROR_ICON_NAME,
                Gtk.IconSize.SMALL_TOOLBAR)
            songWidget.now_playing_sign.show()
            songWidget.can_be_played = False

        if selected != songWidget.checkButton.get_active():
            songWidget.checkButton.set_active(selected)
