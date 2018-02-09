# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
# Copyright (c) 2013 Eslam Mostafa <cseslam@gmail.com>
# Copyright (c) 2013 Sai Suman Prayaga <suman.sai14@gmail.com>
# Copyright (c) 2013 Shivani Poddar <shivani.poddar92@gmail.com>
# Copyright (c) 2013 Guillaume Quintard <guillaume.quintard@gmail.com>
# Copyright (c) 2014 Cedric Bellegarde <gnumdk@gmail.com>
# Copyright (C) 2010 Jonathan Matthew (replay gain code)
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

from collections import deque
import logging
from random import randint
import time

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstAudio', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gtk, GLib, Gio, GObject, Gst, GstAudio, GstPbutils
from gettext import gettext as _, ngettext

from gnomemusic import log
from gnomemusic.albumartcache import Art
from gnomemusic.gstplayer import GstPlayer, Playback
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists
from gnomemusic.scrobbler import LastFmScrobbler
from gnomemusic.widgets.coverstack import CoverStack
import gnomemusic.utils as utils


logger = logging.getLogger(__name__)
playlists = Playlists.get_default()


class RepeatType:
    NONE = 0
    SONG = 1
    ALL = 2
    SHUFFLE = 3


class DiscoveryStatus:
    PENDING = 0
    FAILED = 1
    SUCCEEDED = 2


class Player(GObject.GObject):
    nextTrack = None
    timeout = None
    _seconds_timeout = None
    shuffleHistory = deque(maxlen=10)

    __gsignals__ = {
        'playlist-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'playlist-item-changed': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.TreeModel, Gtk.TreeIter)),
        'current-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'playback-status-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'repeat-mode-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'volume-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'prev-next-invalidated': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'seeked': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'thumbnail-updated': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __repr__(self):
        return '<Player>'

    @log
    def __init__(self, parent_window):
        super().__init__()

        self._parent_window = parent_window
        self.playlist = None
        self.playlistType = None
        self.playlistId = None
        self.playlistField = None
        self.currentTrack = None
        self.currentTrackUri = None

        self._missingPluginMessages = []

        Gst.init(None)
        GstPbutils.pb_utils_init()

        self.discoverer = GstPbutils.Discoverer()
        self.discoverer.connect('discovered', self._on_discovered)
        self.discoverer.start()
        self._discovering_urls = {}

        self._settings = Gio.Settings.new('org.gnome.Music')
        self._settings.connect('changed::repeat', self._on_repeat_setting_changed)
        self.repeat = self._settings.get_enum('repeat')
        self._setup_view()

        self.playlist_insert_handler = 0
        self.playlist_delete_handler = 0

        self._player = GstPlayer()
        self._player.connect('eos', self._on_eos)
        self._player.connect('notify::state', self._on_state_change)

        self._lastfm = LastFmScrobbler()

    def discover_item(self, item, callback, data=None):
        url = item.get_url()
        if not url:
            logger.warn("The item %s doesn't have a URL set", item)
            return

        if not url.startswith("file://"):
            logger.debug("Skipping discovery of %s as not a local file", url)
            return

        obj = (callback, data)

        if url in self._discovering_urls:
            self._discovering_urls[url] += [obj]
        else:
            self._discovering_urls[url] = [obj]
            self.discoverer.discover_uri_async(url)

    def _on_discovered(self, discoverer, info, error):
        try:
            cbs = self._discovering_urls[info.get_uri()]
            del(self._discovering_urls[info.get_uri()])

            for callback, data in cbs:
                if data is not None:
                    callback(info, error, data)
                else:
                    callback(info, error)
        except KeyError:
            # Not something we're interested in
            return

    @log
    def _on_repeat_setting_changed(self, settings, value):
        self.repeat = settings.get_enum('repeat')
        self._sync_prev_next()
        self._sync_repeat_image()
        self._validate_next_track()

    @log
    def _on_glib_idle(self):
        self.currentTrack = self.nextTrack
        if self.currentTrack and self.currentTrack.valid():
            self.currentTrackUri = self.playlist.get_value(
                self.playlist.get_iter(self.currentTrack.get_path()), 5).get_url()
        self.play()

    @log
    def _on_playlist_size_changed(self, path, _iter=None, data=None):
        self._sync_prev_next()

    @log
    def _get_random_iter(self, currentTrack):
        first_iter = self.playlist.get_iter_first()
        if not currentTrack:
            currentTrack = first_iter
        if not currentTrack:
            return None
        if hasattr(self.playlist, "iter_is_valid") and\
           not self.playlist.iter_is_valid(currentTrack):
            return None
        currentPath = int(self.playlist.get_path(currentTrack).to_string())
        rows = self.playlist.iter_n_children(None)
        if rows == 1:
            return currentTrack
        rand = currentPath
        while rand == currentPath:
            rand = randint(0, rows - 1)
        return self.playlist.get_iter_from_string(str(rand))

    @log
    def _get_next_track(self):
        if self.currentTrack and self.currentTrack.valid():
            currentTrack = self.playlist.get_iter(self.currentTrack.get_path())
        else:
            currentTrack = None

        nextTrack = None

        if self.repeat == RepeatType.SONG:
            if currentTrack:
                nextTrack = currentTrack
            else:
                nextTrack = self.playlist.get_iter_first()
        elif self.repeat == RepeatType.ALL:
            if currentTrack:
                nextTrack = self.playlist.iter_next(currentTrack)
            if not nextTrack:
                nextTrack = self.playlist.get_iter_first()
        elif self.repeat == RepeatType.NONE:
            if currentTrack:
                nextTrack = self.playlist.iter_next(currentTrack)
        elif self.repeat == RepeatType.SHUFFLE:
            nextTrack = self._get_random_iter(currentTrack)
            if currentTrack:
                self.shuffleHistory.append(currentTrack)

        if nextTrack:
            return Gtk.TreeRowReference.new(self.playlist, self.playlist.get_path(nextTrack))
        else:
            return None

    @log
    def _get_iter_last(self):
        iter = self.playlist.get_iter_first()
        last = None

        while iter is not None:
            last = iter
            iter = self.playlist.iter_next(iter)

        return last

    @log
    def _get_previous_track(self):
        if self.currentTrack and self.currentTrack.valid():
            currentTrack = self.playlist.get_iter(self.currentTrack.get_path())
        else:
            currentTrack = None

        previousTrack = None

        if self.repeat == RepeatType.SONG:
            if currentTrack:
                previousTrack = currentTrack
            else:
                previousTrack = self.playlist.get_iter_first()
        elif self.repeat == RepeatType.ALL:
            if currentTrack:
                previousTrack = self.playlist.iter_previous(currentTrack)
            if not previousTrack:
                previousTrack = self._get_iter_last()
        elif self.repeat == RepeatType.NONE:
            if currentTrack:
                previousTrack = self.playlist.iter_previous(currentTrack)
        elif self.repeat == RepeatType.SHUFFLE:
            if currentTrack:
                if self.played_seconds < 10 and len(self.shuffleHistory) > 0:
                    previousTrack = self.shuffleHistory.pop()

                    # Discard the current song, which is already queued
                    if self.playlist.get_path(previousTrack) == self.playlist.get_path(currentTrack):
                        previousTrack = None

                if previousTrack is None and len(self.shuffleHistory) > 0:
                    previousTrack = self.shuffleHistory.pop()
                else:
                    previousTrack = self._get_random_iter(currentTrack)

        if previousTrack:
            return Gtk.TreeRowReference.new(self.playlist, self.playlist.get_path(previousTrack))
        else:
            return None

    @log
    def has_next(self):
        if not self.playlist or self.playlist.iter_n_children(None) < 1:
            return False
        elif not self.currentTrack:
            return False
        elif self.repeat in [RepeatType.ALL, RepeatType.SONG, RepeatType.SHUFFLE]:
            return True
        elif self.currentTrack.valid():
            tmp = self.playlist.get_iter(self.currentTrack.get_path())
            return self.playlist.iter_next(tmp) is not None
        else:
            return True

    @log
    def has_previous(self):
        if not self.playlist or self.playlist.iter_n_children(None) < 1:
            return False
        elif not self.currentTrack:
            return False
        elif self.repeat in [RepeatType.ALL, RepeatType.SONG, RepeatType.SHUFFLE]:
            return True
        elif self.currentTrack.valid():
            tmp = self.playlist.get_iter(self.currentTrack.get_path())
            return self.playlist.iter_previous(tmp) is not None
        else:
            return True

    @property
    def playing(self):
        return self._player.is_playing()

    @log
    def _on_state_change(self, klass, arguments):
        self._sync_playing()

    @log
    def _sync_playing(self):
        if self._player.is_playing():
            image = self._pauseImage
            tooltip = _("Pause")
        else:
            image = self._playImage
            tooltip = _("Play")

        if self.playBtn.get_image() != image:
            self.playBtn.set_image(image)

        self.playBtn.set_tooltip_text(tooltip)

    @log
    def _sync_prev_next(self):
        hasNext = self.has_next()
        hasPrevious = self.has_previous()

        self.nextBtn.set_sensitive(hasNext)
        self.prevBtn.set_sensitive(hasPrevious)

        self.emit('prev-next-invalidated')

    @log
    def set_playing(self, value):
        self.actionbar.show()

        if value:
            self.play()
        else:
            self.pause()

        media = self.get_current_media()
        self.playBtn.set_image(self._pauseImage)
        return media

    @log
    def load(self, media):
        self._progress_scale_zero()
        self._set_duration(media.get_duration())
        self.songTotalTimeLabel.set_label(
            utils.seconds_to_string(media.get_duration()))
        self.progressScale.set_sensitive(True)

        self.playBtn.set_sensitive(True)
        self._sync_prev_next()

        artist = utils.get_artist_name(media)
        self.artistLabel.set_label(artist)

        self._cover_stack.update(media)

        title = utils.get_media_title(media)
        self.titleLabel.set_label(title)

        self._time_stamp = int(time.time())

        url_ = media.get_url()
        if url_ != self._player.url:
            self._player.url = url_

        if self.currentTrack and self.currentTrack.valid():
            currentTrack = self.playlist.get_iter(self.currentTrack.get_path())
            self.emit('playlist-item-changed', self.playlist, currentTrack)
            self.emit('current-changed')

        self._validate_next_track()

    def _on_next_item_validated(self, info, error, _iter):
        if error:
            print("Info %s: error: %s" % (info, error))
            self.playlist.set_value(_iter, self.discovery_status_field, DiscoveryStatus.FAILED)
            nextTrack = self.playlist.iter_next(_iter)

            if nextTrack:
                self._validate_next_track(Gtk.TreeRowReference.new(self.playlist, self.playlist.get_path(nextTrack)))

    @log
    def _validate_next_track(self, track=None):
        if track is None:
            track = self._get_next_track()

        self.nextTrack = track

        if track is None:
            return

        iter_ = self.playlist.get_iter(self.nextTrack.get_path())
        status = self.playlist.get_value(iter_, self.discovery_status_field)
        nextSong = self.playlist.get_value(iter_, self.playlistField)
        url_ = self.playlist[iter_][5].get_url()

        # Skip remote songs discovery
        if (url_.startswith('http://')
                or url_.startswith('https://')):
            return False
        elif status == DiscoveryStatus.PENDING:
            self.discover_item(nextSong, self._on_next_item_validated, iter_)
        elif status == DiscoveryStatus.FAILED:
            GLib.idle_add(self._validate_next_track)

        return False

    @log
    def _on_cover_stack_updated(self, klass):
        self.emit('thumbnail-updated')

    @log
    def _on_eos(self, klass):
        if self.nextTrack:
            GLib.idle_add(self._on_glib_idle)
        elif (self.repeat == RepeatType.NONE):
            self.stop()
            self.playBtn.set_image(self._playImage)
            self._progress_scale_zero()
            self.progressScale.set_sensitive(False)
            if self.playlist is not None:
                currentTrack = self.playlist.get_path(self.playlist.get_iter_first())
                if currentTrack:
                    self.currentTrack = Gtk.TreeRowReference.new(self.playlist, currentTrack)
                    self.currentTrackUri = self.playlist.get_value(
                        self.playlist.get_iter(self.currentTrack.get_path()), 5).get_url()
                else:
                    self.currentTrack = None
                self.load(self.get_current_media())
            self.emit('playback-status-changed')
        else:
            # Stop playback
            self.stop()
            self.playBtn.set_image(self._playImage)
            self._progress_scale_zero()
            self.progressScale.set_sensitive(False)
            self.emit('playback-status-changed')


    @log
    def play(self):
        if self.playlist is None:
            return

        media = None

        if self._player.state != Playback.PAUSED:
            self.stop()

            media = self.get_current_media()
            if not media:
                return

            self.load(media)

        self._player.state = Playback.PLAYING

        self._update_position_callback()
        if media:
            self._lastfm.now_playing(media)
        if not self.timeout and self.progressScale.get_realized():
            self._update_timeout()

        self.emit('playback-status-changed')

    @log
    def pause(self):
        self._remove_timeout()

        self._player.state = Playback.PAUSED
        self.emit('playback-status-changed')

    @log
    def stop(self):
        self._remove_timeout()

        self._player.state = Playback.STOPPED
        self.emit('playback-status-changed')

    @log
    def play_next(self):
        if self.playlist is None:
            return True

        if not self.nextBtn.get_sensitive():
            return True

        self.stop()
        self.currentTrack = self.nextTrack

        if self.currentTrack and self.currentTrack.valid():
            self.currentTrackUri = self.playlist.get_value(
                self.playlist.get_iter(self.currentTrack.get_path()), 5).get_url()
            self.play()

    @log
    def play_previous(self):
        if self.playlist is None:
            return

        if self.prevBtn.get_sensitive() is False:
            return

        position = self._player.position
        if position >= 5:
            self._progress_scale_zero()
            self.on_progress_scale_change_value(self.progressScale)
            return

        self.stop()

        self.currentTrack = self._get_previous_track()
        if self.currentTrack and self.currentTrack.valid():
            self.currentTrackUri = self.playlist.get_value(
                self.playlist.get_iter(self.currentTrack.get_path()), 5).get_url()
            self.play()

    @log
    def play_pause(self):
        if self._player.state == Playback.PLAYING:
            self.set_playing(False)
        else:
            self.set_playing(True)

    # FIXME: set the discovery field to 11 to be safe, but for some
    # models it is 12.
    @log
    def set_playlist(self, type, id, model, iter, field,
                     discovery_status_field=11):
        old_playlist = self.playlist
        if old_playlist != model:
            self.playlist = model
            if self.playlist_insert_handler:
                old_playlist.disconnect(self.playlist_insert_handler)
            if self.playlist_delete_handler:
                old_playlist.disconnect(self.playlist_delete_handler)

        self.playlistType = type
        self.playlistId = id
        self.currentTrack = Gtk.TreeRowReference.new(model, model.get_path(iter))
        if self.currentTrack and self.currentTrack.valid():
            self.currentTrackUri = self.playlist.get_value(
                self.playlist.get_iter(self.currentTrack.get_path()), 5).get_url()
        self.playlistField = field
        self.discovery_status_field = discovery_status_field

        if old_playlist != model:
            self.playlist_insert_handler = model.connect('row-inserted', self._on_playlist_size_changed)
            self.playlist_delete_handler = model.connect('row-deleted', self._on_playlist_size_changed)
            self.emit('playlist-changed')
        self.emit('current-changed')

        GLib.idle_add(self._validate_next_track)

    @log
    def running_playlist(self, type, id):
        if type == self.playlistType and id == self.playlistId:
            return self.playlist
        else:
            return None

    @log
    def _setup_view(self):
        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Music/PlayerToolbar.ui')
        self.actionbar = self._ui.get_object('actionbar')
        self.prevBtn = self._ui.get_object('previous_button')
        self.playBtn = self._ui.get_object('play_button')
        self.nextBtn = self._ui.get_object('next_button')
        self._playImage = self._ui.get_object('play_image')
        self._pauseImage = self._ui.get_object('pause_image')
        self.progressScale = self._ui.get_object('progress_scale')
        self.songPlaybackTimeLabel = self._ui.get_object('playback')
        self.songTotalTimeLabel = self._ui.get_object('duration')
        self.titleLabel = self._ui.get_object('title')
        self.artistLabel = self._ui.get_object('artist')

        stack = self._ui.get_object('cover')
        self._cover_stack = CoverStack(stack, Art.Size.XSMALL)
        self._cover_stack.connect('updated', self._on_cover_stack_updated)

        self.duration = self._ui.get_object('duration')
        self.repeatBtnImage = self._ui.get_object('playlistRepeat')

        self._sync_repeat_image()

        self.prevBtn.connect('clicked', self._on_prev_btn_clicked)
        self.playBtn.connect('clicked', self._on_play_btn_clicked)
        self.nextBtn.connect('clicked', self._on_next_btn_clicked)
        self.progressScale.connect('button-press-event', self._on_progress_scale_event)
        self.progressScale.connect('value-changed', self._on_progress_value_changed)
        self.progressScale.connect('button-release-event', self._on_progress_scale_button_released)
        self.progressScale.connect('change-value', self._on_progress_scale_seek)
        self._ps_draw = self.progressScale.connect('draw',
            self._on_progress_scale_draw)
        self._seek_timeout = None
        self._old_progress_scale_value = 0.0
        self.progressScale.set_increments(300, 600)

    def _on_progress_scale_seek_finish(self, value):
        """Prevent stutters when seeking with infinitesimal amounts"""
        self._seek_timeout = None
        round_digits = self.progressScale.get_property('round-digits')
        if self._old_progress_scale_value != round(value, round_digits):
            self.on_progress_scale_change_value(self.progressScale)
            self._old_progress_scale_value = round(value, round_digits)
        return False

    def _on_progress_scale_seek(self, scale, scroll_type, value):
        """Smooths out the seeking process

        Called every time progress scale is moved. Only after a seek has been
        stable for 100ms, we play the song from its location.
        """
        if self._seek_timeout:
            GLib.source_remove(self._seek_timeout)

        Gtk.Range.do_change_value(scale, scroll_type, value)
        if scroll_type == Gtk.ScrollType.JUMP:
            self._seek_timeout = GLib.timeout_add(
                100, self._on_progress_scale_seek_finish, value)
        else:
            # scroll with keys, hence no smoothing
            self._on_progress_scale_seek_finish(value)
            self._update_position_callback()

        return True

    @log
    def _on_progress_scale_button_released(self, scale, data):
        if self._seek_timeout:
            GLib.source_remove(self._seek_timeout)
            self._on_progress_scale_seek_finish(self.progressScale.get_value())

        self._update_position_callback()
        return False

    def _on_progress_value_changed(self, widget):
        seconds = int(self.progressScale.get_value() / 60)
        self.songPlaybackTimeLabel.set_label(utils.seconds_to_string(seconds))
        return False

    @log
    def _on_progress_scale_event(self, scale, data):
        self._remove_timeout()
        self._old_progress_scale_value = self.progressScale.get_value()
        return False

    def _on_progress_scale_draw(self, cr, data):
        self._update_timeout()
        self.progressScale.disconnect(self._ps_draw)
        return False

    def _update_timeout(self):
        """Update the duration for self.timeout and self._seconds_timeout

        Sets the period of self.timeout to a value small enough to make the
        slider of self.progressScale move smoothly based on the current song
        duration and progressScale length.  self._seconds_timeout is always set
        to a fixed value, short enough to hide irregularities in GLib event
        timing from the user, for updating the songPlaybackTimeLabel.
        """
        # Don't run until progressScale has been realized
        if self.progressScale.get_realized() is False:
            return

        # Update self.timeout
        width = self.progressScale.get_allocated_width()
        padding = self.progressScale.get_style_context().get_padding(
            Gtk.StateFlags.NORMAL)
        width -= padding.left + padding.right

        duration = self._player.duration
        timeout_period = min(1000 * duration // width, 1000)

        if self.timeout:
            GLib.source_remove(self.timeout)
        self.timeout = GLib.timeout_add(
            timeout_period, self._update_position_callback)

        # Update self._seconds_timeout
        if not self._seconds_timeout:
            self.seconds_period = 1000
            self._seconds_timeout = GLib.timeout_add(
                self.seconds_period, self._update_seconds_callback)

    def _remove_timeout(self):
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None
        if self._seconds_timeout:
            GLib.source_remove(self._seconds_timeout)
            self._seconds_timeout = None

    def _progress_scale_zero(self):
        self.progressScale.set_value(0)
        self._on_progress_value_changed(None)

    @log
    def _on_play_btn_clicked(self, btn):
        if self._player.is_playing():
            self.pause()
        else:
            self.play()

    @log
    def _on_next_btn_clicked(self, btn):
        self.play_next()

    @log
    def _on_prev_btn_clicked(self, btn):
        self.play_previous()

    @log
    def _set_duration(self, duration):
        self.duration = duration
        self.played_seconds = 0
        self.progressScale.set_range(0.0, duration * 60)

    @log
    def _update_position_callback(self):
        position = self._player.position
        if position > 0:
            self.progressScale.set_value(position * 60)
        self._update_timeout()
        return False

    @log
    def _update_seconds_callback(self):
        self._on_progress_value_changed(None)

        position = self._player.position
        if position > 0:
            self.played_seconds += self.seconds_period / 1000
            try:
                percentage = self.played_seconds / self.duration
                if (not self._lastfm.scrobbled
                        and percentage > 0.4):
                    current_media = self.get_current_media()
                    if current_media:
                        # FIXME: we should not need to update static
                        # playlists here but removing it may introduce
                        # a bug. So, we keep it for the time being.
                        playlists.update_all_static_playlists()
                        grilo.bump_play_count(current_media)
                        grilo.set_last_played(current_media)
                        self._lastfm.scrobble(current_media, self._time_stamp)

            except Exception as e:
                logger.warn("Error: %s, %s", e.__class__, e)
        return True

    @log
    def _sync_repeat_image(self):
        icon = None
        if self.repeat == RepeatType.NONE:
            icon = 'media-playlist-consecutive-symbolic'
        elif self.repeat == RepeatType.SHUFFLE:
            icon = 'media-playlist-shuffle-symbolic'
        elif self.repeat == RepeatType.ALL:
            icon = 'media-playlist-repeat-symbolic'
        elif self.repeat == RepeatType.SONG:
            icon = 'media-playlist-repeat-song-symbolic'

        self.repeatBtnImage.set_from_icon_name(icon, Gtk.IconSize.MENU)
        self.emit('repeat-mode-changed')

    @log
    def on_progress_scale_change_value(self, scroll):
        seconds = scroll.get_value() / 60
        if True: # seconds != self.duration:
            self._player.seek(seconds)
            try:
                # FIXME mpris
                self.emit('seeked', seconds * 1000000)
            except TypeError:
                # See https://bugzilla.gnome.org/show_bug.cgi?id=733095
                pass
        else:
            print("WEIRD SCROLL VALUE?", seconds)
            duration = self._player.duration
            if duration:
                # Rewind a second back before the track end
                self._player.seek(duration - 1)
                try:
                    # FIXME mpris
                    self.emit('seeked', (duration - 1) / 1000)
                except TypeError:
                    # See https://bugzilla.gnome.org/show_bug.cgi?id=733095
                    pass

        return True

    # MPRIS

    @log
    def Stop(self):
        self._progress_scale_zero()
        self.progressScale.set_sensitive(False)
        self.playBtn.set_image(self._playImage)
        self.stop()
        self.emit('playback-status-changed')

    @log
    def get_playback_status(self):
        # FIXME: Just a proxy right now.
        return self._player.state

    @log
    def get_repeat_mode(self):
        return self.repeat

    @log
    def set_repeat_mode(self, mode):
        self.repeat = mode
        self._sync_repeat_image()

    # TODO: used by MPRIS
    @log
    def set_position(self, offset, start_if_ne=False, next_on_overflow=False):
        if offset < 0:
            if start_if_ne:
                offset = 0
            else:
                return

        duration = self._player._player.query_duration(Gst.Format.TIME)
        if duration is None:
            return

        if duration[1] >= offset * 1000:
            self._player._player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, offset * 1000)
            self.emit('seeked', offset)
        elif next_on_overflow:
            self.play_next()

    @log
    def get_volume(self):
        return self._player._player.get_volume(GstAudio.StreamVolumeFormat.LINEAR)

    @log
    def set_volume(self, rate):
        self._player._player.set_volume(GstAudio.StreamVolumeFormat.LINEAR, rate)
        self.emit('volume-changed')

    @log
    def get_current_media(self):
        if not self.currentTrack or not self.currentTrack.valid():
            return None
        currentTrack = self.playlist.get_iter(self.currentTrack.get_path())
        if self.playlist.get_value(currentTrack, self.discovery_status_field) == DiscoveryStatus.FAILED:
            return None
        return self.playlist.get_value(currentTrack, self.playlistField)


class SelectionToolbar():

    def __repr__(self):
        return '<SelectionToolbar>'

    @log
    def __init__(self):
        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Music/SelectionToolbar.ui')
        self.actionbar = self._ui.get_object('actionbar')
        self._add_to_playlist_button = self._ui.get_object('button1')
        self.actionbar.set_visible(False)
