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
from gnomemusic.albumartcache import lookup_art_file_from_cache
from gnomemusic.grilo import grilo
from gnomemusic.gstplayer import Playback
from gnomemusic.player import PlayerPlaylist, RepeatMode
from gnomemusic.playlists import Playlists
import gnomemusic.utils as utils

logger = logging.getLogger(__name__)


class DBusInterface:

    def __init__(self, name, path):
        """Etablish a D-Bus session connection

        :param str name: interface name
        :param str path: object path
        """
        self._path = path
        Gio.bus_get(Gio.BusType.SESSION, None, self._bus_get_sync, name)

    def _bus_get_sync(self, source, res, name):
        try:
            self._con = Gio.bus_get_finish(res)
        except GLib.Error as e:
            logger.warning(
                "Unable to connect to to session bus: {}".format(e.message))
            return

        Gio.bus_own_name_on_connection(
            self._con, name, Gio.BusNameOwnerFlags.NONE, None, None)

        method_outargs = {}
        method_inargs = {}
        signals = {}
        for interface in Gio.DBusNodeInfo.new_for_xml(self.__doc__).interfaces:

            for method in interface.methods:
                method_outargs[method.name] = "(" + "".join(
                    [arg.signature for arg in method.out_args]) + ")"
                method_inargs[method.name] = tuple(
                    arg.signature for arg in method.in_args)

            for signal in interface.signals:
                args = {arg.name: arg.signature for arg in signal.args}
                signals[signal.name] = {
                    'interface': interface.name, 'args': args}

            self._con.register_object(
                object_path=self._path, interface_info=interface,
                method_call_closure=self._on_method_call)

        self._method_inargs = method_inargs
        self._method_outargs = method_outargs
        self._signals = signals

    def _on_method_call(
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

        method_snake_name = DBusInterface.camelcase_to_snake_case(method_name)
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

    @staticmethod
    def camelcase_to_snake_case(name):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return '_' + re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


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
            <property name='Tracks' type='ao' access='read'/>
            <property name='CanEditTracks' type='b' access='read'/>
        </interface>
        <interface name='org.mpris.MediaPlayer2.Playlists'>
            <method name='ActivatePlaylist'>
                <arg direction="in" name="PlaylistId" type="o" />
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
        return "<MPRIS>"

    def __init__(self, app):
        name = 'org.mpris.MediaPlayer2.GnomeMusic'
        path = '/org/mpris/MediaPlayer2'
        super().__init__(name, path)

        self._app = app
        self._player = app.props.player
        self._player.connect(
            'song-changed', self._on_current_song_changed)
        self._player.connect('notify::state', self._on_player_state_changed)
        self._player.connect(
            'notify::repeat-mode', self._on_repeat_mode_changed)
        self._player.connect('seek-finished', self._on_seek_finished)
        self._player.connect(
            'playlist-changed', self._on_player_playlist_changed)

        self._playlists = Playlists.get_default()
        self._playlists.connect(
            'playlist-created', self._on_playlists_count_changed)
        self._playlists.connect(
            'playlist-deleted', self._on_playlists_count_changed)
        self._playlists.connect('playlist-renamed', self._on_playlist_renamed)
        grilo.connect('ready', self._on_grilo_ready)
        self._stored_playlists = []
        self._player_previous_type = None
        self._path_list = []
        self._metadata_list = []
        self._previous_can_go_next = False
        self._previous_can_go_previous = False
        self._previous_can_play = False
        self._previous_is_shuffled = None
        self._previous_loop_status = ""
        self._previous_mpris_playlist = self._get_active_playlist()
        self._previous_playback_status = "Stopped"

    @log
    def _get_playback_status(self):
        state = self._player.props.state
        if state == Playback.STOPPED:
            return 'Stopped'
        elif state == Playback.PAUSED:
            return 'Paused'
        else:
            return 'Playing'

    @log
    def _get_loop_status(self):
        if self._player.props.repeat_mode == RepeatMode.NONE:
            return 'None'
        elif self._player.props.repeat_mode == RepeatMode.SONG:
            return 'Track'
        else:
            return 'Playlist'

    @log
    def _get_metadata(self, media=None, index=None):
        song_dbus_path = self._get_song_dbus_path(media, index)
        if not self._player.props.current_song:
            return {
                'mpris:trackid': GLib.Variant('o', song_dbus_path)
            }

        if not media:
            media = self._player.props.current_song

        length = media.get_duration() * 1e6
        user_rating = 1.0 if media.get_favourite() else 0.0
        artist = utils.get_artist_name(media)

        metadata = {
            'mpris:trackid': GLib.Variant('o', song_dbus_path),
            'xesam:url': GLib.Variant('s', media.get_url()),
            'mpris:length': GLib.Variant('x', length),
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
            last_played_str = last_played.format("%FT%T%:z")
            metadata['xesam:lastUsed'] = GLib.Variant('s', last_played_str)

        track_nr = media.get_track_number()
        if track_nr > 0:
            metadata['xesam:trackNumber'] = GLib.Variant('i', track_nr)

        # If the media has already been part of an MPRIS playlist, its
        # thumbnail is already set. Otherwise, try to look for it in the
        # cache directory and set the media thumbnail for a future use.
        # The search is only through the cache to prevent any delayed
        # loading.
        # FIXME: The thumbnail retrieval should take place in the
        # player.
        art_url = media.get_thumbnail()
        if not art_url:
            thumb_file = lookup_art_file_from_cache(media)
            if thumb_file:
                art_url = GLib.filename_to_uri(thumb_file.get_path())
                media.set_thumbnail(art_url)

        if art_url:
            metadata['mpris:artUrl'] = GLib.Variant('s', art_url)

        return metadata

    @log
    def _get_song_dbus_path(self, media=None, index=None):
        """Convert a Grilo media to a D-Bus path

        The hex encoding is used to remove any possible invalid character.
        Use player index to make the path truly unique in case the same song
        is present multiple times in a playlist.
        If media is None, it means that the current song path is requested.

        :param Grl.Media media: The media object
        :param int index: The media position in the current playlist
        :return: a D-Bus id to uniquely identify the song
        :rtype: str
        """
        if not self._player.props.current_song:
            return "/org/mpris/MediaPlayer2/TrackList/NoTrack"

        if not media:
            media = self._player.props.current_song
            index = self._player.props.current_song_index

        id_hex = media.get_id().encode('ascii').hex()
        path = "/org/gnome/GnomeMusic/TrackList/{}_{}".format(
            id_hex, index)
        return path

    @log
    def _update_songs_list(self):
        previous_path_list = self._path_list
        self._path_list = []
        self._metadata_list = []
        for index, song in self._player.get_mpris_playlist():
            path = self._get_song_dbus_path(song, index)
            metadata = self._get_metadata(song, index)
            self._path_list.append(path)
            self._metadata_list.append(metadata)

        # current song has changed
        if (not previous_path_list
                or previous_path_list[0] != self._path_list[0]
                or previous_path_list[-1] != self._path_list[-1]):
            current_song_path = self._get_song_dbus_path()
            self._track_list_replaced(self._path_list, current_song_path)

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
        for playlist in self._stored_playlists:
            if playlist_path == self._get_playlist_dbus_path(playlist):
                return playlist
        return None

    @log
    def _get_mpris_playlist_from_playlist(self, playlist):
        playlist_name = utils.get_media_title(playlist)
        path = self._get_playlist_dbus_path(playlist)
        return (path, playlist_name, "")

    @log
    def _get_playlist_from_id(self, playlist_id):
        for playlist in self._stored_playlists:
            if playlist_id == playlist.get_id():
                return playlist
        return None

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
        if self._player.get_playlist_type() != PlayerPlaylist.Type.PLAYLIST:
            return (False, ("/", "", ""))

        playlist = self._get_playlist_from_id(self._player.get_playlist_id())
        mpris_playlist = self._get_mpris_playlist_from_playlist(playlist)
        return (True, mpris_playlist)

    @log
    def _on_current_song_changed(self, player):
        # In repeat song mode, no metadata has changed if the
        # player was already started
        if self._player.props.repeat_mode == RepeatMode.SONG:
            self._seeked(0)
            if self._previous_can_play is True:
                return

        self._update_songs_list()

        properties = {}
        properties["Metadata"] = GLib.Variant("a{sv}", self._get_metadata())

        has_next = self._player.props.has_next
        if has_next != self._previous_can_go_next:
            properties["CanGoNext"] = GLib.Variant("b", has_next)
            self._previous_can_go_next = has_next

        has_previous = self._player.props.has_previous
        if has_previous != self._previous_can_go_previous:
            properties["CanGoPrevious"] = GLib.Variant("b", has_previous)
            self._previous_can_go_previous = has_previous

        if self._previous_can_play is not True:
            properties["CanPause"] = GLib.Variant("b", has_previous)
            properties["CanPlay"] = GLib.Variant("b", has_previous)
            self._previous_can_play = True

        self._properties_changed(
            MPRIS.MEDIA_PLAYER2_PLAYER_IFACE, properties, [])

    @log
    def _on_player_state_changed(self, klass, args):
        playback_status = self._get_playback_status()
        if playback_status == self._previous_playback_status:
            return

        self._previous_playback_status = playback_status
        self._properties_changed(MPRIS.MEDIA_PLAYER2_PLAYER_IFACE,
                               {
                                   'PlaybackStatus': GLib.Variant('s', playback_status),
                               },
                               [])

    @log
    def _on_repeat_mode_changed(self, player, param):
        self._update_songs_list()

        properties = {}

        is_shuffled = self._player.props.repeat_mode == RepeatMode.SHUFFLE
        if is_shuffled != self._previous_is_shuffled:
            properties["Shuffle"] = GLib.Variant("b", is_shuffled)
            self._previous_is_shuffled = is_shuffled

        loop_status = self._get_loop_status()
        if loop_status != self._previous_loop_status:
            properties["LoopStatus"] = GLib.Variant("s", loop_status)
            self._previous_loop_status = loop_status

        if not properties:
            return
        self._properties_changed(
            MPRIS.MEDIA_PLAYER2_PLAYER_IFACE, properties, [])

    @log
    def _on_seek_finished(self, player):
        position_second = self._player.get_position()
        self._seeked(int(position_second * 1e6))

    @log
    def _on_player_playlist_changed(self, klass):
        self._update_songs_list()

        mpris_playlist = self._get_active_playlist()
        if mpris_playlist == self._previous_mpris_playlist:
            return

        self._previous_mpris_playlist = mpris_playlist
        properties = {
            "ActivePlaylist": GLib.Variant("(b(oss))", mpris_playlist)}
        self._properties_changed(
            MPRIS.MEDIA_PLAYER2_PLAYLISTS_IFACE, properties, [])

    @log
    def _reload_playlists(self):
        def _populate_cb(source, param, item, remaining=0, data=None):
            if item:
                self._stored_playlists.append(item)
            else:
                playlists_nr = len(self._stored_playlists)
                self._properties_changed(
                    MPRIS.MEDIA_PLAYER2_PLAYLISTS_IFACE,
                    {'PlaylistCount': GLib.Variant('u', playlists_nr), }, [])

        self._stored_playlists = []
        grilo.populate_playlists(0, _populate_cb)

    @log
    def _on_playlists_count_changed(self, playlists, item):
        self._reload_playlists()

    @log
    def _on_playlist_renamed(self, playlists, renamed_playlist):
        mpris_playlist = self._get_mpris_playlist_from_playlist(
            renamed_playlist)
        self._dbus_emit_signal('PlaylistChanged', {'Playlist': mpris_playlist})

    @log
    def _on_grilo_ready(self, grilo):
        self._reload_playlists()

    def _raise(self):
        """Brings user interface to the front (MPRIS Method)."""
        self._app.do_activate()

    def _quit(self):
        """Causes the media player to stop running (MPRIS Method)."""
        self._app.quit()

    def _next(self):
        """Skips to the next track in the tracklist (MPRIS Method)."""
        self._player.next()

    def _previous(self):
        """Skips to the previous track in the tracklist.

        (MPRIS Method)
        """
        self._player.previous()

    def _pause(self):
        """Pauses playback (MPRIS Method)."""
        self._player.pause()

    def _play_pause(self):
        """Play or Pauses playback (MPRIS Method)."""
        self._player.play_pause()

    def _stop(self):
        """Stop playback (MPRIS Method)."""
        self._player.stop()

    def _play(self):
        """Start or resume playback (MPRIS Method).

        If there is no track to play, this has no effect.
        """
        self._player.play()

    def _seek(self, offset_msecond):
        """Seek forward in the current track (MPRIS Method).

        Seek is relative to the current player position.
        If the value passed in would mean seeking beyond the end of the track,
        acts like a call to Next.

        :param int offset_msecond: number of microseconds
        """
        current_position_second = self._player.get_position()
        new_position_second = current_position_second + offset_msecond / 1e6

        duration_second = self._player.props.duration
        if new_position_second <= duration_second:
            self._player.set_position(new_position_second)
        else:
            self._player.next()

    def _set_position(self, track_id, position_msecond):
        """Set the current track position in microseconds (MPRIS Method)

        :param str track_id: The currently playing track's identifier
        :param int position_msecond: new position in microseconds
        """
        metadata = self._get_metadata()
        current_track_id = metadata["mpris:trackid"].get_string()
        if track_id != current_track_id:
            return
        self._player.set_position(position_msecond / 1e6)

    def _open_uri(self, uri):
        """Opens the Uri given as an argument (MPRIS Method).

        Not implemented.

        :param str uri: Uri of the track to load.
        """
        pass

    def _seeked(self, position_msecond):
        """Indicate that the track position has changed.

        :param int position_msecond: new position in microseconds.
        """
        self._dbus_emit_signal("Seeked", {"Position": position_msecond})

    def _get_tracks_metadata(self, track_paths):
        """Gets all the metadata available for a set of tracks.

        (MPRIS Method)

        :param list track_paths: list of track ids
        :returns: Metadata of the set of tracks given as input.
        :rtype: list
        """
        metadata = []
        for path in track_paths:
            index = self._path_list.index(path)
            metadata.append(self._metadata_list[index])
        return metadata

    def _add_track(self, uri, after_track, set_as_current):
        """Adds a URI in the TrackList. (MPRIS Method).

        This is not implemented (CanEditTracks is set to False).
        """
        pass

    def _remove_track(self, path):
        """Removes an item from the TrackList. (MPRIS Method).

        This is not implemented (CanEditTracks is set to False).
        """
        pass

    def _go_to(self, path):
        """Skip to the specified TrackId (MPRIS Method).

        :param str path: Identifier of the track to skip to
        """
        current_song_path = self._get_song_dbus_path()
        current_song_index = self._path_list.index(current_song_path)
        goto_index = self._path_list.index(path)
        song_offset = goto_index - current_song_index
        self._player.play(song_offset=song_offset)

    def _track_list_replaced(self, tracks, current_song):
        parameters = {
            "Tracks": self._path_list,
            "CurrentTrack": self._get_song_dbus_path()}
        self._dbus_emit_signal("TrackListReplaced", parameters)

    def _activate_playlist(self, playlist_path):
        """Starts playing the given playlist (MPRIS Method).

        :param str playlist_path: The id of the playlist to activate.
        """
        playlist_id = self._get_playlist_from_dbus_path(playlist_path).get_id()
        self._playlists.activate_playlist(playlist_id)

    def _get_playlists(self, index, max_count, order, reverse):
        """Gets a set of playlists (MPRIS Method).

        GNOME Music only handles playlists with the Alphabetical order.

        :param int index: the index of the first playlist to be fetched
        :param int max_count: the maximum number of playlists to fetch.
        :param str order: the ordering that should be used.
        :param bool reverse: whether the order should be reversed.
        """
        if order != 'Alphabetical':
            return []

        mpris_playlists = [self._get_mpris_playlist_from_playlist(playlist)
                           for playlist in self._stored_playlists]

        if not reverse:
            return mpris_playlists[index:index + max_count]

        first_index = index - 1
        if first_index < 0:
            first_index = None
        return mpris_playlists[index + max_count - 1:first_index:-1]

    def _get(self, interface_name, property_name):
        return self._get_all(interface_name)[property_name]

    def _get_all(self, interface_name):
        if interface_name == MPRIS.MEDIA_PLAYER2_IFACE:
            application_id = self._app.props.application_id
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
        elif interface_name == MPRIS.MEDIA_PLAYER2_PLAYER_IFACE:
            position_msecond = int(self._player.get_position() * 1e6)
            return {
                'PlaybackStatus': GLib.Variant('s', self._get_playback_status()),
                'LoopStatus': GLib.Variant('s', self._get_loop_status()),
                'Rate': GLib.Variant('d', 1.0),
                'Shuffle': GLib.Variant('b', self._player.props.repeat_mode == RepeatMode.SHUFFLE),
                'Metadata': GLib.Variant('a{sv}', self._get_metadata()),
                'Position': GLib.Variant('x', position_msecond),
                'MinimumRate': GLib.Variant('d', 1.0),
                'MaximumRate': GLib.Variant('d', 1.0),
                'CanGoNext': GLib.Variant('b', self._player.props.has_next),
                'CanGoPrevious': GLib.Variant('b', self._player.props.has_previous),
                'CanPlay': GLib.Variant('b', self._player.props.current_song is not None),
                'CanPause': GLib.Variant('b', self._player.props.current_song is not None),
                'CanSeek': GLib.Variant('b', True),
                'CanControl': GLib.Variant('b', True),
            }
        elif interface_name == MPRIS.MEDIA_PLAYER2_TRACKLIST_IFACE:
            return {
                'Tracks': GLib.Variant('ao', self._path_list),
                'CanEditTracks': GLib.Variant('b', False)
            }
        elif interface_name == MPRIS.MEDIA_PLAYER2_PLAYLISTS_IFACE:
            playlist_count = len(self._stored_playlists)
            return {
                'PlaylistCount': GLib.Variant('u', playlist_count),
                'Orderings': GLib.Variant('as', ['Alphabetical']),
                'ActivePlaylist': GLib.Variant('(b(oss))', self._get_active_playlist()),
            }
        elif interface_name == 'org.freedesktop.DBus.Properties':
            return {}
        elif interface_name == 'org.freedesktop.DBus.Introspectable':
            return {}
        else:
            logger.warning(
                "MPRIS does not implement {} interface".format(interface_name))

    def _set(self, interface_name, property_name, new_value):
        if interface_name == MPRIS.MEDIA_PLAYER2_IFACE:
            if property_name == 'Fullscreen':
                pass
        elif interface_name == MPRIS.MEDIA_PLAYER2_PLAYER_IFACE:
            if property_name in ['Rate', 'Volume']:
                pass
            elif property_name == 'LoopStatus':
                if new_value == 'None':
                    self._player.props.repeat_mode = RepeatMode.NONE
                elif new_value == 'Track':
                    self._player.props.repeat_mode = RepeatMode.SONG
                elif new_value == 'Playlist':
                    self._player.props.repeat_mode = RepeatMode.ALL
            elif property_name == 'Shuffle':
                if new_value:
                    self._player.props.repeat_mode = RepeatMode.SHUFFLE
                else:
                    self._player.props.repeat_mode = RepeatMode.NONE
        else:
            logger.warning(
                "MPRIS does not implement {} interface".format(interface_name))

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
