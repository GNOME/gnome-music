# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
#
# Gnome Music is free software; you can Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# Gnome Music is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along
# with Gnome Music; if not, write to the Free Software Foundation,
# Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

from gnomemusic.player import PlaybackStatus, RepeatType
from gnomemusic.albumArtCache import AlbumArtCache


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
        self.player.connect('playback-status-changed', self._on_playback_status_changed)
        self.player.connect('repeat-mode-changed', self._on_repeat_mode_changed)
        self.player.connect('volume-changed', self._on_volume_changed)
        self.player.connect('prev-next-invalidated', self._on_prev_next_invalidated)
        self.player.connect('seeked', self._on_seeked)

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
            'xesam:url': media.get_url(),
            'mpris:length': dbus.Int64(media.get_duration() * 1000000),
            'xesam:trackNumber': media.get_track_number(),
            'xesam:useCount': media.get_play_count(),
            'xesam:userRating': media.get_rating(),
        }

        title = AlbumArtCache.get_media_title(media)
        if title:
            metadata['xesam:title'] = title

        album = media.get_album()
        if album:
            metadata['xesam:album'] = album

        artist = media.get_artist()
        if artist:
            metadata['xesam:artist'] = [artist]
            metadata['xesam:albumArtist'] = [artist]

        genre = media.get_genre()
        if genre:
            metadata['xesam:genre'] = [genre]

        last_played = media.get_last_played()
        if last_played:
            metadata['xesam:lastUsed'] = last_played

        thumbnail = media.get_thumbnail()
        if thumbnail:
            metadata['mpris:artUrl'] = thumbnail

        return metadata

    def _on_current_changed(self, player, data=None):
        self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'Metadata': dbus.Dictionary(self._get_metadata(),
                                                               signature='sv'),
                                   'CanPlay': True,
                                   'CanPause': True,
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
        self.player.set_playing(True)

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
