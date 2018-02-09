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

from enum import IntEnum
import logging

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstAudio', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gtk, Gio, GObject, Gst, GstAudio, GstPbutils
from gettext import gettext as _, ngettext

from gnomemusic import log
from gnomemusic.playlists import Playlists

logger = logging.getLogger(__name__)
playlists = Playlists.get_default()


class Playback(IntEnum):
    STOPPED = 0
    PAUSED = 1
    PLAYING = 2


class GstPlayer(GObject.GObject):

    __gsignals__ = {
        'eos': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    @log
    def __init__(self):
        super().__init__()

        Gst.init(None)

        self._settings = Gio.Settings.new('org.gnome.Music')

        self._player = Gst.ElementFactory.make('playbin3', 'player')
        self._bus = self._player.get_bus()
        self._bus.add_signal_watch()
        self._setup_replaygain()

        replaygain = self._settings.get_value('replaygain') is not None
        self._toggle_replaygain(replaygain)

        self._settings.connect(
            'changed::replaygain', self._on_replaygain_setting_changed)

        self._bus.connect('message::state-changed', self._on_bus_state_changed)
        self._bus.connect('message::error', self._on_bus_error)
        self._bus.connect('message::element', self._on_bus_element)
        self._bus.connect('message::eos', self._on_bus_eos)
        self._bus.connect(
            'message::duration-changed', self._on_duration_changed)

    @log
    def _setup_replaygain(self):
        """Set up replaygain

        See https://github.com/gnumdk/lollypop/commit/429383c3742e631b34937d8987d780edc52303c0
        """
        self._rgfilter = Gst.ElementFactory.make("bin", "bin")
        self._rg_audioconvert1 = Gst.ElementFactory.make(
            "audioconvert", "audioconvert")
        self._rg_audioconvert2 = Gst.ElementFactory.make(
            "audioconvert", "audioconvert2")
        self._rgvolume = Gst.ElementFactory.make("rgvolume", "rgvolume")
        self._rglimiter = Gst.ElementFactory.make("rglimiter", "rglimiter")
        self._rg_audiosink = Gst.ElementFactory.make(
            "autoaudiosink", "autoaudiosink")

        if (not self._rgfilter
                or not self._rg_audioconvert1
                or not self._rg_audioconvert2
                or not self._rgvolume
                or not self._rglimiter
                or not self._rg_audiosink):
            logger.debug("Replay Gain is not available")
            return

        self._rgvolume.props.pre_amp = 0.0
        self._rgfilter.add(self._rgvolume)
        self._rgfilter.add(self._rg_audioconvert1)
        self._rgfilter.add(self._rg_audioconvert2)
        self._rgfilter.add(self._rglimiter)
        self._rgfilter.add(self._rg_audiosink)
        self._rg_audioconvert1.link(self._rgvolume)
        self._rgvolume.link(self._rg_audioconvert2)
        self._rgvolume.link(self._rglimiter)
        self._rg_audioconvert2.link(self._rg_audiosink)
        self._rgfilter.add_pad(Gst.GhostPad.new(
            "sink", self._rg_audioconvert1.get_static_pad("sink")))

    @log
    def _toggle_replaygain(self, state=False):
        if state and self._rgfilter:
            self._player.set_property("audio-sink", self._rgfilter)
        else:
            self._player.set_property("audio-sink", None)

    @log
    def _on_replaygain_setting_changed(self, settings, value):
        replaygain = settings.get_value('replaygain') is not None
        self._toggle_replaygain(replaygain)

    @log
    def _on_bus_state_changed(self, bus, message):
        print(message.type, self.state)
        # Note: not all state changes are signaled through here, in
        # particular transitions between Gst.State.READY and
        # Gst.State.NULL are never async and thus don't cause a
        # message. In practice, self means only Gst.State.PLAYING and
        # Gst.State.PAUSED are.
        self.state = self.state

    @log
    def _on_duration_changed(self, bus, message):
        self._duration = self._player.query_duration(
            Gst.Format.TIME)[1] / 10**9

    @log
    def _on_bus_element(self, bus, message):
        if GstPbutils.is_missing_plugin_message(message):
            self._missingPluginMessages.append(message)

    @log
    def _on_bus_error(self, bus, message):
        if self._is_missing_plugin_message(message):
            self.state = Playback.PAUSED
            self._handle_missing_plugins()
            return True

        # FIXME: This shouldn't be here
        # validation stuff
#        media = self.get_current_media()
#        if media is not None:
#            if self.currentTrack and self.currentTrack.valid():
#                currentTrack = self.playlist.get_iter(
#                    self.currentTrack.get_path())
#                self.playlist.set_value(
#                    currentTrack, self.discovery_status_field, DiscoveryStatus.FAILED)
#            uri = media.get_url()
#        else:
#            uri = 'none'

        # TODO: What does this do exactly?
        error, debug = message.parse_error()
        debug = debug.split('\n')
        debug = [('     ') + line.lstrip() for line in debug]
        debug = '\n'.join(debug)
        logger.warn("URI: {}".format(self.url))
        logger.warn(
            "Error from element {}: {}", message.src.get_name(), error.message)
        logger.warn("Debugging info:\n{}", debug)

        self.emit('eos')
        return True

    @log
    def _on_bus_eos(self, bus, message):
        self.emit('eos')

    @log
    def is_playing(self):
        ok, state, pending = self._player.get_state(0)

        if ok == Gst.StateChangeReturn.ASYNC:
            return pending == Gst.State.PLAYING
        elif ok == Gst.StateChangeReturn.SUCCESS:
            return state == Gst.State.PLAYING

        return False

    @log
    def _get_playback_status(self):
        ok, state, pending = self._player.get_state(0)
        if ok == Gst.StateChangeReturn.ASYNC:
            state = pending
        elif (ok != Gst.StateChangeReturn.SUCCESS):
            return Playback.STOPPED

        if state == Gst.State.PLAYING:
            return Playback.PLAYING
        elif state == Gst.State.PAUSED:
            return Playback.PAUSED

        return Playback.STOPPED

    @GObject.Property
    @log
    def state(self):
        return self._get_playback_status()

    @state.setter
    @log
    def state(self, state):
        if state == Playback.PAUSED:
            self._player.set_state(Gst.State.PAUSED)
        if state == Playback.STOPPED:
            self._player.set_state(Gst.State.NULL)
        if state == Playback.PLAYING:
            self._player.set_state(Gst.State.PLAYING)

    @GObject.Property
    @log
    def url(self):
        return self._player.get_value('current-uri', 0)

    @url.setter
    @log
    def url(self, url_):
        self._player.set_property('uri', url_)

    @GObject.Property
    @log
    def position(self):
        """Position in seconds (float)"""
        position = self._player.query_position(Gst.Format.TIME)[1] / 10**9
        print("position ", position)
        return position

    @GObject.Property
    @log
    def duration(self):
        """Total duration in seconds (float)"""
        print("duration ", self._duration)
        return self._duration

    @GObject.Property
    @log
    def volume(self):
        volume = self._player.get_volume(GstAudio.StreamVolumeFormat.LINEAR)
        return volume

    @volume.setter
    def volume(self, rate):
        self._player.set_volume(GstAudio.StreamVolumeFormat.LINEAR, rate)

    @log
    def seek(self, seconds):
        """Seek to"""
        self._player.seek_simple(
            Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            seconds * 10**9)
    @log
    def _start_plugin_installation(
            self, missing_plugin_messages, confirm_search):
        install_ctx = GstPbutils.InstallPluginsContext.new()

        install_ctx.set_desktop_id('org.gnome.Music.desktop')
        install_ctx.set_confirm_search(confirm_search)

        startup_id = '_TIME%u' % Gtk.get_current_event_time()
        install_ctx.set_startup_notification_id(startup_id)

        installer_details = []
        for message in missing_plugin_messages:
            installer_detail = GstPbutils.missing_plugin_message_get_installer_detail(message)
            installer_details.append(installer_detail)

        def on_install_done(res):
            # We get the callback too soon, before the installation has
            # actually finished. Do nothing for now.
            pass

        GstPbutils.install_plugins_async(
            installer_details, install_ctx, on_install_done)

    @log
    def _show_codec_confirmation_dialog(
            self, install_helper_name, missing_plugin_messages):
        dialog = MissingCodecsDialog(self._parent_window, install_helper_name)

        def on_dialog_response(dialog, response_type):
            if response_type == Gtk.ResponseType.ACCEPT:
                self._start_plugin_installation(missing_plugin_messages, False)

            dialog.destroy()

        descriptions = []
        for message in missing_plugin_messages:
            description = GstPbutils.missing_plugin_message_get_description(message)
            descriptions.append(description)

        dialog.set_codec_names(descriptions)
        dialog.connect('response', on_dialog_response)
        dialog.present()

    @log
    def _handle_missing_plugins(self):
        if not self._missingPluginMessages:
            return

        missing_plugin_messages = self._missingPluginMessages
        self._missingPluginMessages = []

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

    @log
    def _is_missing_plugin_message(self, message):
        error, debug = message.parse_error()

        if error.matches(Gst.CoreError.quark(), Gst.CoreError.MISSING_PLUGIN):
            return True

        return False


class MissingCodecsDialog(Gtk.MessageDialog):

    def __repr__(self):
        return '<MissingCodecsDialog>'

    @log
    def __init__(self, parent_window, install_helper_name):
        super().__init__(
            transient_for=parent_window, modal=True, destroy_with_parent=True,
            message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CANCEL,
            text=_("Unable to play the file"))

        # TRANSLATORS: this is a button to launch a codec installer.
        # %s will be replaced with the software installer's name, e.g.
        # 'Software' in case of gnome-software.
        self.find_button = self.add_button(_("_Find in %s") % install_helper_name,
                                           Gtk.ResponseType.ACCEPT)
        self.set_default_response(Gtk.ResponseType.ACCEPT)
        Gtk.StyleContext.add_class(self.find_button.get_style_context(), 'suggested-action')

    @log
    def set_codec_names(self, codec_names):
        n_codecs = len(codec_names)
        if n_codecs == 2:
            # TRANSLATORS: separator for a list of codecs
            text = _(" and ").join(codec_names)
        else:
            # TRANSLATORS: separator for a list of codecs
            text = _(", ").join(codec_names)
        self.format_secondary_text(ngettext("%s is required to play the file, but is not installed.",
                                            "%s are required to play the file, but are not installed.",
                                            n_codecs) % text)