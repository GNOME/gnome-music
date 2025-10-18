# Copyright © 2018 The GNOME Music developers
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
from typing import List, Optional
from enum import IntEnum
import typing

from gettext import gettext as _, ngettext
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gtk, Gio, GObject, Gst, GstPbutils

if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


class Playback(IntEnum):
    """Playback status enumerator"""
    STOPPED = 0
    LOADING = 1
    PAUSED = 2
    PLAYING = 3


class GstPlayer(GObject.GObject):
    """Contains GStreamer logic for Player

    Handles GStreamer interaction for Player and SmoothScale.
    """
    __gsignals__ = {
        "about-to-finish": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "clock-tick": (GObject.SignalFlags.RUN_FIRST, None, (int, )),
        'eos': (GObject.SignalFlags.RUN_FIRST, None, ()),
        "error": (GObject.SignalFlags.RUN_FIRST, None, ()),
        'seek-finished': (GObject.SignalFlags.RUN_FIRST, None, ()),
        "stream-start": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    mute = GObject.Property(type=bool, default=False)
    volume = GObject.Property(type=float, default=1.)

    def __init__(self, application: Application) -> None:
        """Initialize the GStreamer player

        :param Application application: Application object
        """
        super().__init__()

        Gst.init(None)

        self._application = application
        self._buffering = False
        self._duration = -1.
        self._known_duration = False
        self._log = application.props.log
        self._seek = False
        self._tick = 0

        self._clock_id = 0
        self._clock: Optional[Gst.Clock] = None

        self._missing_plugin_messages: List[Gst.Message] = []
        self._settings = application.props.settings

        self._player = Gst.ElementFactory.make('playbin3', 'player')

        # Disable video output
        GST_PLAY_FLAGS_VIDEO = 1 << 0
        GST_PLAY_FLAGS_AUDIO = 1 << 1
        player_flags = GST_PLAY_FLAGS_AUDIO & ~GST_PLAY_FLAGS_VIDEO
        self._player.set_property("flags", player_flags)

        self._setup_replaygain()

        self._settings.connect(
            "changed::replaygain", self._on_replaygain_setting_changed)
        self._settings.emit("changed", "replaygain")

        self._bus = self._player.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect('message::async-done', self._on_async_done)
        self._bus.connect("message::buffering", self._on_bus_buffering)
        self._bus.connect(
            "message::duration-changed", self._on_duration_changed)
        self._bus.connect('message::error', self._on_bus_error)
        self._bus.connect('message::element', self._on_bus_element)
        self._bus.connect('message::eos', self._on_bus_eos)
        self._bus.connect('message::new-clock', self._on_new_clock)
        self._bus.connect("message::state-changed", self._on_state_changed)
        self._bus.connect("message::stream-start", self._on_bus_stream_start)

        self._player.connect("about-to-finish", self._on_about_to_finish)

        self._state = Playback.STOPPED

        self._player.bind_property(
            "volume", self, "volume", GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        self._player.bind_property(
            "mute", self, "mute", GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

    def _setup_replaygain(self):
        """Set up replaygain"""
        self._rg_volume = Gst.ElementFactory.make("rgvolume", "rg volume")
        self._rg_limiter = Gst.ElementFactory.make("rglimiter", "rg limiter")

        self._filter_bin = Gst.ElementFactory.make("bin", "filter bin")
        self._filter_bin.add(self._rg_volume)
        self._filter_bin.add(self._rg_limiter)
        self._rg_volume.link(self._rg_limiter)

        pad_src = self._rg_limiter.get_static_pad('src')
        ghost_src = Gst.GhostPad.new('src', pad_src)
        self._filter_bin.add_pad(ghost_src)

        pad_sink = self._rg_volume.get_static_pad('sink')
        ghost_sink = Gst.GhostPad.new('sink', pad_sink)
        self._filter_bin.add_pad(ghost_sink)

        if (not self._filter_bin
                or not self._rg_volume
                or not self._rg_limiter):
            self._log.message("Replay Gain is not available")
            return

    def _on_replaygain_setting_changed(
            self, settings: Gio.Settings, key: str) -> None:
        value = settings.get_string(key)

        if value != "disabled":
            self._player.set_property("audio-filter", self._filter_bin)

            if value == "album":
                self._rg_volume.props.album_mode = True
            else:
                self._rg_volume.props.album_mode = False
        else:
            self._player.set_property("audio-filter", None)

    def _on_about_to_finish(self, klass):
        self.emit("about-to-finish")

    def _on_async_done(self, bus, message):
        if self._seek:
            self._seek = False
            self.emit("seek-finished")

        if not self._known_duration:
            self._query_duration()

    def _on_duration_changed(self, bus: Gst.Bus, message: Gst.Message) -> None:
        self._query_duration()

    def _query_duration(self) -> None:
        self._known_duration, duration = self._player.query_duration(
            Gst.Format.TIME)

        if self._known_duration:
            self.props.duration = duration / Gst.SECOND
            self._log.debug("duration changed: {}".format(self.props.duration))
        else:
            self.props.duration = duration

    def _create_clock_tick(self):
        if self._clock_id > 0:
            return

        self._clock_id = self._clock.new_periodic_id(
            self._clock.get_time(), 1 * Gst.SECOND)
        self._clock.id_wait_async(self._clock_id, self._on_clock_tick, None)

    def _destroy_clock_tick(self) -> None:
        if (self._clock_id > 0
                and self._clock is not None):
            self._clock.id_unschedule(self._clock_id)
            self._clock_id = 0

    def _on_new_clock(self, bus, message):
        self._clock_id = 0
        self._clock = message.parse_new_clock()
        self._create_clock_tick()

    def _on_clock_tick(self, clock, time, id, data):
        self.emit("clock-tick", self._tick)
        self._tick += 1

    def _on_bus_element(self, bus, message):
        if GstPbutils.is_missing_plugin_message(message):
            self._missing_plugin_messages.append(message)

    def _on_bus_buffering(self, bus: Gst.Bus, message: Gst.Message) -> None:
        percent = message.parse_buffering()

        if (percent < 100
                and not self._buffering):
            self._buffering = True
            self.props.state = Playback.PAUSED
        elif percent == 100:
            self._buffering = False
            self.props.state = Playback.PLAYING

    def _on_bus_stream_start(self, bus, message):
        self._query_duration()
        self._tick = 0
        self.emit("stream-start")

    def _on_state_changed(self, bus, message):
        if message.src != self._player:
            return

        old_state, new_state, _ = message.parse_state_changed()
        self._log.debug(
            "Player state changed: {} -> {}".format(old_state, new_state))

        if new_state == Gst.State.PAUSED:
            self._state = Playback.PAUSED
            self._destroy_clock_tick()
        elif new_state == Gst.State.PLAYING:
            self._state = Playback.PLAYING
            self._create_clock_tick()
        elif new_state == Gst.State.READY:
            self._state = Playback.LOADING
        else:
            self._state = Playback.STOPPED

        self.notify("state")

    def _on_bus_error(self, bus, message):
        if self._is_missing_plugin_message(message):
            self.props.state = Playback.PAUSED
            self._handle_missing_plugins()
            return True

        error, debug = message.parse_error()
        debug = debug.split('\n')
        debug = [('     ') + line.lstrip() for line in debug]
        debug = '\n'.join(debug)
        self._log.warning("URI: {}".format(self.props.url))
        self._log.warning(
            "Error from element {}: {}".format(
                message.src.get_name(), error.message))
        self._log.warning("Debugging info:\n{}".format(debug))

        self.emit("error")
        return True

    def _on_bus_eos(self, bus, message):
        self.emit('eos')

    @GObject.Property(
        type=int, flags=GObject.ParamFlags.READWRITE
        | GObject.ParamFlags.EXPLICIT_NOTIFY)
    def state(self):
        """Current state of the player

        :return: state
        :rtype: Playback (enum)
        """
        return self._state

    @state.setter  # type: ignore
    def state(self, state):
        """Set state of the player

        :param Playback state: The state to set
        """
        if state == Playback.PAUSED:
            self._player.set_state(Gst.State.PAUSED)
        if state == Playback.STOPPED:
            # Changing the state to NULL flushes the pipeline.
            # Thus, the change message never arrives.
            self._player.set_state(Gst.State.NULL)
            self._state = Playback.STOPPED
            self.notify("state")
            self._destroy_clock_tick()
        if state == Playback.LOADING:
            self._player.set_state(Gst.State.READY)
        if state == Playback.PLAYING:
            self._player.set_state(Gst.State.PLAYING)

    @GObject.Property
    def url(self):
        """Current url loaded

        :return: url
        :rtype: string
        """
        return self._player.props.current_uri

    @url.setter  # type: ignore
    def url(self, url_):
        """url to load next

        :param string url: url to load
        """
        self._player.set_property('uri', url_)

    @GObject.Property
    def position(self):
        """Current player position

        Player position in seconds
        :return: position
        :rtype: float
        """
        position = self._player.query_position(Gst.Format.TIME)[1] / Gst.SECOND

        return position

    @GObject.Property(
        type=float, flags=GObject.ParamFlags.READWRITE
        | GObject.ParamFlags.EXPLICIT_NOTIFY)
    def duration(self):
        """Total duration of current media

        Total duration in seconds or -1. if not available
        :return: duration
        :rtype: float
        """
        if self.props.state == Playback.STOPPED:
            return -1.

        return self._duration

    # Setter provided to trigger a property signal.
    # For internal use only.
    @duration.setter  # type: ignore
    def duration(self, duration):
        """Set duration of current media (internal)

        For internal use only.
        """
        if duration != self._duration:
            self._duration = duration
            self.notify("duration")

    def seek(self, seconds):
        """Seek to position

        :param float seconds: Position in seconds to seek
        """
        self._seek = self._player.seek_simple(
            Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            seconds * Gst.SECOND)

    def _start_plugin_installation(
            self, missing_plugin_messages, confirm_search):
        install_ctx = GstPbutils.InstallPluginsContext.new()
        application_id = self._application.props.application_id
        install_ctx.set_desktop_id(application_id + '.desktop')
        install_ctx.set_confirm_search(confirm_search)

        startup_id = "_TIME{}".format(Gtk.get_current_event_time())
        install_ctx.set_startup_notification_id(startup_id)

        installer_details = []
        get_details = GstPbutils.missing_plugin_message_get_installer_detail
        for message in missing_plugin_messages:
            installer_detail = get_details(message)
            installer_details.append(installer_detail)

        def on_install_done(res):
            # We get the callback too soon, before the installation has
            # actually finished. Do nothing for now.
            pass

        GstPbutils.install_plugins_async(
            installer_details, install_ctx, on_install_done)

    def _show_codec_confirmation_dialog(
            self, install_helper_name, missing_plugin_messages):
        active_window = self._application.props.active_window
        dialog = MissingCodecsDialog(active_window, install_helper_name)

        def on_dialog_response(dialog, response_type):
            if response_type == Gtk.ResponseType.ACCEPT:
                self._start_plugin_installation(missing_plugin_messages, False)

            dialog.destroy()

        descriptions = []
        get_description = GstPbutils.missing_plugin_message_get_description
        for message in missing_plugin_messages:
            description = get_description(message)
            descriptions.append(description)

        dialog.set_codec_names(descriptions)
        dialog.connect('response', on_dialog_response)
        dialog.present()

    def _handle_missing_plugins(self):
        if not self._missing_plugin_messages:
            return

        missing_plugin_messages = self._missing_plugin_messages
        self._missing_plugin_messages = []

        proxy = Gio.DBusProxy.new_sync(
            Gio.bus_get_sync(Gio.BusType.SESSION, None),
            Gio.DBusProxyFlags.NONE, None, 'org.freedesktop.PackageKit',
            '/org/freedesktop/PackageKit',
            'org.freedesktop.PackageKit.Modify2', None)
        prop = Gio.DBusProxy.get_cached_property(proxy, 'DisplayName')
        if prop:
            display_name = prop.get_string()
            if display_name:
                self._show_codec_confirmation_dialog(
                    display_name, missing_plugin_messages)
                return

        # If the above failed, fall back to immediately starting the
        # codec installation.
        self._start_plugin_installation(missing_plugin_messages, True)

    def _is_missing_plugin_message(self, message):
        error, debug = message.parse_error()

        if error.matches(Gst.CoreError.quark(), Gst.CoreError.MISSING_PLUGIN):
            return True

        return False


class MissingCodecsDialog(Gtk.MessageDialog):

    def __init__(self, parent_window, install_helper_name):
        super().__init__(
            transient_for=parent_window, modal=True, destroy_with_parent=True,
            message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CANCEL,
            text=_("Unable to play the file"))

        # TRANSLATORS: this is a button to launch a codec installer.
        # {} will be replaced with the software installer's name, e.g.
        # 'Software' in case of gnome-software.
        self.find_button = self.add_button(
            _("_Find in {}").format(install_helper_name),
            Gtk.ResponseType.ACCEPT)
        self.set_default_response(Gtk.ResponseType.ACCEPT)
        Gtk.StyleContext.add_class(
            self.find_button.get_style_context(), 'suggested-action')

    def set_codec_names(self, codec_names):
        n_codecs = len(codec_names)
        if n_codecs == 2:
            # TRANSLATORS: separator for two codecs
            text = _(" and ").join(codec_names)
        else:
            # TRANSLATORS: separator for a list of codecs
            text = _(", ").join(codec_names)
        self.format_secondary_text(ngettext(
            "{} is required to play the file, but is not installed.",
            "{} are required to play the file, but are not installed.",
            n_codecs).format(text))
