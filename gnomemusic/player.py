# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
# Copyright (c) 2013 Eslam Mostafa <cseslam@gmail.com>
# Copyright (c) 2013 Sai Suman Prayaga <suman.sai14@gmail.com>
# Copyright (c) 2013 Shivani Poddar <shivani.poddar92@gmail.com>
# Copyright (c) 2013 Guillaume Quintard <guillaume.quintard@gmail.com>
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


from gi.repository import GIRepository
GIRepository.Repository.prepend_search_path('libgd')

from gi.repository import Gtk, Gdk, GLib, Gio, GObject, Gst, GstAudio, GstPbutils
from gettext import gettext as _
from random import randint
from queue import LifoQueue
from gnomemusic.albumArtCache import AlbumArtCache
from gnomemusic.query import Query

from gnomemusic import log
import logging
logger = logging.getLogger(__name__)

from gi.repository import Tracker
try:
    tracker = Tracker.SparqlConnection.get(None)
except Exception as e:
    from sys import exit
    logger.error("Cannot connect to tracker, error '%s'\Exiting" % str(e))
    exit(1)

ART_SIZE = 34


class RepeatType:
    NONE = 0
    SONG = 1
    ALL = 2
    SHUFFLE = 3


class PlaybackStatus:
    PLAYING = 0
    PAUSED = 1
    STOPPED = 2


class Player(GObject.GObject):
    nextTrack = None
    timeout = None
    shuffleHistory = LifoQueue(maxsize=10)

    __gsignals__ = {
        'playing-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'playlist-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'playlist-item-changed': (GObject.SIGNAL_RUN_FIRST, None, (Gtk.TreeModel, Gtk.TreeIter)),
        'current-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'playback-status-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'repeat-mode-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'volume-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'prev-next-invalidated': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'seeked': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
        'thumbnail-updated': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
    }

    @log
    def __init__(self):
        GObject.GObject.__init__(self)
        self.playlist = None
        self.playlistType = None
        self.playlistId = None
        self.playlistField = None
        self.currentTrack = None
        self._lastState = Gst.State.PAUSED
        self.cache = AlbumArtCache.get_default()
        self._symbolicIcon = self.cache.get_default_icon(ART_SIZE, ART_SIZE)

        Gst.init(None)

        self.discoverer = GstPbutils.Discoverer()
        self.discoverer.connect('discovered', self._on_discovered)
        self.discoverer.start()
        self._discovering_urls = {}

        self.player = Gst.ElementFactory.make('playbin', 'player')
        self.bus = self.player.get_bus()
        self.bus.add_signal_watch()

        self._settings = Gio.Settings.new('org.gnome.Music')
        self._settings.connect('changed::repeat', self._on_settings_changed)
        self.repeat = self._settings.get_enum('repeat')

        self.bus.connect('message::state-changed', self._on_bus_state_changed)
        self.bus.connect('message::error', self._onBusError)
        self.bus.connect('message::eos', self._on_bus_eos)
        self._setup_view()

        self.playlist_insert_handler = 0
        self.playlist_delete_handler = 0

    def discover_item(self, item, callback, data=None):
        url = item.get_url()
        if not url:
            logger.warn("The item %s doesn't have a URL set" % item)
            return

        if not url.startswith("file://"):
            logger.debug("Skipping discovery of %s as a remote url" % url)
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
    def _on_settings_changed(self, settings, value):
        self.repeat = settings.get_enum('repeat')
        self._sync_prev_next()
        self._sync_repeat_image()

    @log
    def _on_bus_state_changed(self, bus, message):
        # Note: not all state changes are signaled through here, in particular
        # transitions between Gst.State.READY and Gst.State.NULL are never async
        # and thus don't cause a message
        # In practice, self means only Gst.State.PLAYING and Gst.State.PAUSED are
        self._sync_playing()

    @log
    def _onBusError(self, bus, message):
        media = self.get_current_media()
        if media is not None:
            uri = media.get_url()
        else:
            uri = 'none'
        logger.warn('URI: ' + uri)
        error, debug = message.parse_error()
        debug = debug.split('\n')
        debug = [('     ') + line.lstrip() for line in debug]
        debug = '\n'.join(debug)
        logger.warn('Error from element ' + message.src.get_name() + ': ' + error.message)
        logger.warn('Debugging info:\n' + debug)
        self.play_next()
        return True

    @log
    def _on_bus_eos(self, bus, message):

        # update playcount
        cur_song_title = self.get_current_media().get_title() # for testing
        cur_song_id = self.get_current_media().get_id()
        print("Updating play count on %s (tracker id %s)" % (cur_song_title, cur_song_id)) # for testing
        query = Query.update_playcount(cur_song_id)
        tracker.update(query, GLib.PRIORITY_DEFAULT, None) # TODO: async? callback funct.?

        self.nextTrack = self._get_next_track()

        if self.nextTrack:
            GLib.idle_add(self._on_glib_idle)
        elif (self.repeat == RepeatType.NONE):
            self.stop()
            self.playBtn.set_image(self._playImage)
            self.progressScale.set_value(0)
            self.progressScale.set_sensitive(False)
            if self.playlist is not None:
                currentTrack = self.playlist.get_path(self.playlist.get_iter_first())
                if currentTrack:
                    self.currentTrack = Gtk.TreeRowReference.new(self.playlist, currentTrack)
                else:
                    self.currentTrack = None
                self.load(self.get_current_media())
        else:
            # Stop playback
            self.stop()
            self.playBtn.set_image(self._playImage)
            self.progressScale.set_value(0)
            self.progressScale.set_sensitive(False)
            self.emit('playback-status-changed')

    @log
    def _on_glib_idle(self):
        self.currentTrack = self.nextTrack
        self.play()

    @log
    def _on_playlist_size_changed(self, path, _iter=None, data=None):
        self._sync_prev_next()

    @log
    def _get_random_iter(self, currentTrack):
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
            if currentTrack:
                nextTrack = self._get_random_iter(currentTrack)
                if self.shuffleHistory.full():
                    self.shuffleHistory.get_nowait()
                self.shuffleHistory.put_nowait(currentTrack)

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
                if not self.shuffleHistory.empty():
                    previousTrack = self.shuffleHistory.get_nowait()
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

    @log
    def _get_playing(self):
        ok, state, pending = self.player.get_state(0)
        # log('get playing(), [ok, state, pending] = [%s, %s, %s]'.format(ok, state, pending))
        if ok == Gst.StateChangeReturn.ASYNC:
            return pending == Gst.State.PLAYING
        elif ok == Gst.StateChangeReturn.SUCCESS:
            return state == Gst.State.PLAYING
        else:
            return False

    @property
    def playing(self):
        return self._get_playing()

    @log
    def _sync_playing(self):
        if self._get_playing():
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
        self.progressScale.set_value(0)
        self._set_duration(media.get_duration())
        self.songTotalTimeLabel.set_label(self.seconds_to_string(media.get_duration()))
        self.progressScale.set_sensitive(True)

        self.playBtn.set_sensitive(True)
        self._sync_prev_next()

        artist = _("Unknown Artist")
        try:
            assert media.get_artist() is not None
            artist = media.get_artist()
        except:
            pass
        finally:
            self.artistLabel.set_label(artist)

        album = _("Unknown Album")
        try:
            assert media.get_album() is not None
            album = media.get_album()
        except:
            pass

        self.coverImg.set_from_pixbuf(self._symbolicIcon)
        self.cache.lookup(
            media, ART_SIZE, ART_SIZE, self._on_cache_lookup, None, artist, album)

        self.titleLabel.set_label(AlbumArtCache.get_media_title(media))

        url = media.get_url()
        if url != self.player.get_value('current-uri', 0):
            self.player.set_property('uri', url)

        currentTrack = self.playlist.get_iter(self.currentTrack.get_path())
        self.emit('playlist-item-changed', self.playlist, currentTrack)
        self.emit('current-changed')

    @log
    def _on_cache_lookup(self, pixbuf, path, data=None):
        if pixbuf is not None:
            self.coverImg.set_from_pixbuf(pixbuf)
        self.emit('thumbnail-updated', path)

    @log
    def play(self):
        if self.playlist is None:
            return

        if self.player.get_state(1)[1] != Gst.State.PAUSED:
            self.stop()

            media = self.get_current_media()
            if not media:
                return

            self.load(media)

        self.player.set_state(Gst.State.PLAYING)
        self._update_position_callback()
        if not self.timeout:
            self.timeout = GLib.timeout_add(1000, self._update_position_callback)

        self.emit('playback-status-changed')
        self.emit('playing-changed')

    @log
    def pause(self):
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None

        self.player.set_state(Gst.State.PAUSED)
        self.emit('playback-status-changed')
        self.emit('playing-changed')

    @log
    def stop(self):
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None

        self.player.set_state(Gst.State.NULL)
        self.emit('playing-changed')

    @log
    def play_next(self):
        if self.playlist is None:
            return True

        if not self.nextBtn.get_sensitive():
            return True

        self.stop()
        self.currentTrack = self._get_next_track()

        if self.currentTrack:
            self.play()

    @log
    def play_previous(self):
        if self.playlist is None:
            return

        if self.prevBtn.get_sensitive() is False:
            return

        position = self.get_position() / 1000000
        if position >= 5:
            self.progressScale.set_value(0)
            self.on_progress_scale_change_value(self.progressScale)
            return

        self.stop()

        self.currentTrack = self._get_previous_track()
        if self.currentTrack:
            self.play()

    @log
    def play_pause(self):
        if self.player.get_state(1)[1] == Gst.State.PLAYING:
            self.set_playing(False)
        else:
            self.set_playing(True)

    @log
    def set_playlist(self, type, id, model, iter, field):
        self.stop()

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
        self.playlistField = field

        if old_playlist != model:
            self.playlist_insert_handler = model.connect('row-inserted', self._on_playlist_size_changed)
            self.playlist_delete_handler = model.connect('row-deleted', self._on_playlist_size_changed)
            self.emit('playlist-changed')
        self.emit('current-changed')

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
        self.coverImg = self._ui.get_object('cover')
        self.duration = self._ui.get_object('duration')
        self.repeatBtnImage = self._ui.get_object('playlistRepeat')

        if Gtk.Settings.get_default().get_property('gtk_application_prefer_dark_theme'):
            color = Gdk.RGBA(red=1.0, green=1.0, blue=1.0, alpha=1.0)
        else:
            color = Gdk.RGBA(red=0.0, green=0.0, blue=0.0, alpha=0.0)
        self._playImage.override_color(Gtk.StateFlags.ACTIVE, color)
        self._pauseImage.override_color(Gtk.StateFlags.ACTIVE, color)

        self._sync_repeat_image()

        self.prevBtn.connect('clicked', self._on_prev_btn_clicked)
        self.playBtn.connect('clicked', self._on_play_btn_clicked)
        self.nextBtn.connect('clicked', self._on_next_btn_clicked)
        self.progressScale.connect('button-press-event', self._on_progress_scale_event)
        self.progressScale.connect('value-changed', self._on_progress_value_changed)
        self.progressScale.connect('button-release-event', self._on_progress_scale_button_released)

    @log
    def _on_progress_scale_button_released(self, scale, data):
        self.on_progress_scale_change_value(self.progressScale)
        self._update_position_callback()
        self.player.set_state(self._lastState)
        self.timeout = GLib.timeout_add(1000, self._update_position_callback)
        return False

    def _on_progress_value_changed(self, widget):
        seconds = int(self.progressScale.get_value() / 60)
        self.songPlaybackTimeLabel.set_label(self.seconds_to_string(seconds))
        return False

    @log
    def _on_progress_scale_event(self, scale, data):
        self._lastState = self.player.get_state(1)[1]
        self.player.set_state(Gst.State.PAUSED)
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None
        return False

    @log
    def seconds_to_string(self, duration):
        seconds = duration
        minutes = seconds // 60
        seconds %= 60

        return '%i:%02i' % (minutes, seconds)

    @log
    def _on_play_btn_clicked(self, btn):
        if self._get_playing():
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
        self.progressScale.set_range(0.0, duration * 60)

    @log
    def _update_position_callback(self):
        position = self.player.query_position(Gst.Format.TIME)[1] / 1000000000
        if position > 0:
            self.progressScale.set_value(position * 60)
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
        if seconds != self.duration:
            self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, seconds * 1000000000)
            try:
                self.emit('seeked', seconds * 1000000)
            except TypeError:
                # See https://bugzilla.gnome.org/show_bug.cgi?id=733095
                pass
        else:
            duration = self.player.query_duration(Gst.Format.TIME)
            if duration:
                # Rewind a second back before the track end
                self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, duration[1] - 1000000000)
                try:
                    self.emit('seeked', (duration[1] - 1000000000) / 1000)
                except TypeError:
                    # See https://bugzilla.gnome.org/show_bug.cgi?id=733095
                    pass
        return True

    # MPRIS

    @log
    def Stop(self):
        self.progressScale.set_value(0)
        self.progressScale.set_sensitive(False)
        self.playBtn.set_image(self._playImage)
        self.stop()
        self.emit('playback-status-changed')

    @log
    def get_playback_status(self):
        ok, state, pending = self.player.get_state(0)
        if ok == Gst.StateChangeReturn.ASYNC:
            state = pending
        elif (ok != Gst.StateChangeReturn.SUCCESS):
            return PlaybackStatus.STOPPED

        if state == Gst.State.PLAYING:
            return PlaybackStatus.PLAYING
        elif state == Gst.State.PAUSED:
            return PlaybackStatus.PAUSED
        else:
            return PlaybackStatus.STOPPED

    @log
    def get_repeat_mode(self):
        return self.repeat

    @log
    def set_repeat_mode(self, mode):
        self.repeat = mode
        self._sync_repeat_image()

    @log
    def get_position(self):
        return self.player.query_position(Gst.Format.TIME)[1] / 1000

    @log
    def set_position(self, offset, start_if_ne=False, next_on_overflow=False):
        if offset < 0:
            if start_if_ne:
                offset = 0
            else:
                return

        duration = self.player.query_duration(Gst.Format.TIME)
        if duration is None:
            return

        if duration[1] >= offset * 1000:
            self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, offset * 1000)
            self.emit('seeked', offset)
        elif next_on_overflow:
            self.play_next()

    @log
    def get_volume(self):
        return self.player.get_volume(GstAudio.StreamVolumeFormat.LINEAR)

    @log
    def set_volume(self, rate):
        self.player.set_volume(GstAudio.StreamVolumeFormat.LINEAR, rate)
        self.emit('volume-changed')

    @log
    def get_current_media(self):
        if not self.currentTrack or not self.currentTrack.valid():
            return None
        currentTrack = self.playlist.get_iter(self.currentTrack.get_path())
        return self.playlist.get_value(currentTrack, self.playlistField)


class SelectionToolbar():

    @log
    def __init__(self):
        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Music/SelectionToolbar.ui')
        self.actionbar = self._ui.get_object('actionbar')
        self._add_to_playlist_button = self._ui.get_object('button1')
        self._remove_from_playlist_button = self._ui.get_object('button2')
        self.actionbar.set_visible(False)
