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
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists

from gettext import gettext as _
from gi.repository import GLib
from gi.repository import Grl
from gnomemusic import log
import logging
logger = logging.getLogger(__name__)


class MediaPlayer2Service(dbus.service.Object):
    MEDIA_PLAYER2_IFACE = 'org.mpris.MediaPlayer2'
    MEDIA_PLAYER2_PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'
    MEDIA_PLAYER2_TRACKLIST_IFACE = 'org.mpris.MediaPlayer2.TrackList'
    MEDIA_PLAYER2_PLAYLISTS_IFACE = 'org.mpris.MediaPlayer2.Playlists'

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
        self.player.connect('playlist-changed', self._on_playlist_changed)
        playlists = Playlists.get_default()
        playlists.connect('playlist-created', self._on_playlists_count_changed)
        playlists.connect('playlist-deleted', self._on_playlists_count_changed)
        grilo.connect('ready', self._on_grilo_ready)
        self.playlists = []
        self.playlist = None
        self.playlist_insert_handler = 0
        self.playlist_delete_handler = 0
        self.first_song_handler = 0

    @log
    def _get_playback_status(self):
        state = self.player.get_playback_status()
        if state == PlaybackStatus.PLAYING:
            return 'Playing'
        elif state == PlaybackStatus.PAUSED:
            return 'Paused'
        else:
            return 'Stopped'

    @log
    def _get_loop_status(self):
        if self.player.repeat == RepeatType.NONE:
            return 'None'
        elif self.player.repeat == RepeatType.SONG:
            return 'Track'
        else:
            return 'Playlist'

    @log
    def _get_metadata(self, media=None):
        if not media:
            media = self.player.get_current_media()
        if not media:
            return {}

        metadata = {
            'mpris:trackid': self._get_media_id(media),
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
            assert lastUsed is not None
            metadata['xesam:lastUsed'] = lastUsed
        except:
            pass

        try:
            artUrl = media.get_thumbnail()
            assert artUrl is not None
            metadata['mpris:artUrl'] = artUrl
        except:
            pass

        return metadata

    @log
    def _get_media_id(self, media):
        return '/org/mpris/MediaPlayer2/TrackList/%s' % \
            (media.get_id() if media else 'NoTrack')

    @log
    def _get_media_from_id(self, track_id):
        for track in self.player.playlist:
            media = track[self.player.playlistField]
            if track_id == self._get_media_id(media):
                return media
        return None

    @log
    def _get_track_list(self):
        if self.player.playlist:
            return [self._get_media_id(track[self.player.playlistField])
                    for track in self.player.playlist]
        else:
            return []

    @log
    def _get_playlist_path(self, playlist):
        return '/org/mpris/MediaPlayer2/Playlist/%s' % \
            (playlist.get_id() if playlist else 'Invalid')

    @log
    def _get_playlist_from_path(self, playlist_path):
        for playlist in self.playlists:
            if playlist_path == self._get_playlist_path(playlist):
                return playlist
        return None

    @log
    def _get_playlist_from_id(self, playlist_id):
        for playlist in self.playlists:
            if playlist_id == playlist.get_id():
                return playlist
        return None

    @log
    def _get_playlists(self, callback):
        playlists = []

        def populate_callback(source, param, item, remaining=0, data=None):
            if item:
                playlists.append(item)
            else:
                callback(playlists)

        if grilo.tracker:
            GLib.idle_add(grilo.populate_playlists, 0, populate_callback)
        else:
            callback(playlists)

    @log
    def _get_active_playlist(self):
        playlist = self._get_playlist_from_id(self.player.playlistId) \
            if self.player.playlistType == 'Playlist' else None
        playlistName = AlbumArtCache.get_media_title(playlist) \
            if playlist else ''
        return (playlist is not None,
                (self._get_playlist_path(playlist), playlistName, ''))

    @log
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

    @log
    def _on_thumbnail_updated(self, player, path, data=None):
        self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'Metadata': dbus.Dictionary(self._get_metadata(),
                                                               signature='sv'),
                               },
                               [])

    @log
    def _on_playback_status_changed(self, data=None):
        self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'PlaybackStatus': self._get_playback_status(),
                               },
                               [])

    @log
    def _on_repeat_mode_changed(self, player, data=None):
        self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'LoopStatus': self._get_loop_status(),
                                   'Shuffle': self.player.repeat == RepeatType.SHUFFLE,
                               },
                               [])

    @log
    def _on_volume_changed(self, player, data=None):
        self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'Volume': dbus.Double(self.player.get_volume()),
                               },
                               [])

    @log
    def _on_prev_next_invalidated(self, player, data=None):
        self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'CanGoNext': self.player.has_next(),
                                   'CanGoPrevious': self.player.has_previous(),
                               },
                               [])

    @log
    def _play_first_song(self, model, path, iter_, data=None):
        if self.first_song_handler:
            model.disconnect(self.first_song_handler)
            self.first_song_handler = 0
        self.player.set_playlist('Songs', None, model, iter_, 5)
        self.player.set_playing(True)

    @log
    def _on_seeked(self, player, position, data=None):
        self.Seeked(position)

    @log
    def _on_playlist_changed(self, player, data=None):
        if self.playlist:
            if self.playlist_insert_handler:
                self.playlist.disconnect(self.playlist_insert_handler)
            if self.playlist_delete_handler:
                self.playlist.disconnect(self.playlist_delete_handler)

        self.playlist = self.player.playlist
        self._on_playlist_modified()

        self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYLISTS_IFACE,
                               {
                                   'ActivePlaylist': self._get_active_playlist(),
                               },
                               [])

        self.playlist_insert_handler = \
            self.playlist.connect('row-inserted', self._on_playlist_modified)
        self.playlist_delete_handler = \
            self.playlist.connect('row-deleted', self._on_playlist_modified)

    @log
    def _on_playlist_modified(self, path=None, _iter=None, data=None):
        path = self.player.currentTrack.get_path()
        currentTrack = self.player.playlist[path][self.player.playlistField]
        track_list = self._get_track_list()
        self.TrackListReplaced(track_list, self._get_media_id(currentTrack))
        self.PropertiesChanged(self.MEDIA_PLAYER2_TRACKLIST_IFACE,
                               {
                                   'Tracks': track_list,
                               },
                               [])

    @log
    def _reload_playlists(self):
        def get_playlists_callback(playlists):
            self.playlists = playlists
            self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYLISTS_IFACE,
                                   {
                                       'PlaylistCount': len(playlists),
                                   },
                                   [])

        self._get_playlists(get_playlists_callback)

    @log
    def _on_playlists_count_changed(self, playlists, item):
        self._reload_playlists()

    @log
    def _on_grilo_ready(self, grilo):
        self._reload_playlists()

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
            model = window.views[2]._model
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

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_TRACKLIST_IFACE,
                         in_signature='ao', out_signature='aa{sv}')
    def GetTracksMetadata(self, track_ids):
        metadata = []
        for track_id in track_ids:
            metadata.append(self._get_metadata(self._get_media_from_id(track_id)))
        return metadata

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_TRACKLIST_IFACE,
                         in_signature='sob')
    def AddTrack(self, uri, after_track, set_as_current):
        pass

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_TRACKLIST_IFACE,
                         in_signature='o')
    def RemoveTrack(self, track_id):
        pass

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_TRACKLIST_IFACE,
                         in_signature='o')
    def GoTo(self, track_id):
        for track in self.player.playlist:
            media = track[self.player.playlistField]
            if track_id == self._get_media_id(media):
                self.player.set_playlist(self.player.playlistType,
                                         self.player.playlistId,
                                         self.player.playlist,
                                         track.iter,
                                         self.player.playlistField)
                self.player.play()
                return

    @dbus.service.signal(dbus_interface=MEDIA_PLAYER2_TRACKLIST_IFACE,
                         signature='aoo')
    def TrackListReplaced(self, tracks, current_track):
        pass

    @dbus.service.signal(dbus_interface=MEDIA_PLAYER2_TRACKLIST_IFACE,
                         signature='a{sv}o')
    def TrackAdded(self, metadata, after_track):
        pass

    @dbus.service.signal(dbus_interface=MEDIA_PLAYER2_TRACKLIST_IFACE,
                         signature='o')
    def TrackRemoved(self, track_id):
        pass

    @dbus.service.signal(dbus_interface=MEDIA_PLAYER2_TRACKLIST_IFACE,
                         signature='oa{sv}')
    def TrackMetadataChanged(self, track_id, metadata):
        pass

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYLISTS_IFACE,
                         in_signature='o')
    def ActivatePlaylist(self, playlist_path):
        playlist_id = self._get_playlist_from_path(playlist_path).get_id()
        self.app._window.views[3].activate_playlist(playlist_id)

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYLISTS_IFACE,
                         in_signature='uusb', out_signature='a(oss)')
    def GetPlaylists(self, index, max_count, order, reverse):
        if order != 'Alphabetical':
            return []
        playlists = [(self._get_playlist_path(playlist),
                      AlbumArtCache.get_media_title(playlist) or '', '')
                     for playlist in self.playlists]
        return playlists[index:index + max_count] if not reverse \
            else playlists[index + max_count - 1:index - 1 if index - 1 >= 0 else None:-1]

    @dbus.service.signal(dbus_interface=MEDIA_PLAYER2_PLAYLISTS_IFACE,
                         signature='(oss)')
    def PlaylistChanged(self, playlist):
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
                'Fullscreen': False,
                'CanSetFullscreen': False,
                'CanRaise': True,
                'HasTrackList': True,
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
        elif interface_name == self.MEDIA_PLAYER2_TRACKLIST_IFACE:
            return {
                'Tracks': self._get_track_list(),
                'CanEditTracks': False,
            }
        elif interface_name == self.MEDIA_PLAYER2_PLAYLISTS_IFACE:
            return {
                'PlaylistCount': len(self.playlists),
                'Orderings': ['Alphabetical'],
                'ActivePlaylist': self._get_active_playlist(),
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
            if property_name == 'Fullscreen':
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
