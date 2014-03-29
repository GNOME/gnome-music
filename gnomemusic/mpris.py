# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
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


import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

from gnomemusic.player import PlaybackStatus, RepeatType
from gnomemusic.albumArtCache import AlbumArtCache

from gettext import gettext as _
from gi.repository import Grl


class MediaPlayer2Service(dbus.service.Object):
    MEDIA_PLAYER2_IFACE = 'org.mpris.MediaPlayer2'
    MEDIA_PLAYER2_PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'

    def __init__(self, app):
        DBusGMainLoop(set_as_default=True)
        name = dbus.service.BusName('org.mpris.MediaPlayer2.GnomeMusic', dbus.SessionBus())
        dbus.service.Object.__init__(self, name, '/org/mpris/MediaPlayer2')
        self.app = app
        self.player = app.get_active_window().player
        self.player.connect('current-changed', self._on_current_changed)
        self.player.connect('thumbnail-updated', self._on_thumbnail_updated)
        self.player.connect('playback-status-changed', self._on_playback_status_changed)
        self.player.connect('repeat-mode-changed', self._on_repeat_mode_changed)
        self.player.connect('volume-changed', self._on_volume_changed)
        self.player.connect('prev-next-invalidated', self._on_prev_next_invalidated)
        self.player.connect('seeked', self._on_seeked)
        self.first_song_handler = 0

    def _get_playback_status(self):
        state = self.player.get_playback_status()
        if state == PlaybackStatus.PLAYING:
            return 'Playing'
        elif state == PlaybackStatus.PAUSED:
            return 'Paused'
        else:
            return 'Stopped'

    def _get_loop_status(self):
        if self.player.repeat == RepeatType.NONE:
            return 'None'
        elif self.player.repeat == RepeatType.SONG:
            return 'Track'
        else:
            return 'Playlist'

    def _get_metadata(self):
        media = self.player.get_current_media()
        if not media:
            return {}

        metadata = {
            'mpris:trackid': '/org/mpris/MediaPlayer2/Track/%s' % media.get_id(),
            'xesam:url': media.get_url()
        }

        try:
            length = dbus.Int64(media.get_duration() * 1000000)
            assert length is not None
            metadata['mpris:length'] = length
        except:
            pass

        try:
            trackNumber = media.get_track_number()
            assert trackNumber is not None
            metadata['xesam:trackNumber'] = trackNumber
        except:
            pass

        try:
            useCount = media.get_play_count()
            assert useCount is not None
            metadata['xesam:useCount'] = useCount
        except:
            pass

        try:
            userRating = media.get_rating()
            assert userRating is not None
            metadata['xesam:userRating'] = userRating
        except:
            pass

        try:
            title = AlbumArtCache.get_media_title(media)
            assert title is not None
            metadata['xesam:title'] = title
        except:
            pass

        try:
            album = media.get_album()
            assert album is not None
        except:
            try:
                album = media.get_string(Grl.METADATA_KEY_ALBUM)
                assert album is not None
            except:
                album = _("Unknown Album")
        finally:
            metadata['xesam:album'] = album

        try:
            artist = media.get_artist()
            assert artist is not None
        except:
            try:
                artist = media.get_string(Grl.METADATA_KEY_ARTIST)
                assert artist is not None
            except:
                try:
                    artist = media.get_author()
                    assert artist is not None
                except (AssertionError, ValueError):
                    artist = _("Unknown Artist")
        finally:
            metadata['xesam:artist'] = [artist]
            metadata['xesam:albumArtist'] = [artist]

        try:
            genre = media.get_genre()
            assert genre is not None
            metadata['xesam:genre'] = genre
        except:
            pass

        try:
            lastUsed = media.get_last_played()
            assert genre is not None
            metadata['xesam:lastUsed'] = lastUsed
        except:
            pass

        try:
            artUrl = media.get_thumbnail()
            assert genre is not None
            metadata['mpris:artUrl'] = artUrl
        except:
            pass

        return metadata

    def _on_current_changed(self, player, data=None):
        if self.player.repeat == RepeatType.SONG:
            self.Seeked(0)

        self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'Metadata': dbus.Dictionary(self._get_metadata(),
                                                               signature='sv'),
                                   'CanPlay': True,
                                   'CanPause': True,
                               },
                               [])

    def _on_thumbnail_updated(self, player, path, data=None):
        self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'Metadata': dbus.Dictionary(self._get_metadata(),
                                                               signature='sv'),
                               },
                               [])

    def _on_playback_status_changed(self, data=None):
        self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'PlaybackStatus': self._get_playback_status(),
                               },
                               [])

    def _on_repeat_mode_changed(self, player, data=None):
        self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'LoopStatus': self._get_loop_status(),
                                   'Shuffle': self.player.repeat == RepeatType.SHUFFLE,
                               },
                               [])

    def _on_volume_changed(self, player, data=None):
        self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'Volume': dbus.Double(self.player.get_volume()),
                               },
                               [])

    def _on_prev_next_invalidated(self, player, data=None):
        self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'CanGoNext': self.player.has_next(),
                                   'CanGoPrevious': self.player.has_previous(),
                               },
                               [])

    def _play_first_song(self, model, path, iter_, data=None):
        if self.first_song_handler:
            model.disconnect(self.first_song_handler)
            self.first_song_handler = 0
        self.player.set_playlist('Songs', None, model, iter_, 5)
        self.player.set_playing(True)

    def _on_seeked(self, player, position, data=None):
        self.Seeked(position)

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_IFACE)
    def Raise(self):
        self.app.do_activate()

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_IFACE)
    def Quit(self):
        self.app.quit()

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE)
    def Next(self):
        self.player.play_next()

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE)
    def Previous(self):
        self.player.play_previous()

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE)
    def Pause(self):
        self.player.set_playing(False)

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE)
    def PlayPause(self):
        self.player.play_pause()

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE)
    def Stop(self):
        self.player.Stop()

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE)
    def Play(self):
        if self.player.playlist is not None:
            self.player.set_playing(True)
        elif self.first_song_handler == 0:
            window = self.app.get_active_window()
            window._stack.set_visible_child(window.views[2])
            model = window.views[2].filter
            if model.iter_n_children(None):
                _iter = model.get_iter_first()
                self._play_first_song(model, model.get_path(_iter), _iter)
            else:
                self.first_song_handler = model.connect('row-inserted', self._play_first_song)

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE,
                         in_signature='x')
    def Seek(self, offset):
        self.player.set_position(offset, True, True)

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE,
                         in_signature='ox')
    def SetPosition(self, track_id, position):
        if track_id != self._get_metadata().get('mpris:trackid'):
            return
        self.player.set_position(position)

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE,
                         in_signature='s')
    def OpenUri(self, uri):
        pass

    @dbus.service.signal(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE,
                         signature='x')
    def Seeked(self, position):
        pass

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ss', out_signature='v')
    def Get(self, interface_name, property_name):
        return self.GetAll(interface_name)[property_name]

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        if interface_name == self.MEDIA_PLAYER2_IFACE:
            return {
                'CanQuit': True,
                'CanRaise': True,
                'HasTrackList': False,
                'Identity': 'Music',
                'DesktopEntry': 'gnome-music',
                'SupportedUriSchemes': [
                    'file'
                ],
                'SupportedMimeTypes': [
                    'application/ogg',
                    'audio/x-vorbis+ogg',
                    'audio/x-flac',
                    'audio/mpeg'
                ],
            }
        elif interface_name == self.MEDIA_PLAYER2_PLAYER_IFACE:
            return {
                'PlaybackStatus': self._get_playback_status(),
                'LoopStatus': self._get_loop_status(),
                'Rate': dbus.Double(1.0),
                'Shuffle': self.player.repeat == RepeatType.SHUFFLE,
                'Metadata': dbus.Dictionary(self._get_metadata(), signature='sv'),
                'Volume': dbus.Double(self.player.get_volume()),
                'Position': dbus.Int64(self.player.get_position()),
                'MinimumRate': dbus.Double(1.0),
                'MaximumRate': dbus.Double(1.0),
                'CanGoNext': self.player.has_next(),
                'CanGoPrevious': self.player.has_previous(),
                'CanPlay': self.player.currentTrack is not None,
                'CanPause': self.player.currentTrack is not None,
                'CanSeek': True,
                'CanControl': True,
            }
        else:
            raise dbus.exceptions.DBusException(
                'org.mpris.MediaPlayer2.GnomeMusic',
                'This object does not implement the %s interface'
                % interface_name)

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ssv')
    def Set(self, interface_name, property_name, new_value):
        if interface_name == self.MEDIA_PLAYER2_IFACE:
            pass
        elif interface_name == self.MEDIA_PLAYER2_PLAYER_IFACE:
            if property_name == 'Rate':
                pass
            elif property_name == 'Volume':
                self.player.set_volume(new_value)
            elif property_name == 'LoopStatus':
                if new_value == 'None':
                    self.player.set_repeat_mode(RepeatType.NONE)
                elif new_value == 'Track':
                    self.player.set_repeat_mode(RepeatType.SONG)
                elif new_value == 'Playlist':
                    self.player.set_repeat_mode(RepeatType.ALL)
            elif property_name == 'Shuffle':
                if (new_value and self.player.get_repeat_mode() != RepeatType.SHUFFLE):
                    self.set_repeat_mode(RepeatType.SHUFFLE)
                elif new_value and self.player.get_repeat_mode() == RepeatType.SHUFFLE:
                    self.set_repeat_mode(RepeatType.NONE)
        else:
            raise dbus.exceptions.DBusException(
                'org.mpris.MediaPlayer2.GnomeMusic',
                'This object does not implement the %s interface'
                % interface_name)

    @dbus.service.signal(dbus_interface=dbus.PROPERTIES_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        pass
