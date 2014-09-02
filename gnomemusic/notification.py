# Copyright (c) 2013 Giovanni Campagna <scampa.giovanni@gmail.com>
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

from gi.repository import GLib, Grl, Gtk, Notify

from gnomemusic.albumArtCache import AlbumArtCache

from gettext import gettext as _

from gnomemusic import log
import logging
logger = logging.getLogger(__name__)

IMAGE_SIZE = 125


class NotificationManager:
    @log
    def __init__(self, player):
        self._player = player

        self._notification = Notify.Notification()

        self._notification.set_category('x-gnome.music')
        self._notification.set_hint('action-icons', GLib.Variant('b', True))
        self._notification.set_hint('resident', GLib.Variant('b', True))
        self._notification.set_hint('desktop-entry', GLib.Variant('s', 'gnome-music'))

        self._isPlaying = False

        self._albumArtCache = AlbumArtCache.get_default()
        self._symbolicIcon = self._albumArtCache.get_default_icon(IMAGE_SIZE, IMAGE_SIZE)

        rowStride = self._symbolicIcon.get_rowstride()
        hasAlpha = self._symbolicIcon.get_has_alpha()
        bitsPerSample = self._symbolicIcon.get_bits_per_sample()
        nChannels = self._symbolicIcon.get_n_channels()
        data = self._symbolicIcon.get_pixels()

        self._symbolicIconSerialized = GLib.Variant('(iiibiiay)',
                                                    (IMAGE_SIZE, IMAGE_SIZE, rowStride, hasAlpha,
                                                     bitsPerSample, nChannels, data))

        self._player.connect('playing-changed', self._on_playing_changed)
        self._player.connect('current-changed', self._update_track)
        self._player.connect('thumbnail-updated', self._on_thumbnail_updated)

    @log
    def _on_playing_changed(self, player):
        # this function might be called from one of the action handlers
        # from libnotify, and we can't call _set_actions() from there
        # (we would free the closure we're currently in and corrupt
        # the stack)
        GLib.idle_add(self._update_playing)

    @log
    def _update_playing(self):
        isPlaying = self._player.playing

        if self._isPlaying != isPlaying:
            self._isPlaying = isPlaying
            self._set_actions(isPlaying)
            self._update_track(self._player)

    @log
    def _update_track(self, player):
        if not self._player.currentTrack:
            self._notification.update(_("Not playing"), None, 'gnome-music')
            self._notification.set_hint('image-data', None)
            self._notification.show()
        else:
            item = self._player.get_current_media()
            if not item:
                return
            artist = item.get_string(Grl.METADATA_KEY_ARTIST)\
                or item.get_author()\
                or _("Unknown Artist")
            album = item.get_string(Grl.METADATA_KEY_ALBUM)\
                or _("Unknown Album")

            self._notification.update(AlbumArtCache.get_media_title(item),
                                      # TRANSLATORS: by refers to the artist, from to the album
                                      _("by %s, from %s") % ('<b>' + artist + '</b>',
                                                             '<i>' + album + '</i>'),
                                      'gnome-music')

            self._notification.show()

    @log
    def _on_thumbnail_updated(self, player, path, data=None):
        if path:
            self._notification.set_hint('image-path', GLib.Variant('s', path))
            self._notification.set_hint('image-data', None)
        else:
            self._notification.set_hint('image-path', None)
            self._notification.set_hint('image-data', self._symbolicIconSerialized)
        self._notification.show()

    @log
    def _set_actions(self, playing):
        self._notification.clear_actions()

        if (Notify.VERSION_MINOR > 7) or (Notify.VERSION_MINOR == 7 and Notify.VERSION_MICRO > 5):
            self._notification.add_action('media-skip-backward', _("Previous"),
                                          self._go_previous, None)
            if playing:
                self._notification.add_action('media-playback-pause', _("Pause"),
                                              self._pause, None)
            else:
                self._notification.add_action('media-playback-start', _("Play"),
                                              self._play, None)
            self._notification.add_action('media-skip-forward', _("Next"),
                                          self._go_next, None)

    @log
    def _go_previous(self, notification, action, data):
        self._player.play_previous()

    @log
    def _go_next(self, notification, action, data):
        self._player.play_next()

    @log
    def _play(self, notification, action, data):
        self._player.play()

    @log
    def _pause(self, notification, action, data):
        self._player.pause()
