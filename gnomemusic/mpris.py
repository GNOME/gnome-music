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

import codecs

from gnomemusic.gstplayer import Playback
from gnomemusic.player import RepeatType
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists
from gnomemusic.utils import View
import gnomemusic.utils as utils

from gi.repository import GLib
from gi.repository import Gio
from gnomemusic import log
import logging
logger = logging.getLogger(__name__)


class Server:
    def __init__(self, con, path):
        method_outargs = {}
        method_inargs = {}
        for interface in Gio.DBusNodeInfo.new_for_xml(self.__doc__).interfaces:

            for method in interface.methods:
                method_outargs[method.name] = '(' + ''.join([arg.signature for arg in method.out_args]) + ')'
                method_inargs[method.name] = tuple(arg.signature for arg in method.in_args)

            con.register_object(object_path=path,
                                interface_info=interface,
                                method_call_closure=self.on_method_call)

        self.method_inargs = method_inargs
        self.method_outargs = method_outargs

    def on_method_call(self,
                       connection,
                       sender,
                       object_path,
                       interface_name,
                       method_name,
                       parameters,
                       invocation):

        args = list(parameters.unpack())
        for i, sig in enumerate(self.method_inargs[method_name]):
            if sig is 'h':
                msg = invocation.get_message()
                fd_list = msg.get_unix_fd_list()
                args[i] = fd_list.get(args[i])

        result = getattr(self, method_name)(*args)

        # out_args is atleast (signature1). We therefore always wrap the result
        # as a tuple. Refer to https://bugzilla.gnome.org/show_bug.cgi?id=765603
        result = (result,)

        out_args = self.method_outargs[method_name]
        if out_args != '()':
            variant = GLib.Variant(out_args, result)
            invocation.return_value(variant)
        else:
            invocation.return_value(None)


class MediaPlayer2Service(Server):
    '''
    <!DOCTYPE node PUBLIC '-//freedesktop//DTD D-BUS Object Introspection 1.0//EN'
    'http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd'>
    <node>
        <interface name='org.freedesktop.DBus.Introspectable'>
            <method name='Introspect'>
                <arg name='data' direction='out' type='s'/>
            </method>
        </interface>
        <interface name='org.freedesktop.DBus.Properties'>
            <method name='Get'>
                <arg name='interface' direction='in' type='s'/>
                <arg name='property' direction='in' type='s'/>
                <arg name='value' direction='out' type='v'/>
            </method>
            <method name="Set">
                <arg name="interface_name" direction="in" type="s"/>
                <arg name="property_name" direction="in" type="s"/>
                <arg name="value" direction="in" type="v"/>
            </method>
            <method name='GetAll'>
                <arg name='interface' direction='in' type='s'/>
                <arg name='properties' direction='out' type='a{sv}'/>
            </method>
        </interface>
        <interface name='org.mpris.MediaPlayer2'>
            <method name='Raise'>
            </method>
            <method name='Quit'>
            </method>
            <property name='CanQuit' type='b' access='read' />
            <property name='Fullscreen' type='b' access='readwrite' />
            <property name='CanRaise' type='b' access='read' />
            <property name='HasTrackList' type='b' access='read'/>
            <property name='Identity' type='s' access='read'/>
            <property name='DesktopEntry' type='s' access='read'/>
            <property name='SupportedUriSchemes' type='as' access='read'/>
            <property name='SupportedMimeTypes' type='as' access='read'/>
        </interface>
        <interface name='org.mpris.MediaPlayer2.Player'>
            <method name='Next'/>
            <method name='Previous'/>
            <method name='Pause'/>
            <method name='PlayPause'/>
            <method name='Stop'/>
            <method name='Play'/>
            <method name='Seek'>
                <arg direction='in' name='Offset' type='x'/>
            </method>
            <method name='SetPosition'>
                <arg direction='in' name='TrackId' type='o'/>
                <arg direction='in' name='Position' type='x'/>
            </method>
            <method name='OpenUri'>
                <arg direction='in' name='Uri' type='s'/>
            </method>
            <signal name='Seeked'>
                <arg name='Position' type='x'/>
            </signal>
            <property name='PlaybackStatus' type='s' access='read'/>
            <property name='LoopStatus' type='s' access='readwrite'/>
            <property name='Rate' type='d' access='readwrite'/>
            <property name='Shuffle' type='b' access='readwrite'/>
            <property name='Metadata' type='a{sv}' access='read'>
            </property>
            <property name='Volume' type='d' access='readwrite'/>
            <property name='Position' type='x' access='read'/>
            <property name='MinimumRate' type='d' access='read'/>
            <property name='MaximumRate' type='d' access='read'/>
            <property name='CanGoNext' type='b' access='read'/>
            <property name='CanGoPrevious' type='b' access='read'/>
            <property name='CanPlay' type='b' access='read'/>
            <property name='CanPause' type='b' access='read'/>
            <property name='CanSeek' type='b' access='read'/>
            <property name='CanControl' type='b' access='read'/>
        </interface>
        <interface name='org.mpris.MediaPlayer2.TrackList'>
            <method name='GetTracksMetadata'>
                <arg direction='in' name='TrackIds' type='ao'/>
                <arg direction='out' name='Metadata' type='aa{sv}'>
                </arg>
            </method>
            <method name='AddTrack'>
                <arg direction='in' name='Uri' type='s'/>
                <arg direction='in' name='AfterTrack' type='o'/>
                <arg direction='in' name='SetAsCurrent' type='b'/>
            </method>
            <method name='RemoveTrack'>
                <arg direction='in' name='TrackId' type='o'/>
            </method>
            <method name='GoTo'>
                <arg direction='in' name='TrackId' type='o'/>
            </method>
            <signal name='TrackListReplaced'>
                <arg name='Tracks' type='ao'/>
                <arg name='CurrentTrack' type='o'/>
            </signal>
            <signal name='TrackAdded'>
                <arg name='Metadata' type='a{sv}'>
                </arg>
                <arg name='AfterTrack' type='o'/>
            </signal>
            <signal name='TrackRemoved'>
                <arg name='TrackId' type='o'/>
            </signal>
            <signal name='TrackMetadataChanged'>
                <arg name='TrackId' type='o'/>
                <arg name='Metadata' type='a{sv}'>
                </arg>
            </signal>
            <property name='Tracks' type='ao' access='read'/>
            <property name='CanEditTracks' type='b' access='read'/>
        </interface>
    </node>
    '''

    MEDIA_PLAYER2_IFACE = 'org.mpris.MediaPlayer2'
    MEDIA_PLAYER2_PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'
    MEDIA_PLAYER2_TRACKLIST_IFACE = 'org.mpris.MediaPlayer2.TrackList'
    MEDIA_PLAYER2_PLAYLISTS_IFACE = 'org.mpris.MediaPlayer2.Playlists'

    def __repr__(self):
        return '<MediaPlayer2Service>'

    def __init__(self, app):
        self.con = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        Gio.bus_own_name_on_connection(self.con,
                                       'org.mpris.MediaPlayer2.GnomeMusic',
                                       Gio.BusNameOwnerFlags.NONE,
                                       None,
                                       None)
        super().__init__(self.con, '/org/mpris/MediaPlayer2')

        self.app = app
        self.player = app.get_active_window().player
        self.player.connect(
            'current-song-changed', self._on_current_song_changed)
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
        if state == Playback.PLAYING:
            return 'Playing'
        elif state == Playback.PAUSED:
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
            'mpris:trackid': GLib.Variant('o', self._get_media_id(media)),
            'xesam:url': GLib.Variant('s', media.get_url())
        }

        try:
            length = media.get_duration() * 1000000
            assert length is not None
            metadata['mpris:length'] = GLib.Variant('x', length)
        except:
            pass

        try:
            trackNumber = media.get_track_number()
            assert trackNumber is not None
            metadata['xesam:trackNumber'] = GLib.Variant('i', trackNumber)
        except:
            pass

        try:
            useCount = media.get_play_count()
            assert useCount is not None
            metadata['xesam:useCount'] = GLib.Variant('i', useCount)
        except:
            pass

        try:
            userRating = media.get_rating()
            assert userRating is not None
            metadata['xesam:userRating'] = GLib.Variant('d', userRating)
        except:
            pass

        try:
            title = utils.get_media_title(media)
            assert title is not None
            metadata['xesam:title'] = GLib.Variant('s', title)
        except:
            pass


        album = utils.get_album_title(media)
        metadata['xesam:album'] = GLib.Variant('s', album)

        artist = utils.get_artist_name(media)
        metadata['xesam:artist'] = GLib.Variant('as', [artist])
        metadata['xesam:albumArtist'] = GLib.Variant('as', [artist])

        try:
            genre = media.get_genre()
            assert genre is not None
            metadata['xesam:genre'] = GLib.Variant('as', genre)
        except:
            pass

        try:
            lastUsed = media.get_last_played()
            assert lastUsed is not None
            metadata['xesam:lastUsed'] = GLib.Variant('s', lastUsed)
        except:
            pass

        try:
            artUrl = media.get_thumbnail()
            assert artUrl is not None
            metadata['mpris:artUrl'] = GLib.Variant('s', artUrl)
        except:
            pass

        return metadata

    @log
    def _get_media_id(self, media):
        if media:
            trackid = "/org/gnome/GnomeMusic/Tracklist/{}".format(
                codecs.encode(
                    bytes(media.get_id(), 'ascii'), 'hex').decode('ascii'))
        else:
            trackid = "/org/mpris/MediaPlayer2/TrackList/NoTrack"

        return trackid

    @log
    def _get_media_from_id(self, track_id):
        for track in self.player.playlist:
            media = track[self.player.Field.SONG]
            if track_id == self._get_media_id(media):
                return media
        return None

    @log
    def _get_track_list(self):
        if self.player.playlist:
            return [self._get_media_id(track[self.player.Field.SONG])
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

        grilo.populate_playlists(0, populate_callback)

    @log
    def _get_active_playlist(self):
        playlist = self._get_playlist_from_id(self.player.playlist_id) \
            if self.player.playlist_type == 'Playlist' else None
        playlistName = utils.get_media_title(playlist) \
            if playlist else ''
        return (playlist is not None,
                (self._get_playlist_path(playlist), playlistName, ''))

    @log
    def _on_current_song_changed(self, player, current_iter, data=None):
        if self.player.repeat == RepeatType.SONG:
            self.Seeked(0)

        self.PropertiesChanged(MediaPlayer2Service.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'Metadata': GLib.Variant('a{sv}', self._get_metadata()),
                                   'CanPlay': GLib.Variant('b', True),
                                   'CanPause': GLib.Variant('b', True),
                               },
                               [])

    @log
    def _on_thumbnail_updated(self, player, data=None):
        self.PropertiesChanged(MediaPlayer2Service.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'Metadata': GLib.Variant('a{sv}', self._get_metadata()),
                               },
                               [])

    @log
    def _on_playback_status_changed(self, data=None):
        self.PropertiesChanged(MediaPlayer2Service.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'PlaybackStatus': GLib.Variant('s', self._get_playback_status()),
                               },
                               [])

    @log
    def _on_repeat_mode_changed(self, player, data=None):
        self.PropertiesChanged(MediaPlayer2Service.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'LoopStatus': GLib.Variant('s', self._get_loop_status()),
                                   'Shuffle': GLib.Variant('b', self.player.repeat == RepeatType.SHUFFLE),
                               },
                               [])

    @log
    def _on_volume_changed(self, player, data=None):
        self.PropertiesChanged(MediaPlayer2Service.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'Volume': GLib.Variant('d', self.player.get_volume()),
                               },
                               [])

    @log
    def _on_prev_next_invalidated(self, player, data=None):
        self.PropertiesChanged(MediaPlayer2Service.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'CanGoNext': GLib.Variant('b', self.player.has_next()),
                                   'CanGoPrevious': GLib.Variant('b', self.player.has_previous()),
                               },
                               [])

    @log
    def _play_first_song(self, model, path, iter_, data=None):
        if self.first_song_handler:
            model.disconnect(self.first_song_handler)
            self.first_song_handler = 0
        self.player.set_playlist('Songs', None, model, iter_)
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

        self.PropertiesChanged(MediaPlayer2Service.MEDIA_PLAYER2_PLAYLISTS_IFACE,
                               {
                                'ActivePlaylist': GLib.Variant('(b(oss))', self._get_active_playlist()),
                               },
                               [])

        self.playlist_insert_handler = \
            self.playlist.connect('row-inserted', self._on_playlist_modified)
        self.playlist_delete_handler = \
            self.playlist.connect('row-deleted', self._on_playlist_modified)

    @log
    def _on_playlist_modified(self, path=None, _iter=None, data=None):
        if self.player.current_track and self.player.current_track.valid():
            path = self.player.current_track.get_path()
            current_track = self.player.playlist[path][self.player.Field.SONG]
            track_list = self._get_track_list()
            self.TrackListReplaced(track_list, self._get_media_id(current_track))
            self.PropertiesChanged(MediaPlayer2Service.MEDIA_PLAYER2_TRACKLIST_IFACE,
                                   {
                                       'Tracks': GLib.Variant('ao', track_list),
                                   },
                                   [])

    @log
    def _reload_playlists(self):
        def get_playlists_callback(playlists):
            self.playlists = playlists
            self.PropertiesChanged(MediaPlayer2Service.MEDIA_PLAYER2_PLAYLISTS_IFACE,
                                   {
                                       'PlaylistCount': GLib.Variant('u', len(playlists)),
                                   },
                                   [])

        self._get_playlists(get_playlists_callback)

    @log
    def _on_playlists_count_changed(self, playlists, item):
        self._reload_playlists()

    @log
    def _on_grilo_ready(self, grilo):
        self._reload_playlists()

    def Raise(self):
        self.app.do_activate()

    def Quit(self):
        self.app.quit()

    def Next(self):
        self.player.play_next()

    def Previous(self):
        self.player.play_previous()

    def Pause(self):
        self.player.set_playing(False)

    def PlayPause(self):
        self.player.play_pause()

    def Stop(self):
        self.player.stop()

    def Play(self):
        if self.player.playlist is not None:
            self.player.set_playing(True)
        elif self.first_song_handler == 0:
            window = self.app.get_active_window()
            window._stack.set_visible_child(window.views[View.SONG])
            model = window.views[View.SONG].model
            if model.iter_n_children(None):
                _iter = model.get_iter_first()
                self._play_first_song(model, model.get_path(_iter), _iter)
            else:
                self.first_song_handler = model.connect('row-inserted', self._play_first_song)

    def Seek(self, offset):
        self.player.set_position(offset, True, True)

    def SetPosition(self, track_id, position):
        if track_id != self._get_metadata().get('mpris:trackid').get_string():
            return
        self.player.set_position(position)

    def OpenUri(self, uri):
        pass

    def Seeked(self, position):
        self.con.emit_signal(None,
                             '/org/mpris/MediaPlayer2',
                             MediaPlayer2Service.MEDIA_PLAYER2_PLAYER_IFACE,
                             'Seeked',
                             GLib.Variant.new_tuple(GLib.Variant('x', position)))

    def GetTracksMetadata(self, track_ids):
        metadata = []
        for track_id in track_ids:
            metadata.append(self._get_metadata(self._get_media_from_id(track_id)))
        return metadata

    def AddTrack(self, uri, after_track, set_as_current):
        pass

    def RemoveTrack(self, track_id):
        pass

    def GoTo(self, track_id):
        for track in self.player.playlist:
            media = track[self.player.Field.SONG]
            if track_id == self._get_media_id(media):
                self.player.set_playlist(
                    self.player.playlist_type, self.player.playlist_id,
                    self.player.playlist, track.iter)
                self.player.play()
                return

    def TrackListReplaced(self, tracks, current_track):
        self.con.emit_signal(None,
                             '/org/mpris/MediaPlayer2',
                             MediaPlayer2Service.MEDIA_PLAYER2_TRACKLIST_IFACE,
                             'TrackListReplaced',
                             GLib.Variant.new_tuple(GLib.Variant('ao', tracks),
                                                    GLib.Variant('o', current_track)))

    def TrackAdded(self, metadata, after_track):
        self.con.emit_signal(None,
                             '/org/mpris/MediaPlayer2',
                             MediaPlayer2Service.MEDIA_PLAYER2_TRACKLIST_IFACE,
                             'TrackAdded',
                             GLib.Variant.new_tuple(GLib.Variant('a{sv}', metadata),
                                                    GLib.Variant('o', after_track)))

    def TrackRemoved(self, track_id):
        self.con.emit_signal(None,
                             '/org/mpris/MediaPlayer2',
                             MediaPlayer2Service.MEDIA_PLAYER2_TRACKLIST_IFACE,
                             'TrackRemoved',
                             GLib.Variant.new_tuple(GLib.Variant('o', track_id)))

    def TrackMetadataChanged(self, track_id, metadata):
        self.con.emit_signal(None,
                             '/org/mpris/MediaPlayer2',
                             MediaPlayer2Service.MEDIA_PLAYER2_TRACKLIST_IFACE,
                             'TrackMetadataChanged',
                             GLib.Variant.new_tuple(GLib.Variant('o', track_id),
                                                    GLib.Variant('a{sv}', metadata)))

    def ActivatePlaylist(self, playlist_path):
        playlist_id = self._get_playlist_from_path(playlist_path).get_id()
        self.app._window.views[View.PLAYLIST].activate_playlist(playlist_id)

    def GetPlaylists(self, index, max_count, order, reverse):
        if order != 'Alphabetical':
            return []
        playlists = [(self._get_playlist_path(playlist),
                      utils.get_media_title(playlist) or '', '')
                     for playlist in self.playlists]
        return playlists[index:index + max_count] if not reverse \
            else playlists[index + max_count - 1:index - 1 if index - 1 >= 0 else None:-1]

    def PlaylistChanged(self, playlist):
        self.con.emit_signal(None,
                             '/org/mpris/MediaPlayer2',
                             MediaPlayer2Service.MEDIA_PLAYER2_PLAYLISTS_IFACE,
                             'PlaylistChanged',
                             GLib.Variant.new_tuple(GLib.Variant('(oss)', playlist)))

    def Get(self, interface_name, property_name):
        return self.GetAll(interface_name)[property_name]

    def GetAll(self, interface_name):
        if interface_name == MediaPlayer2Service.MEDIA_PLAYER2_IFACE:
            return {
                'CanQuit': GLib.Variant('b', True),
                'Fullscreen': GLib.Variant('b', False),
                'CanSetFullscreen': GLib.Variant('b', False),
                'CanRaise': GLib.Variant('b', True),
                'HasTrackList': GLib.Variant('b', True),
                'Identity': GLib.Variant('s', 'Music'),
                'DesktopEntry': GLib.Variant('s', 'gnome-music'),
                'SupportedUriSchemes': GLib.Variant('as', [
                    'file'
                ]),
                'SupportedMimeTypes': GLib.Variant('as', [
                    'application/ogg',
                    'audio/x-vorbis+ogg',
                    'audio/x-flac',
                    'audio/mpeg'
                ]),
            }
        elif interface_name == MediaPlayer2Service.MEDIA_PLAYER2_PLAYER_IFACE:
            return {
                'PlaybackStatus': GLib.Variant('s', self._get_playback_status()),
                'LoopStatus': GLib.Variant('s', self._get_loop_status()),
                'Rate': GLib.Variant('d', 1.0),
                'Shuffle': GLib.Variant('b', self.player.repeat == RepeatType.SHUFFLE),
                'Metadata': GLib.Variant('a{sv}', self._get_metadata()),
                'Volume': GLib.Variant('d', self.player.get_volume()),
                'Position': GLib.Variant('x', self.player.get_position()),
                'MinimumRate': GLib.Variant('d', 1.0),
                'MaximumRate': GLib.Variant('d', 1.0),
                'CanGoNext': GLib.Variant('b', self.player.has_next()),
                'CanGoPrevious': GLib.Variant('b', self.player.has_previous()),
                'CanPlay': GLib.Variant('b', self.player.current_track is not None),
                'CanPause': GLib.Variant('b', self.player.current_track is not None),
                'CanSeek': GLib.Variant('b', True),
                'CanControl': GLib.Variant('b', True),
            }
        elif interface_name == MediaPlayer2Service.MEDIA_PLAYER2_TRACKLIST_IFACE:
            return {
                'Tracks': GLib.Variant('ao', self._get_track_list()),
                'CanEditTracks': GLib.Variant('b', False)
            }
        elif interface_name == MediaPlayer2Service.MEDIA_PLAYER2_PLAYLISTS_IFACE:
            return {
                'PlaylistCount': GLib.Variant('u', len(self.playlists)),
                'Orderings': GLib.Variant('as', ['Alphabetical']),
                'ActivePlaylist': GLib.Variant('(b(oss))', self._get_active_playlist()),
            }
        elif interface_name == 'org.freedesktop.DBus.Properties':
            return {}
        elif interface_name == 'org.freedesktop.DBus.Introspectable':
            return {}
        else:
            raise Exception(
                'org.mpris.MediaPlayer2.GnomeMusic',
                'This object does not implement the %s interface'
                % interface_name)

    def Set(self, interface_name, property_name, new_value):
        if interface_name == MediaPlayer2Service.MEDIA_PLAYER2_IFACE:
            if property_name == 'Fullscreen':
                pass
        elif interface_name == MediaPlayer2Service.MEDIA_PLAYER2_PLAYER_IFACE:
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
                if new_value:
                    self.player.set_repeat_mode(RepeatType.SHUFFLE)
                else:
                    self.player.set_repeat_mode(RepeatType.NONE)
        else:
            raise Exception(
                'org.mpris.MediaPlayer2.GnomeMusic',
                'This object does not implement the %s interface'
                % interface_name)

    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        self.con.emit_signal(None,
                             '/org/mpris/MediaPlayer2',
                             'org.freedesktop.DBus.Properties',
                             'PropertiesChanged',
                             GLib.Variant.new_tuple(GLib.Variant('s', interface_name),
                                                    GLib.Variant('a{sv}', changed_properties),
                                                    GLib.Variant('as', invalidated_properties)))

    def Introspect(self):
        return self.__doc__
