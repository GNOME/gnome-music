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

import logging
import re

from gi.repository import Gio, GLib

from gnomemusic import log
from gnomemusic.gstplayer import Playback
from gnomemusic.player import PlayerPlaylist, RepeatMode
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists
from gnomemusic.utils import View
import gnomemusic.utils as utils

logger = logging.getLogger(__name__)


def camelcase_to_snake_case(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return '_' + re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class DBusInterface:

    def __init__(self, name, path):
        self._con = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        Gio.bus_own_name_on_connection(
            self._con, name, Gio.BusNameOwnerFlags.NONE, None, None)
        self._path = path

        method_outargs = {}
        method_inargs = {}
        signals = {}
        for interface in Gio.DBusNodeInfo.new_for_xml(self.__doc__).interfaces:

            for method in interface.methods:
                method_outargs[method.name] = '(' + ''.join(
                    [arg.signature for arg in method.out_args]) + ')'
                method_inargs[method.name] = tuple(
                    arg.signature for arg in method.in_args)

            for signal in interface.signals:
                args = {arg.name: arg.signature for arg in signal.args}
                signals[signal.name] = {
                    'interface': interface.name, 'args': args}

            self._con.register_object(
                object_path=self._path, interface_info=interface,
                method_call_closure=self.on_method_call)

        self._method_inargs = method_inargs
        self._method_outargs = method_outargs
        self._signals = signals

    def on_method_call(
        self, connection, sender, object_path, interface_name, method_name,
            parameters, invocation):
        """GObject.Closure to handle incoming method calls.

        :param Gio.DBusConnection connection: D-Bus connection
        :param str sender: bus name that invoked the method
        :param srt object_path: object path the method was invoked on
        :param str interface_name: name of the D-Bus interface
        :param str method_name: name of the method that was invoked
        :param GLib.Variant parameters: parameters of the method invocation
        :param Gio.DBusMethodInvocation invocation: invocation
        """
        args = list(parameters.unpack())
        for i, sig in enumerate(self._method_inargs[method_name]):
            if sig is 'h':
                msg = invocation.get_message()
                fd_list = msg.get_unix_fd_list()
                args[i] = fd_list.get(args[i])

        method_snake_name = camelcase_to_snake_case(method_name)
        result = getattr(self, method_snake_name)(*args)

        # out_args is at least (signature1). We therefore always wrap the
        # result as a tuple.
        # Reference:
        # https://bugzilla.gnome.org/show_bug.cgi?id=765603
        result = (result,)

        out_args = self._method_outargs[method_name]
        if out_args != '()':
            variant = GLib.Variant(out_args, result)
            invocation.return_value(variant)
        else:
            invocation.return_value(None)

    def _dbus_emit_signal(self, signal_name, values):
        signal = self._signals[signal_name]
        parameters = []
        for arg_name, arg_signature in signal['args'].items():
            value = values[arg_name]
            parameters.append(GLib.Variant(arg_signature, value))

        variant = GLib.Variant.new_tuple(*parameters)
        self._con.emit_signal(
            None, self._path, signal['interface'], signal_name, variant)


class MPRIS(DBusInterface):
    """
    <!DOCTYPE node PUBLIC
    '-//freedesktop//DTD D-BUS Object Introspection 1.0//EN'
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
            <method name='Set'>
                <arg name='interface_name' direction='in' type='s'/>
                <arg name='property_name' direction='in' type='s'/>
                <arg name='value' direction='in' type='v'/>
            </method>
            <method name='GetAll'>
                <arg name='interface' direction='in' type='s'/>
                <arg name='properties' direction='out' type='a{sv}'/>
            </method>
            <signal name='PropertiesChanged'>
                <arg name='interface_name' type='s' />
                <arg name='changed_properties' type='a{sv}' />
                <arg name='invalidated_properties' type='as' />
            </signal>
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
        <interface name='org.mpris.MediaPlayer2.Playlists'>
            <method name='ActivatePlaylist'>
            </method>
            <method name='GetPlaylists'>
                <arg direction='in' name='Index' type='u' />
                <arg direction='in' name='MaxCount' type='u' />
                <arg direction='in' name='Order' type='s' />
                <arg direction='in' name='ReverseOrder' type='b' />
                <arg direction='out' name='Playlists' type='a(oss)' />
            </method>
            <property name='PlaylistCount' type='u' access='read' />
            <property name='Orderings' type='as' access='read' />
            <property name='ActivePlaylist' type='(b(oss))' access='read' />
            <signal name='PlaylistChanged'>
                <arg name='Playlist' type='(oss)' />
            </signal>
        </interface>
    </node>
    """

    MEDIA_PLAYER2_IFACE = 'org.mpris.MediaPlayer2'
    MEDIA_PLAYER2_PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'
    MEDIA_PLAYER2_TRACKLIST_IFACE = 'org.mpris.MediaPlayer2.TrackList'
    MEDIA_PLAYER2_PLAYLISTS_IFACE = 'org.mpris.MediaPlayer2.Playlists'

    def __repr__(self):
        return '<MPRIS>'

    def __init__(self, app):
        name = 'org.mpris.MediaPlayer2.GnomeMusic'
        path = '/org/mpris/MediaPlayer2'
        super().__init__(name, path)

        self._app = app
        self.player = app.get_active_window()._player
        self.player.connect(
            'song-changed', self._on_current_song_changed)
        self.player.connect('notify::state', self._on_player_state_changed)
        self.player.connect('notify::repeat-mode', self._on_repeat_mode_changed)
        self.player.connect('prev-next-invalidated', self._on_prev_next_invalidated)
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
        self._playlists = []
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
    def _get_metadata(self, media):
        song_dbus_path = self._get_song_dbus_path(media)
        if not media:
            return {
                'mpris:trackid': GLib.Variant('o', song_dbus_path)
            }

        length = media.get_duration() * 1e6
        user_rating = 1.0 if media.get_favourite() else 0.0
        artist = utils.get_artist_name(media)

        metadata = {
            'mpris:trackid': GLib.Variant('o', song_dbus_path),
            'xesam:url': GLib.Variant('s', media.get_url()),
            'mpris:length': GLib.Variant('x', length),
            'xesam:trackNumber': GLib.Variant('i', media.get_track_number()),
            'xesam:useCount': GLib.Variant('i', media.get_play_count()),
            'xesam:userRating': GLib.Variant('d', user_rating),
            'xesam:title': GLib.Variant('s', utils.get_media_title(media)),
            'xesam:album': GLib.Variant('s', utils.get_album_title(media)),
            'xesam:artist': GLib.Variant('as', [artist]),
            'xesam:albumArtist': GLib.Variant('as', [artist])
        }

        genre = media.get_genre()
        if genre is not None:
            metadata['xesam:genre'] = GLib.Variant('as', [genre])

        last_played = media.get_last_played()
        if last_played is not None:
            metadata['xesam:lastUsed'] = GLib.Variant('s', last_played)

        art_url = media.get_thumbnail()
        if art_url is not None:
            metadata['mpris:artUrl'] = GLib.Variant('s', art_url)

        return metadata

    @log
    def _get_song_dbus_path(self, media):
        """Convert a Grilo media to a D-Bus path

        The hex encoding is used to remove any possible invalid character.
        Use player index to make the path truly unique in case the same song
        is present multiple times in a playlist.

        :param Grl.Media media: The media object
        :return: a D-Bus id to uniquely identify the song
        :rtype: str
        """
        if not media:
            return "/org/mpris/MediaPlayer2/TrackList/NoTrack"

        id_hex = media.get_id().encode('ascii').hex()
        current_index = self.player.get_current_index()
        path = "/org/gnome/GnomeMusic/TrackList/{}_{}".format(
            id_hex, current_index)
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
            self._track_list_replaced(self._path_list, current_song_path)
            self._properties_changed(
                MPRIS.MEDIA_PLAYER2_TRACKLIST_IFACE,
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
        for playlist in self._playlists:
            if playlist_path == self._get_playlist_dbus_path(playlist):
                return playlist
        return None

    @log
    def _get_playlist_from_id(self, playlist_id):
        for playlist in self._playlists:
            if playlist_id == playlist.get_id():
                return playlist
        return None

    @log
    def _query_playlists(self, callback):
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
            self._seeked(0)

        has_next = self.player.props.has_next
        has_previous = self.player.props.has_previous
        metadata = self._get_metadata(self.player.props.current_song)
        self._properties_changed(
            MPRIS.MEDIA_PLAYER2_PLAYER_IFACE,
            {
                'CanGoNext': GLib.Variant('b', has_next),
                'CanGoPrevious': GLib.Variant('b', has_previous),
                'CanPause': GLib.Variant('b', True),
                'CanPlay': GLib.Variant('b', True),
                'Metadata': GLib.Variant('a{sv}', metadata),
            },
            [])

    @log
    def _on_thumbnail_updated(self, player, data=None):
        metadata = self._get_metadata(self.player.props.current_song)
        self._properties_changed(
            MPRIS.MEDIA_PLAYER2_PLAYER_IFACE,
            {
                'Metadata': GLib.Variant('a{sv}', metadata),
            },
            [])

    @log
    def _on_player_state_changed(self, klass, args):
        playback_status = self._get_playback_status()
        if playback_status == self._previous_playback_status:
            return

        self._previous_playback_status = playback_status
        self._properties_changed(
            MPRIS.MEDIA_PLAYER2_PLAYER_IFACE,
            {
                'PlaybackStatus': GLib.Variant('s', playback_status),
            },
            [])

    @log
    def _on_repeat_mode_changed(self, player, param):
        is_shuffle = self.player.props.repeat_mode == RepeatMode.SHUFFLE
        self._properties_changed(
            MPRIS.MEDIA_PLAYER2_PLAYER_IFACE,
            {
                'LoopStatus': GLib.Variant('s', self._get_loop_status()),
                'Shuffle': GLib.Variant('b', is_shuffle),
            },
            [])

    @log
    def _on_prev_next_invalidated(self, player, data=None):
        has_next = self.player.props.has_next
        has_previous = self.player.props.has_previous
        self._properties_changed(
            MPRIS.MEDIA_PLAYER2_PLAYER_IFACE,
            {
                'CanGoNext': GLib.Variant('b', has_previous),
                'CanGoPrevious': GLib.Variant('b', has_next),
            },
            [])

    @log
    def _on_seek_finished(self, player, position_second):
        self._seeked(int(position_second * 1e6))

    @log
    def _on_player_playlist_changed(self, klass):
        self._update_songs_list()

        if (self.player.get_playlist_type() == PlayerPlaylist.Type.PLAYLIST
                or self._player_previous_type == PlayerPlaylist.Type.PLAYLIST):
            variant = GLib.Variant('(b(oss))', self._get_active_playlist())
            self._properties_changed(
                MPRIS.MEDIA_PLAYER2_PLAYLISTS_IFACE,
                {'ActivePlaylist': variant, }, [])

        self._player_previous_type = klass.get_playlist_type()

    @log
    def _reload_playlists(self):
        def query_playlists_callback(playlists):
            self._playlists = playlists
            self._properties_changed(
                MPRIS.MEDIA_PLAYER2_PLAYLISTS_IFACE,
                {
                    'PlaylistCount': GLib.Variant('u', len(playlists)),
                },
                [])

        self._query_playlists(query_playlists_callback)

    @log
    def _on_playlists_count_changed(self, playlists, item):
        self._reload_playlists()

    @log
    def _on_grilo_ready(self, grilo):
        self._reload_playlists()

    def _raise(self):
        self._app.do_activate()

    def _quit(self):
        self._app.quit()

    def _next(self):
        self.player.next()

    def _previous(self):
        self.player.previous()

    def _pause(self):
        self.player.pause()

    def _play_pause(self):
        self.player.play_pause()

    def _stop(self):
        self.player.stop()

    def _play(self):
        """Start or resume playback.

        If there is no track to play, this has no effect.
        """
        self.player.play()

    def _seek(self, offset_msecond):
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

    def _set_position(self, path, position_msecond):
        """Set the current track position in microseconds.

        :param str track_id: The currently playing track's identifier
        :param int position_msecond: new position in microseconds
        """
        current_track_id = self._get_metadata(self.player.props.current_song)
        if current_track_id != current_track_id.get_string():
            return
        self.player.set_position(position_msecond / 1e6)

    def _open_uri(self, uri):
        pass

    def _seeked(self, position_msecond):
        """Indicate that the track position has changed.

        :param int position_msecond: new position in microseconds.
        """
        self._dbus_emit_signal('Seeked', {'Position': position_msecond})

    def _get_tracks_metadata(self, track_paths):
        metadata = []
        for path in track_paths:
            index = self._path_list.index(path)
            metadata.append(self._metadata_list[index])
        return metadata

    def _add_track(self, uri, after_track, set_as_current):
        pass

    def _remove_track(self, path):
        pass

    def _go_to(self, path):
        current_song_path = self._get_song_dbus_path(
            self.player.props.current_song)
        current_song_index = self._path_list.index(current_song_path)
        goto_index = self._path_list.index(path)
        self.player.play(goto_index - current_song_index)
        return

    def _track_list_replaced(self, tracks, current_song):
        parameters = {'Tracks': tracks, 'CurrentTrack': current_song}
        self._dbus_emit_signal('TrackListReplaced', parameters)

    def _track_added(self, metadata, after_track):
        parameters = {'Metadata': metadata, 'AfterTrack': after_track}
        self._dbus_emit_signal('TrackAdded', parameters)

    def _track_removed(self, path):
        self._dbus_emit_signal('TrackRemoved', {'TrackRemoved': path})

    def _track_metadata_changed(self, path, metadata):
        parameters = {'TrackId': path, 'Metadata': metadata}
        self._dbus_emit_signal('TrackMetadataChanged', parameters)

    def _activate_playlist(self, playlist_path):
        playlist_id = self._get_playlist_from_path(playlist_path).get_id()
        self._app._window.views[View.PLAYLIST].activate_playlist(playlist_id)

    def _get_playlists(self, index, max_count, order, reverse):
        if order != 'Alphabetical':
            return []

        playlists = [(self._get_playlist_dbus_path(playlist),
                      utils.get_media_title(playlist), '')
                     for playlist in self._playlists]

        if not reverse:
            return playlists[index:index + max_count]

        first_index = index-1
        if first_index < 0:
            first_index = None
        return playlists[index + max_count - 1:first_index:-1]

    def PlaylistChanged(self, playlist):
        self._dbus_emit_signal('PlaylistChanged', {'foo': playlist})

    def _get(self, interface_name, property_name):
        return self._get_all(interface_name)[property_name]

    def _get_all(self, interface_name):
        if interface_name == MPRIS.MEDIA_PLAYER2_IFACE:
            return {
                'CanQuit': GLib.Variant('b', True),
                'Fullscreen': GLib.Variant('b', False),
                'CanSetFullscreen': GLib.Variant('b', False),
                'CanRaise': GLib.Variant('b', True),
                'HasTrackList': GLib.Variant('b', True),
                'Identity': GLib.Variant('s', 'Music'),
                'DesktopEntry': GLib.Variant('s', 'org.gnome.Music'),
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
        elif interface_name == MPRIS.MEDIA_PLAYER2_PLAYER_IFACE:
            position_msecond = int(self.player.get_position() * 1e6)
            return {
                'PlaybackStatus': GLib.Variant('s', self._get_playback_status()),
                'LoopStatus': GLib.Variant('s', self._get_loop_status()),
                'Rate': GLib.Variant('d', 1.0),
                'Shuffle': GLib.Variant('b', self.player.props.repeat_mode == RepeatMode.SHUFFLE),
                'Metadata': GLib.Variant('a{sv}', metadata),
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
        elif interface_name == MPRIS.MEDIA_PLAYER2_TRACKLIST_IFACE:
            return {
                'Tracks': GLib.Variant('ao', self._path_list),
                'CanEditTracks': GLib.Variant('b', False)
            }
        elif interface_name == MPRIS.MEDIA_PLAYER2_PLAYLISTS_IFACE:
            return {
                'PlaylistCount': GLib.Variant('u', len(self._playlists)),
                'Orderings': GLib.Variant('as', ['Alphabetical']),
                'ActivePlaylist': GLib.Variant('(b(oss))', self._get_active_playlist()),
            }
        elif interface_name == 'org.freedesktop.DBus.Properties':
            return {}
        elif interface_name == 'org.freedesktop.DBus.Introspectable':
            return {}
        else:
            logger.warning(
                'MPRIS does not implement {} interface'.format(interface_name))

    def _set(self, interface_name, property_name, new_value):
        if interface_name == MPRIS.MEDIA_PLAYER2_IFACE:
            if property_name == 'Fullscreen':
                pass
        elif interface_name == MPRIS.MEDIA_PLAYER2_PLAYER_IFACE:
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
            logger.warning(
                'MPRIS does not implement {} interface'.format(interface_name))

    def _properties_changed(self, interface_name, changed_properties,
                            invalidated_properties):
        parameters = {
            'interface_name': interface_name,
            'changed_properties': changed_properties,
            'invalidated_properties': invalidated_properties
        }
        self._dbus_emit_signal('PropertiesChanged', parameters)

    def _introspect(self):
        return self.__doc__
