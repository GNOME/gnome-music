# Copyright 2019 The GNOME Music developers
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

from __future__ import annotations
import asyncio
import re
import typing

from gi.repository import Gio, GLib

from gnomemusic.gstplayer import Playback
from gnomemusic.player import RepeatMode
from gnomemusic.queue import Queue
from gnomemusic.widgets.songwidget import SongWidget

if typing.TYPE_CHECKING:
    from gi.repository import GObject, Gtk

    from gnomemusic.coresong import CoreSong
    from gnomemusic.player import Player


class DBusInterface:

    def __init__(self, name, path, application):
        """Etablish a D-Bus session connection

        :param str name: interface name
        :param str path: object path
        :param GtkApplication application: The Application object
        """
        self._con: Gio.DBusConnection
        self._log = application.props.log
        self._path = path
        self._signals = None

        asyncio.create_task(self._get_bus(name))

    async def _get_bus(self, name: str) -> None:
        try:
            self._con = await Gio.bus_get(Gio.BusType.SESSION, None)
        except GLib.Error as error:
            self._log.warning(
                f"Unable to connect to the session bus: {error.message}")
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
                self._path, interface, self._on_method_call, None, None)

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
            if sig == 'h':
                msg = invocation.get_message()
                fd_list = msg.get_unix_fd_list()
                args[i] = fd_list.get(args[i])

        method_snake_name = DBusInterface.camelcase_to_snake_case(method_name)
        try:
            result = getattr(self, method_snake_name)(*args)
        except ValueError as e:
            invocation.return_dbus_error(interface_name, str(e))
            return

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
        if self._signals is None:
            return

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

    _playlist_nb_songs = 10

    def __init__(self, app):
        name = "org.mpris.MediaPlayer2.{}".format(app.props.application_id)
        path = '/org/mpris/MediaPlayer2'
        super().__init__(name, path, app)

        self._app = app
        self._log = app.props.log
        self._player = app.props.player
        self._player.connect(
            'song-changed', self._on_current_song_changed)
        self._player.connect('notify::state', self._on_player_state_changed)
        self._player.connect(
            'notify::repeat-mode', self._on_repeat_mode_changed)
        self._player.connect('seek-finished', self._on_seek_finished)

        self._coremodel = app.props.coremodel
        self._player_model = self._coremodel.props.queue_sort
        self._player_model_changed_id = None

        self._coremodel.connect(
            "queue-loaded", self._on_player_playlist_changed)

        self._playlists_model = self._coremodel.props.playlists_sort
        n_items = self._playlists_model.get_n_items()
        self._on_playlists_items_changed(
            self._playlists_model, 0, n_items, n_items)
        self._playlists_model.connect(
            "items-changed", self._on_playlists_items_changed)

        self._recent_queue = self._coremodel.props.recent_queue
        self._recent_queue.connect(
            "items-changed", self._on_recent_queue_changed)

        self._player_playlist_type = None
        self._path_list = []
        self._metadata_list = []
        self._previous_can_go_next = False
        self._previous_can_go_previous = False
        self._previous_can_play = False
        self._previous_is_shuffled = None
        self._previous_loop_status = ""
        self._previous_mpris_playlist = self._get_active_playlist()
        self._previous_playback_status = "Stopped"
        self._thumbnail_id = 0
        self._current_coresong = None

    def _get_playback_status(self):
        state = self._player.props.state
        if state == Playback.STOPPED:
            return 'Stopped'
        elif state == Playback.PAUSED:
            return 'Paused'
        else:
            return 'Playing'

    def _get_loop_status(self):
        if self._player.props.repeat_mode == RepeatMode.ALL:
            return "Playlist"
        elif self._player.props.repeat_mode == RepeatMode.SONG:
            return "Track"
        else:
            return "None"

    def _get_metadata(self, coresong=None, index=None):
        song_dbus_path = self._get_song_dbus_path(coresong, index)
        if not self._player.props.current_song:
            return {
                'mpris:trackid': GLib.Variant('o', song_dbus_path)
            }

        if not coresong:
            coresong = self._player.props.current_song

        length = coresong.props.duration * 1e6
        user_rating = 1.0 if coresong.props.favorite else 0.0
        artist = coresong.props.artist

        metadata = {
            'mpris:trackid': GLib.Variant('o', song_dbus_path),
            'xesam:url': GLib.Variant('s', coresong.props.url),
            'mpris:length': GLib.Variant('x', length),
            'xesam:useCount': GLib.Variant('i', coresong.props.play_count),
            'xesam:userRating': GLib.Variant('d', user_rating),
            'xesam:title': GLib.Variant('s', coresong.props.title),
            'xesam:album': GLib.Variant('s', coresong.props.album),
            'xesam:artist': GLib.Variant('as', [artist]),
            'xesam:albumArtist': GLib.Variant('as', [artist])
        }

        last_played = coresong.props.last_played
        if last_played is not None:
            last_played_str = last_played.format("%FT%T%:z")
            metadata['xesam:lastUsed'] = GLib.Variant('s', last_played_str)

        track_nr = coresong.props.track_number
        if track_nr > 0:
            metadata['xesam:trackNumber'] = GLib.Variant('i', track_nr)

        art_url = coresong.props.thumbnail
        if (art_url == "generic"
                and self._current_coresong == coresong):
            self._thumbnail_id = coresong.connect(
                "notify::thumbnail", self._on_thumbnail_changed)
        else:
            metadata['mpris:artUrl'] = GLib.Variant('s', art_url)

        return metadata

    def _on_thumbnail_changed(
            self, coresong: CoreSong, param: GObject.ParamSpecString) -> None:
        """Updates MPRIS metadata when a song's thumbnail changes.

        :param coresong: The song with the new thumbnail.
        :param param_spec: Metadata about the changed property.
        :param user_data: Optional; unused.
        """
        if coresong != self._player.props.current_song:
            return

        properties = {}
        properties["Metadata"] = GLib.Variant(
            "a{sv}", self._get_metadata(coresong))
        self._properties_changed(
            MPRIS.MEDIA_PLAYER2_PLAYER_IFACE, properties, [])

    def _get_song_dbus_path(self, coresong=None, index=None):
        """Convert a CoreSong to a D-Bus path

        The hex encoding is used to remove any possible invalid
        character. Use player index to make the path truly unique in
        case the same song is present multiple times in a playlist.
        If coresong is None, it means that the current song path is
        requested.

        :param CoreSong coresong: The CoreSong object
        :param int index: The media position in the current playlist
        :return: a D-Bus id to uniquely identify the song
        :rtype: str
        """
        if not self._player.props.current_song:
            return "/org/mpris/MediaPlayer2/TrackList/NoTrack"

        if not coresong:
            coresong = self._player.props.current_song
            index = self._player.props.position

        id_hex = coresong.props.id.encode('ascii').hex()
        path = "/org/gnome/GnomeMusic/TrackList/{}_{}".format(
            id_hex, index)
        return path

    def _on_recent_queue_changed(
            self, model: Gtk.SliceListModel, position: int, removed: int,
            added: int) -> None:
        self._path_list = []
        self._metadata_list = []

        offset = self._recent_queue.get_offset()
        for position, coresong in enumerate(self._recent_queue):
            offset_position = position + offset
            self._path_list.append(
                self._get_song_dbus_path(coresong, offset_position))
            self._metadata_list.append(
                self._get_metadata(coresong, offset_position))

        current_song_path = self._get_song_dbus_path()
        self._track_list_replaced(self._path_list, current_song_path)

    def _get_playlist_dbus_path(self, playlist):
        """Convert a playlist to a D-Bus path

        :param Playlist playlist: The playlist object
        :return: a D-Bus id to uniquely identify the playlist
        :rtype: str
        """
        if not playlist:
            return "/"

        # Smart Playlists do not have an id
        pl_id = playlist.props.pl_id or playlist.props.tag_text
        pl_id = pl_id.rsplit(":")[-1].replace("-", "")
        return "/org/gnome/GnomeMusic/Playlist/{}".format(pl_id)

    def _get_mpris_playlist_from_playlist(self, playlist):
        playlist_name = playlist.props.title
        path = self._get_playlist_dbus_path(playlist)
        return (path, playlist_name, "")

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
        current_core_object = self._coremodel.props.active_core_object
        if not isinstance(current_core_object, Queue):
            return (False, ("/", "", ""))

        mpris_playlist = self._get_mpris_playlist_from_playlist(
            current_core_object)
        return (True, mpris_playlist)

    def _on_current_song_changed(self, player: Player) -> None:
        if (self._thumbnail_id != 0
                and self._current_coresong):
            self._current_coresong.disconnect(self._thumbnail_id)
            self._thumbnail_id = 0

        self._current_coresong = player.props.current_song

        # In repeat song mode, no metadata has changed if the
        # player was already started
        if self._player.props.repeat_mode == RepeatMode.SONG:
            self._seeked(0)
            if self._previous_can_play is True:
                return

        if self._player_model_changed_id is None:
            self._player_model_changed_id = self._player_model.connect_after(
                "items-changed", self._on_player_model_changed)

        self._on_player_model_changed(self._player_model, 0, 0, 0)

    def _on_player_model_changed(self, model, pos, removed, added):
        # Do no update the properties if the model has completely changed.
        # These changes will be applied once a new song starts playing.
        if added == model.get_n_items():
            return

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
            properties["CanPause"] = GLib.Variant("b", True)
            properties["CanPlay"] = GLib.Variant("b", True)
            self._previous_can_play = True

        self._properties_changed(
            MPRIS.MEDIA_PLAYER2_PLAYER_IFACE, properties, [])

    def _on_player_state_changed(self, klass, args):
        playback_status = self._get_playback_status()
        if playback_status == self._previous_playback_status:
            return

        self._previous_playback_status = playback_status
        self._properties_changed(
            MPRIS.MEDIA_PLAYER2_PLAYER_IFACE,
            {'PlaybackStatus': GLib.Variant('s', playback_status), }, [])

    def _on_repeat_mode_changed(self, player, param):
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

    def _on_seek_finished(self, player):
        position_second = self._player.get_position()
        self._seeked(int(position_second * 1e6))

    def _on_player_playlist_changed(self, coremodel, playlist_type):
        self._player_playlist_type = playlist_type

        mpris_playlist = self._get_active_playlist()
        if mpris_playlist == self._previous_mpris_playlist:
            return

        self._previous_mpris_playlist = mpris_playlist
        properties = {
            "ActivePlaylist": GLib.Variant("(b(oss))", mpris_playlist)}
        self._properties_changed(
            MPRIS.MEDIA_PLAYER2_PLAYLISTS_IFACE, properties, [])

    def _on_playlists_items_changed(self, model, position, removed, added):
        if added > 0:
            for i in range(added):
                playlist = model[position + i]
                playlist.connect("notify::title", self._on_playlist_renamed)
                playlist.connect(
                    "notify::active", self._on_player_playlist_changed)

        playlist_count = model.get_n_items()
        properties = {"PlaylistCount": GLib.Variant("u", playlist_count)}
        self._properties_changed(
            MPRIS.MEDIA_PLAYER2_PLAYLISTS_IFACE, properties, [])

    def _on_playlist_renamed(self, playlist, param):
        mpris_playlist = self._get_mpris_playlist_from_playlist(playlist)
        self._dbus_emit_signal('PlaylistChanged', {'Playlist': mpris_playlist})

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
        current_index = self._path_list.index(self._get_song_dbus_path())
        current_coresong = self._player.props.current_song

        goto_index = self._path_list.index(path)
        new_position = self._player.props.position + goto_index - current_index
        new_coresong = self._player_model[new_position]

        self._player.play(new_coresong)
        current_coresong.props.state = SongWidget.State.PLAYED
        new_coresong.props.state = SongWidget.State.PLAYING

    def _track_list_replaced(self, track_paths, current_song_path):
        """Indicate that the entire tracklist has been replaced.

        (MPRIS Method)

        :param list track_paths: the new list of tracks
        :param current_song_path: the id of the current song
        """
        parameters = {
            "Tracks": track_paths,
            "CurrentTrack": current_song_path}
        self._dbus_emit_signal("TrackListReplaced", parameters)

    def _load_player_playlist(self, playlist):
        def _on_playlist_loaded(klass, playlist_type):
            self._player.play()
            self._coremodel.disconnect(loaded_id)

        loaded_id = self._coremodel.connect(
            "queue-loaded", _on_playlist_loaded)
        self._coremodel.props.active_core_object = playlist

    def _activate_playlist(self, playlist_path):
        """Starts playing the given playlist (MPRIS Method).

        :param str playlist_path: The id of the playlist to activate.
        """
        selected_playlist = None
        for playlist in self._playlists_model:
            if playlist_path == self._get_playlist_dbus_path(playlist):
                selected_playlist = playlist
                break

        if selected_playlist is None:
            return

        def _on_playlist_model_loaded(playlist):
            playlist.disconnect(signal_id)
            self._load_player_playlist(playlist)

        if selected_playlist.props.model.get_n_items() > 0:
            self._load_player_playlist(selected_playlist)
        else:
            signal_id = selected_playlist.connect(
                "queue-loaded", _on_playlist_model_loaded)

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
                           for playlist in self._playlists_model]

        if not reverse:
            return mpris_playlists[index:index + max_count]

        first_index = index - 1
        if first_index < 0:
            first_index = None
        return mpris_playlists[index + max_count - 1:first_index:-1]

    def _get(self, interface_name, property_name):
        # Some clients (for example GSConnect) try to acesss the volume
        # property. This results in a crash at startup.
        # Return nothing to prevent it.
        try:
            return self._get_all(interface_name)[property_name]
        except KeyError:
            msg = "MPRIS does not handle {} property from {} interface".format(
                property_name, interface_name)
            self._log.warning(msg)
            raise ValueError(msg)

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
            playback_status = self._get_playback_status()
            is_shuffle = (self._player.props.repeat_mode == RepeatMode.SHUFFLE)
            can_play = (self._player.props.current_song is not None)
            has_previous = (self._player.props.has_previous)
            return {
                'PlaybackStatus': GLib.Variant('s', playback_status),
                'LoopStatus': GLib.Variant('s', self._get_loop_status()),
                'Rate': GLib.Variant('d', 1.0),
                'Shuffle': GLib.Variant('b', is_shuffle),
                'Metadata': GLib.Variant('a{sv}', self._get_metadata()),
                'Position': GLib.Variant('x', position_msecond),
                'MinimumRate': GLib.Variant('d', 1.0),
                'MaximumRate': GLib.Variant('d', 1.0),
                'CanGoNext': GLib.Variant('b', self._player.props.has_next),
                'CanGoPrevious': GLib.Variant('b', has_previous),
                'CanPlay': GLib.Variant('b', can_play),
                'CanPause': GLib.Variant('b', can_play),
                'CanSeek': GLib.Variant('b', True),
                'CanControl': GLib.Variant('b', True),
            }
        elif interface_name == MPRIS.MEDIA_PLAYER2_TRACKLIST_IFACE:
            return {
                'Tracks': GLib.Variant('ao', self._path_list),
                'CanEditTracks': GLib.Variant('b', False)
            }
        elif interface_name == MPRIS.MEDIA_PLAYER2_PLAYLISTS_IFACE:
            playlist_count = self._playlists_model.get_n_items()
            active_playlist = self._get_active_playlist()
            return {
                'PlaylistCount': GLib.Variant('u', playlist_count),
                'Orderings': GLib.Variant('as', ['Alphabetical']),
                'ActivePlaylist': GLib.Variant('(b(oss))', active_playlist),
            }
        elif interface_name == 'org.freedesktop.DBus.Properties':
            return {}
        elif interface_name == 'org.freedesktop.DBus.Introspectable':
            return {}
        else:
            self._log.warning(
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
            self._log.warning(
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
