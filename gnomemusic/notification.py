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

from gi.repository import GLib, Grl, Notify

from gnomemusic.albumArtCache import AlbumArtCache

from gettext import gettext as _

IMAGE_SIZE = 125


class NotificationManager:
    def __init__(self, player):
        self._player = player

        self._notification = Notify.Notification()

        self._notification.set_category('x-gnome.music')
        self._notification.set_hint('action-icons', GLib.Variant('b', True))
        self._notification.set_hint('resident', GLib.Variant('b', True))
        self._notification.set_hint('desktop-entry', GLib.Variant('s', 'gnome-music'))

        self._isPlaying = False

        self._albumArtCache = AlbumArtCache.get_default()
        self._symbolicIcon = self._albumArtCache.make_default_icon(IMAGE_SIZE, IMAGE_SIZE)

        self._player.connect('playing-changed', self._on_playing_changed)
        self._player.connect('current-changed', self._update_track)

    def _on_playing_changed(self, player):
        # this function might be called from one of the action handlers
        # from libnotify, and we can't call _set_actions() from there
        # (we would free the closure we're currently in and corrupt
        # the stack)
        GLib.idle_add(self._update_playing)

    def _update_playing(self):
        isPlaying = self._player.playing

        if self._isPlaying != isPlaying:
            self._isPlaying = isPlaying
            self._set_actions(isPlaying)
            self._update_track(self._player)

    def _update_track(self, player):
        model = self._player.playlist
        trackIter = self._player.currentTrack

        if trackIter is None:
            self._notification.update(_("Not playing"), None, 'gnome-music')
            self._notification.set_hint('image-data', None)
            self._notification.show()
        else:
            trackField = self._player.playlistField
            item = model.get_value(trackIter, trackField)
            artist = item.get_author()
            if artist is None:
                artist = item.get_string(Grl.METADATA_KEY_ARTIST)
            album = item.get_string(Grl.METADATA_KEY_ALBUM)

            self._notification.update(item.get_title(),
                                      # TRANSLATORS: by refers to the artist, from to the album
                                      _("by %s, from %s") % ('<b>' + artist + '</b>',
                                                             '<i>' + album + '</i>'),
                                      'gnome-music')

            # Try to pass an image path instead of a serialized pixbuf if possible
            if item.get_thumbnail():
                self._notification.set_hint('image-path', GLib.Variant('s', item.get_thumbnail()))
                self._notification.set_hint('image-data', None)
                self._notification.show()
                return

            self._albumArtCache.lookup(item, IMAGE_SIZE, IMAGE_SIZE, self._album_art_loaded)

    def _album_art_loaded(self, image, path, data):
        if path:
            self._notification.set_hint('image-path', GLib.Variant('s', path))
            self._notification.set_hint('image-data', None)
        else:
            self._notification.set_hint('image-path', None)

            if not image:
                image = self._symbolicIcon

            width = image.get_width()
            height = image.get_height()
            rowStride = image.get_rowstride()
            hasAlpha = image.get_has_alpha()
            bitsPerSample = image.get_bits_per_sample()
            nChannels = image.get_n_channels()
            data = image.get_pixels()

            serialized = GLib.Variant('(iiibiiay)',
                                      [width, height, rowStride, hasAlpha,
                                       bitsPerSample, nChannels, data])
            self._notification.set_hint('image-data', serialized)

        self._notification.show()

    def _set_actions(self, playing):
        self._notification.clear_actions()

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

    def _go_previous(self, notification, action, data):
        self._player.play_previous()

    def _go_next(self, notification, action, data):
        self._player.play_next()

    def _play(self, notification, action, data):
        self._player.play()

    def _pause(self, notification, action, data):
        self._player.pause()
