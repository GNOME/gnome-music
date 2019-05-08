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

from gnomemusic.gstplayer import Playback
from gnomemusic.player import PlayerPlaylist, RepeatMode
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
        self.player = app.props.player
        self.player.connect(
            'song-changed', self._on_current_song_changed)
        self.player.connect('notify::state', self._on_player_state_changed)
        self.player.connect('notify::repeat-mode', self._on_repeat_mode_changed)
        self.player.connect('seek-finished', self._on_seek_finished)
        self.player.connect(
            'playlist-changed', self._on_player_playlist_changed)
        self.player_toolbar = app.get_active_window()._player_toolbar
        self.player_toolbar.connect(
            'thumbnail-updated', self._on_thumbnail_updated)
        playlists = Playlists.get_default()
        playlists.connect('playlist-created', self._on_playlists_count_changed)
        playlists.connect('playlist-deleted', self._on_playlists_count_changed)
        grilo.connect('ready', self._on_grilo_ready)
        self.playlists = []
        self._player_previous_type = None
        self._path_list = []
        self._metadata_list = []
        self._previous_playback_status = "Stopped"

    @log
    def _get_playback_status(self):
        state = self.player.props.state
        if state == Playback.PLAYING:
            return 'Playing'
        elif state == Playback.PAUSED:
            return 'Paused'
        else:
            return 'Stopped'

    @log
    def _get_loop_status(self):
        if self.player.props.repeat_mode == RepeatMode.NONE:
            return 'None'
        elif self.player.props.repeat_mode == RepeatMode.SONG:
            return 'Track'
        else:
            return 'Playlist'

    @log
    def _get_metadata(self, media=None):
        if not media:
            media = self.player.props.current_song
        if not media:
            return {}

        song_dbus_path = self._get_song_dbus_path(media)
        metadata = {
            'mpris:trackid': GLib.Variant('o', song_dbus_path),
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
    def _get_song_dbus_path(self, media):
        """Convert a Grilo media to a D-Bus path

        The hex encoding is used to remove any possible invalid character.

        :param Grl.Media media: The media object
        :return: a D-Bus id to uniquely identify the song
        :rtype: str
        """
        if not media:
            return "/org/mpris/MediaPlayer2/TrackList/NoTrack"

        id_hex = media.get_id().encode('ascii').hex()
        path = "/org/gnome/GnomeMusic/TrackList/{}".format(id_hex)
        return path

    @log
    def _update_songs_list(self):
        previous_path_list = self._path_list
        self._path_list = []
        self._metadata_list = []
        for song in self.player.get_mpris_playlist():
            path = self._get_song_dbus_path(song)
            metadata = self._get_metadata(song)
            self._path_list.append(path)
            self._metadata_list.append(metadata)

        # current song has changed
        if (not previous_path_list
                or previous_path_list[0] != self._path_list[0]
                or previous_path_list[-1] != self._path_list[-1]):
            current_song_path = self._get_song_dbus_path(
                self.player.props.current_song)
            self.TrackListReplaced(self._path_list, current_song_path)
            self.PropertiesChanged(
                MediaPlayer2Service.MEDIA_PLAYER2_TRACKLIST_IFACE,
                {'Tracks': GLib.Variant('ao', self._path_list), }, [])

    @log
    def _get_playlist_dbus_path(self, playlist):
        """Convert a playlist to a D-Bus path

        :param Grl.media playlist: The playlist object
        :return: a D-Bus id to uniquely identify the playlist
        :rtype: str
        """
        if playlist:
            id_ = playlist.get_id()
        else:
            id_ = 'Invalid'

        return '/org/mpris/MediaPlayer2/Playlist/{}'.format(id_)

    @log
    def _get_playlist_from_dbus_path(self, playlist_path):
        for playlist in self.playlists:
            if playlist_path == self._get_playlist_dbus_path(playlist):
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
        """Get Active Maybe_Playlist

        Maybe_Playlist is a structure describing a playlist, or nothing
        according to MPRIS specifications.
        If a playlist is active, return True and its description
        (path, name and icon).
        If no playlist is active, return False and an undefined structure.
        :returns: playlist existence and its structure
        :rtype: tuple
        """
        if self.player.get_playlist_type() != PlayerPlaylist.Type.PLAYLIST:
            return (False, ("/", "", ""))

        playlist = self._get_playlist_from_id(self.player.get_playlist_id())
        playlist_name = utils.get_media_title(playlist)
        path = self._get_playlist_dbus_path(playlist)
        return (True, (path, playlist_name, ""))

    @log
    def _on_current_song_changed(self, player, position):
        self._update_songs_list()
        if self.player.props.repeat_mode == RepeatMode.SONG:
            self.Seeked(0)

        has_next = self.player.props.has_next
        has_previous = self.player.props.has_previous
        self.PropertiesChanged(MediaPlayer2Service.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'Metadata': GLib.Variant('a{sv}', self._get_metadata()),
                                   'CanGoNext': GLib.Variant('b', has_next),
                                   'CanGoPrevious': GLib.Variant(
                                       'b', has_previous),
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
    def _on_player_state_changed(self, klass, args):
        playback_status = self._get_playback_status()
        if playback_status == self._previous_playback_status:
            return

        self._previous_playback_status = playback_status
        self.PropertiesChanged(MediaPlayer2Service.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'PlaybackStatus': GLib.Variant('s', playback_status),
                               },
                               [])

    @log
    def _on_repeat_mode_changed(self, player, param):
        self._update_songs_list()
        has_next = self.player.props.has_next
        has_previous = self.player.props.has_previous
        self.PropertiesChanged(MediaPlayer2Service.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'CanGoNext': GLib.Variant('b', has_next),
                                   'CanGoPrevious': GLib.Variant('b', has_previous),
                                   'LoopStatus': GLib.Variant('s', self._get_loop_status()),
                                   'Shuffle': GLib.Variant('b', self.player.props.repeat_mode == RepeatMode.SHUFFLE),
                               },
                               [])

    @log
    def _on_seek_finished(self, player, position_second):
        self.Seeked(int(position_second * 1e6))

    @log
    def _on_player_playlist_changed(self, klass):
        self._update_songs_list()

        if (self.player.get_playlist_type() == PlayerPlaylist.Type.PLAYLIST
                or self._player_previous_type == PlayerPlaylist.Type.PLAYLIST):
            variant = GLib.Variant('(b(oss))', self._get_active_playlist())
            self.PropertiesChanged(
                MediaPlayer2Service.MEDIA_PLAYER2_PLAYLISTS_IFACE,
                {'ActivePlaylist':  variant, }, [])

        self._player_previous_type = klass.get_playlist_type()

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
        self.player.next()

    def Previous(self):
        self.player.previous()

    def Pause(self):
        self.player.pause()

    def PlayPause(self):
        self.player.play_pause()

    def Stop(self):
        self.player.stop()

    def Play(self):
        """Start or resume playback.

        If there is no track to play, this has no effect.
        """
        self.player.play()

    def Seek(self, offset_msecond):
        """Seek forward in the current track.

        Seek is relative to the current player position.
        If the value passed in would mean seeking beyond the end of the track,
        acts like a call to Next.
        :param int offset_msecond: number of microseconds
        """
        current_position_second = self.player.get_position()
        new_position_second = current_position_second + offset_msecond / 1e6

        duration_second = self.player.props.duration
        if new_position_second <= duration_second:
            self.player.set_position(new_position_second)
        else:
            self.player.next()

    def SetPosition(self, track_id, position_msecond):
        """Set the current track position in microseconds.

        :param str track_id: The currently playing track's identifier
        :param int position_msecond: new position in microseconds
        """
        if track_id != self._get_metadata().get('mpris:trackid').get_string():
            return
        self.player.set_position(position_msecond / 1e6)

    def OpenUri(self, uri):
        pass

    def Seeked(self, position_msecond):
        """Indicate that the track position has changed.

        :param int position_msecond: new position in microseconds.
        """
        variant = GLib.Variant.new_tuple(GLib.Variant('x', position_msecond))
        self.con.emit_signal(
            None, '/org/mpris/MediaPlayer2',
            MediaPlayer2Service.MEDIA_PLAYER2_PLAYER_IFACE, 'Seeked', variant)

    def GetTracksMetadata(self, track_paths):
        metadata = []
        for path in track_paths:
            index = self._path_list.index(path)
            metadata.append(self._metadata_list[index])
        return metadata

    def AddTrack(self, uri, after_track, set_as_current):
        pass

    def RemoveTrack(self, path):
        pass

    def GoTo(self, path):
        current_song_path = self._get_song_dbus_path(
            self.player.props.current_song)
        current_song_index = self._path_list.index(current_song_path)
        goto_index = self._path_list.index(path)
        self.player.play(goto_index - current_song_index)
        return

    def TrackListReplaced(self, tracks, current_song):
        self.con.emit_signal(None,
                             '/org/mpris/MediaPlayer2',
                             MediaPlayer2Service.MEDIA_PLAYER2_TRACKLIST_IFACE,
                             'TrackListReplaced',
                             GLib.Variant.new_tuple(GLib.Variant('ao', tracks),
                                                    GLib.Variant('o', current_song)))

    def TrackAdded(self, metadata, after_track):
        self.con.emit_signal(None,
                             '/org/mpris/MediaPlayer2',
                             MediaPlayer2Service.MEDIA_PLAYER2_TRACKLIST_IFACE,
                             'TrackAdded',
                             GLib.Variant.new_tuple(GLib.Variant('a{sv}', metadata),
                                                    GLib.Variant('o', after_track)))

    def TrackRemoved(self, path):
        self.con.emit_signal(
            None, '/org/mpris/MediaPlayer2',
            MediaPlayer2Service.MEDIA_PLAYER2_TRACKLIST_IFACE, 'TrackRemoved',
            GLib.Variant.new_tuple(GLib.Variant('o', path)))

    def TrackMetadataChanged(self, path, metadata):
        self.con.emit_signal(
            None, '/org/mpris/MediaPlayer2',
            MediaPlayer2Service.MEDIA_PLAYER2_TRACKLIST_IFACE,
            'TrackMetadataChanged',
            GLib.Variant.new_tuple(
                GLib.Variant('o', path), GLib.Variant('a{sv}', metadata)))

    def ActivatePlaylist(self, playlist_path):
        playlist_id = self._get_playlist_from_dbus_path(playlist_path).get_id()
        self.app._window.views[View.PLAYLIST].activate_playlist(playlist_id)

    def GetPlaylists(self, index, max_count, order, reverse):
        if order != 'Alphabetical':
            return []
        playlists = [(self._get_playlist_dbus_path(playlist),
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
            application_id = self.app.props.application_id
            return {
                'CanQuit': GLib.Variant('b', True),
                'Fullscreen': GLib.Variant('b', False),
                'CanSetFullscreen': GLib.Variant('b', False),
                'CanRaise': GLib.Variant('b', True),
                'HasTrackList': GLib.Variant('b', True),
                'Identity': GLib.Variant('s', 'Music'),
                'DesktopEntry': GLib.Variant('s', application_id),
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
            position_msecond = int(self.player.get_position() * 1e6)
            return {
                'PlaybackStatus': GLib.Variant('s', self._get_playback_status()),
                'LoopStatus': GLib.Variant('s', self._get_loop_status()),
                'Rate': GLib.Variant('d', 1.0),
                'Shuffle': GLib.Variant('b', self.player.props.repeat_mode == RepeatMode.SHUFFLE),
                'Metadata': GLib.Variant('a{sv}', self._get_metadata()),
                'Position': GLib.Variant('x', position_msecond),
                'MinimumRate': GLib.Variant('d', 1.0),
                'MaximumRate': GLib.Variant('d', 1.0),
                'CanGoNext': GLib.Variant('b', self.player.props.has_next),
                'CanGoPrevious': GLib.Variant('b', self.player.props.has_previous),
                'CanPlay': GLib.Variant('b', self.player.props.current_song is not None),
                'CanPause': GLib.Variant('b', self.player.props.current_song is not None),
                'CanSeek': GLib.Variant('b', True),
                'CanControl': GLib.Variant('b', True),
            }
        elif interface_name == MediaPlayer2Service.MEDIA_PLAYER2_TRACKLIST_IFACE:
            return {
                'Tracks': GLib.Variant('ao', self._path_list),
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
            if property_name in ['Rate', 'Volume']:
                pass
            elif property_name == 'LoopStatus':
                if new_value == 'None':
                    self.player.props.repeat_mode = RepeatMode.NONE
                elif new_value == 'Track':
                    self.player.props.repeat_mode = RepeatMode.SONG
                elif new_value == 'Playlist':
                    self.player.props.repeat_mode = RepeatMode.ALL
            elif property_name == 'Shuffle':
                if new_value:
                    self.player.props.repeat_mode = RepeatMode.SHUFFLE
                else:
                    self.player.props.repeat_mode = RepeatMode.NONE
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
