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
from random import randint
import logging
import time

from gettext import gettext as _
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstAudio', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gtk, GLib, Gio, GObject, Gst, GstPbutils

from gnomemusic import log
from gnomemusic.albumartcache import Art
from gnomemusic.gstplayer import GstPlayer, Playback
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists
from gnomemusic.scrobbler import LastFmScrobbler
from gnomemusic.widgets.coverstack import CoverStack
from gnomemusic.widgets.smoothscale import SmoothScale
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

    __gsignals__ = {
        'playlist-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'playlist-item-changed': (
            GObject.SignalFlags.RUN_FIRST, None, (Gtk.TreeModel, Gtk.TreeIter)
        ),
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
        self.playlist_type = None
        self.playlist_id = None
        self.playlist_field = None
        self.current_track = None
        self.current_track_uri = None
        self._next_track = None
        self._shuffle_history = deque(maxlen=10)
        self._new_clock = True

        Gst.init(None)
        GstPbutils.pb_utils_init()

        self._discoverer = GstPbutils.Discoverer()
        self._discoverer.connect('discovered', self._on_discovered)
        self._discoverer.start()
        self._discovering_urls = {}

        self._settings = Gio.Settings.new('org.gnome.Music')
        self._settings.connect(
            'changed::repeat', self._on_repeat_setting_changed)
        self.repeat = self._settings.get_enum('repeat')

        self.playlist_insert_handler = 0
        self.playlist_delete_handler = 0

        self._player = GstPlayer()
        self._player.connect('clock-tick', self._on_clock_tick)
        self._player.connect('eos', self._on_eos)
        self._player.connect('notify::state', self._on_state_change)

        self._setup_view()
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
            self._discoverer.discover_uri_async(url)

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
        self.current_track = self._next_track
        if (self.current_track
                and self.current_track.valid()):
            iter_ = self.playlist.get_iter(self.current_track.get_path())
            self.current_track_uri = self.playlist[iter_][5].get_url()
        self.play()

    @log
    def _on_playlist_size_changed(self, path, _iter=None, data=None):
        self._sync_prev_next()

    @log
    def _get_random_iter(self, current_track):
        first_iter = self.playlist.get_iter_first()
        if not current_track:
            current_track = first_iter
        if not current_track:
            return None
        if (hasattr(self.playlist, "iter_is_valid")
                and not self.playlist.iter_is_valid(current_track)):
            return None
        current_path = int(self.playlist.get_path(current_track).to_string())
        rows = self.playlist.iter_n_children(None)
        if rows == 1:
            return current_track
        rand = current_path
        while rand == current_path:
            rand = randint(0, rows - 1)
        return self.playlist.get_iter_from_string(str(rand))

    @log
    def _get_next_track(self):
        if (self.current_track
                and self.current_track.valid()):
            iter_ = self.playlist.get_iter(self.current_track.get_path())
        else:
            iter_ = None

        next_track = None

        if self.repeat == RepeatType.SONG:
            if iter_:
                next_track = iter_
            else:
                next_track = self.playlist.get_iter_first()
        elif self.repeat == RepeatType.ALL:
            if iter_:
                next_track = self.playlist.iter_next(iter_)
            if not next_track:
                next_track = self.playlist.get_iter_first()
        elif self.repeat == RepeatType.NONE:
            if iter_:
                next_track = self.playlist.iter_next(iter_)
        elif self.repeat == RepeatType.SHUFFLE:
            next_track = self._get_random_iter(iter_)
            if iter_:
                self._shuffle_history.append(iter_)

        if next_track:
            return Gtk.TreeRowReference.new(
                self.playlist, self.playlist.get_path(next_track))
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
        if (self.current_track
                and self.current_track.valid()):
            iter_ = self.playlist.get_iter(self.current_track.get_path())
        else:
            iter_ = None

        previous_track = None

        if self.repeat == RepeatType.SONG:
            if iter_:
                previous_track = iter_
            else:
                previous_track = self.playlist.get_iter_first()
        elif self.repeat == RepeatType.ALL:
            if iter_:
                previous_track = self.playlist.iter_previous(iter_)
            if not previous_track:
                previous_track = self._get_iter_last()
        elif self.repeat == RepeatType.NONE:
            if iter_:
                previous_track = self.playlist.iter_previous(iter_)
        elif self.repeat == RepeatType.SHUFFLE:
            if iter_:
                if (self._player.position < 5
                        and len(self._shuffle_history) > 0):
                    previous_track = self._shuffle_history.pop()

                    # Discard the current song, which is already queued
                    prev_path = self.playlist.get_path(previous_track)
                    current_path = self.playlist.get_path(iter_)
                    if prev_path == current_path:
                        previous_track = None

                if (previous_track is None
                        and len(self._shuffle_history) > 0):
                    previous_track = self._shuffle_history.pop()
                else:
                    previous_track = self._get_random_iter(iter_)

        if previous_track:
            return Gtk.TreeRowReference.new(
                self.playlist, self.playlist.get_path(previous_track))
        else:
            return None

    @log
    def has_next(self):
        repeat_types = [RepeatType.ALL, RepeatType.SONG, RepeatType.SHUFFLE]
        if (not self.playlist
                or self.playlist.iter_n_children(None) < 1):
            return False
        elif not self.current_track:
            return False
        elif self.repeat in repeat_types:
            return True
        elif self.current_track.valid():
            tmp = self.playlist.get_iter(self.current_track.get_path())
            return self.playlist.iter_next(tmp) is not None
        else:
            return True

    @log
    def has_previous(self):
        repeat_types = [RepeatType.ALL, RepeatType.SONG, RepeatType.SHUFFLE]
        if (not self.playlist
                or self.playlist.iter_n_children(None) < 1):
            return False
        elif not self.current_track:
            return False
        elif self.repeat in repeat_types:
            return True
        elif self.current_track.valid():
            tmp = self.playlist.get_iter(self.current_track.get_path())
            return self.playlist.iter_previous(tmp) is not None
        else:
            return True

    @property
    def playing(self):
        return self._player.state == Playback.PLAYING

    @log
    def _on_state_change(self, klass, arguments):
        self._sync_playing()

        return True

    @log
    def _sync_playing(self):
        if self._player.state == Playback.PLAYING:
            image = self._pause_image
            tooltip = _("Pause")
        else:
            image = self._play_image
            tooltip = _("Play")

        if self._play_button.get_image() != image:
            self._play_button.set_image(image)

        self._play_button.set_tooltip_text(tooltip)

    @log
    def _sync_prev_next(self):
        self._next_button.set_sensitive(self.has_next())
        self._prev_button.set_sensitive(self.has_previous())

        self.emit('prev-next-invalidated')

    @log
    def set_playing(self, value):
        self.actionbar.show()

        if value:
            self.play()
        else:
            self.pause()

        media = self.get_current_media()
        self._play_button.set_image(self._pause_image)
        return media

    @log
    def load(self, media):
        self._total_time_label.set_label(
            utils.seconds_to_string(media.get_duration()))

        self._play_button.set_sensitive(True)
        self._sync_prev_next()

        artist = utils.get_artist_name(media)
        self._artist_label.set_label(artist)

        self._cover_stack.update(media)

        title = utils.get_media_title(media)
        self._title_label.set_label(title)

        self._time_stamp = int(time.time())

        url_ = media.get_url()
        if url_ != self._player.url:
            self._player.url = url_

        if self.current_track and self.current_track.valid():
            current_track = self.playlist.get_iter(
                self.current_track.get_path())
            self.emit('playlist-item-changed', self.playlist, current_track)
            self.emit('current-changed')

        self._validate_next_track()

    def _on_next_item_validated(self, info, error, iter_):
        if error:
            print("Info %s: error: %s" % (info, error))
            field = self.discovery_status_field
            self.playlist[iter_][field] = DiscoveryStatus.FAILED
            next_track = self.playlist.iter_next(iter_)

            if next_track:
                next_path = self.playlist.get_path(next_track)
                self._validate_next_track(
                    Gtk.TreeRowReference.new(self.playlist, next_path))

    @log
    def _validate_next_track(self, track=None):
        if track is None:
            track = self._get_next_track()

        self._next_track = track

        if track is None:
            return

        iter_ = self.playlist.get_iter(self._next_track.get_path())
        status = self.playlist[iter_][self.discovery_status_field]
        next_song = self.playlist[iter_][self.playlist_field]
        url_ = self.playlist[iter_][5].get_url()

        # Skip remote songs discovery
        if (url_.startswith('http://')
                or url_.startswith('https://')):
            return False
        elif status == DiscoveryStatus.PENDING:
            self.discover_item(next_song, self._on_next_item_validated, iter_)
        elif status == DiscoveryStatus.FAILED:
            GLib.idle_add(self._validate_next_track)

        return False

    @log
    def _on_cover_stack_updated(self, klass):
        self.emit('thumbnail-updated')

    @log
    def _on_eos(self, klass):
        if self._next_track:
            GLib.idle_add(self._on_glib_idle)
        elif (self.repeat == RepeatType.NONE):
            self.stop()
            self._play_button.set_image(self._play_image)
            if self.playlist is not None:
                current_track = self.playlist.get_path(
                    self.playlist.get_iter_first())
                if current_track:
                    self.current_track = Gtk.TreeRowReference.new(
                        self.playlist, current_track)
                    iter_ = self.playlist.get_iter(
                        self.current_track.get_path())
                    uri = self.playlist[iter_][5].get_url()
                    self.current_track_uri = uri
                else:
                    self.current_track = None
                self.load(self.get_current_media())
            self.emit('playback-status-changed')
        else:
            # Stop playback
            self.stop()
            self._play_button.set_image(self._play_image)
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
        self.emit('playback-status-changed')

    @log
    def pause(self):
        self._player.state = Playback.PAUSED
        self.emit('playback-status-changed')

    @log
    def stop(self):
        self._player.state = Playback.STOPPED
        self.emit('playback-status-changed')

    @log
    def play_next(self):
        if self.playlist is None:
            return True

        if not self._next_button.get_sensitive():
            return True

        self.stop()
        self.current_track = self._next_track

        if self.current_track and self.current_track.valid():
            iter_ = self.playlist.get_iter(self.current_track.get_path())
            self.current_track_uri = self.playlist[iter_][5].get_url()
            self.play()

    @log
    def play_previous(self):
        if self.playlist is None:
            return

        if self._prev_button.get_sensitive() is False:
            return

        position = self._player.position
        if position >= 5:
            self._player.seek(0)
            self._player.state = Playback.PLAYING
            return

        self.stop()

        self.current_track = self._get_previous_track()
        if self.current_track and self.current_track.valid():
            iter_ = self.playlist.get_iter(self.current_track.get_path())
            uri = self.playlist[iter_][5].get_url()
            self.current_track_uri = uri
            self.play()

    @log
    def play_pause(self):
        self._sync_playing()

    # FIXME: set the discovery field to 11 to be safe, but for some
    # models it is 12.
    @log
    def set_playlist(
            self, type, id, model, iter, field, discovery_status_field=11):
        old_playlist = self.playlist
        if old_playlist != model:
            self.playlist = model
            if self.playlist_insert_handler:
                old_playlist.disconnect(self.playlist_insert_handler)
            if self.playlist_delete_handler:
                old_playlist.disconnect(self.playlist_delete_handler)

        self.playlist_type = type
        self.playlist_id = id
        self.current_track = Gtk.TreeRowReference.new(
            model, model.get_path(iter))
        if self.current_track and self.current_track.valid():
            iter_ = self.playlist.get_iter(self.current_track.get_path())
            uri = self.playlist[iter_][5].get_url()
            self.current_track_uri = uri
        self.playlist_field = field
        self.discovery_status_field = discovery_status_field

        if old_playlist != model:
            self.playlist_insert_handler = model.connect(
                'row-inserted', self._on_playlist_size_changed)
            self.playlist_delete_handler = model.connect(
                'row-deleted', self._on_playlist_size_changed)
            self.emit('playlist-changed')
        self.emit('current-changed')

        GLib.idle_add(self._validate_next_track)

    @log
    def running_playlist(self, type, id):
        if type == self.playlist_type and id == self.playlist_id:
            return self.playlist
        else:
            return None

    @log
    def _setup_view(self):
        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Music/PlayerToolbar.ui')
        self.actionbar = self._ui.get_object('actionbar')
        self._prev_button = self._ui.get_object('previous_button')
        self._play_button = self._ui.get_object('play_button')
        self._next_button = self._ui.get_object('next_button')
        self._play_image = self._ui.get_object('play_image')
        self._pause_image = self._ui.get_object('pause_image')

        self._progress_scale = self._ui.get_object('smooth_scale')
        self._progress_scale.player = self._player

        self._progress_scale.connect('seek-finished', self._on_seek_finished)
        self._progress_scale.connect(
            'value-changed', self._on_progress_value_changed)

        self._progress_time_label = self._ui.get_object('playback')
        self._total_time_label = self._ui.get_object('duration')
        self._title_label = self._ui.get_object('title')
        self._artist_label = self._ui.get_object('artist')

        stack = self._ui.get_object('cover')
        self._cover_stack = CoverStack(stack, Art.Size.XSMALL)
        self._cover_stack.connect('updated', self._on_cover_stack_updated)

        self._repeat_button_image = self._ui.get_object('playlistRepeat')

        self._sync_repeat_image()

        self._prev_button.connect('clicked', self._on_prev_button_clicked)
        self._play_button.connect('clicked', self._on_play_button_clicked)
        self._next_button.connect('clicked', self._on_next_button_clicked)

    def _on_progress_value_changed(self, progress_scale):
        seconds = int(progress_scale.get_value() / 60)
        self._progress_time_label.set_label(utils.seconds_to_string(seconds))

    @log
    def _on_seek_finished(self, klass, time):
        self._player.state = Playback.PLAYING

    @log
    def _on_clock_tick(self, klass, tick):
        seconds = int(self._player.position)
        print("TICK", tick, seconds, self._player.position)

        current_media = self.get_current_media()

        if tick == 0:
            self._new_clock = True
            self._lastfm.now_playing(current_media)

        self._progress_time_label.set_label(
            utils.seconds_to_string(seconds))

        duration = self._player.duration
        if duration is None:
            return

        position = self._player.position
        if position > 0:
            percentage = tick / duration
            if (not self._lastfm.scrobbled
                    and duration > 30
                    and (percentage > 0.5 or tick > 4*60)):
                self._lastfm.scrobble(current_media, self._time_stamp)

            if (percentage > 0.5
                    and self._new_clock):
                self._new_clock = False
                # FIXME: we should not need to update static
                # playlists here but removing it may introduce
                # a bug. So, we keep it for the time being.
                playlists.update_all_static_playlists()
                # FIXME: problematic with clock tick
                # grilo.bump_play_count(current_media)
                # grilo.set_last_played(current_media)

    @log
    def _on_play_button_clicked(self, button):
        if self._player.state == Playback.PLAYING:
            self.pause()
        else:
            self.play()

    @log
    def _on_next_button_clicked(self, button):
        self.play_next()

    @log
    def _on_prev_button_clicked(self, button):
        self.play_previous()

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

        self._repeat_button_image.set_from_icon_name(icon, Gtk.IconSize.MENU)
        self.emit('repeat-mode-changed')

    # MPRIS

    @log
    def Stop(self):
        self._play_button.set_image(self._play_image)
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
    def get_position(self):
        return self._player.position

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

        duration = self._player.duration
        if duration is None:
            return

        if duration >= offset * 1000:
            self._player.seek(offset * 1000)
            self.emit('seeked', offset)
        elif next_on_overflow:
            self.play_next()

    @log
    def get_volume(self):
        return self._player.volume

    @log
    def set_volume(self, rate):
        self._player.volume = rate
        self.emit('volume-changed')

    @log
    def get_current_media(self):
        if not self.current_track or not self.current_track.valid():
            return None
        iter_ = self.playlist.get_iter(self.current_track.get_path())
        field = self.discovery_status_field
        if self.playlist[iter_][field] == DiscoveryStatus.FAILED:
            return None
        return self.playlist[iter_][self.playlist_field]


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
