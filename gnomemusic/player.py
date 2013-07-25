from gi.repository import GIRepository
GIRepository.Repository.prepend_search_path('libgd')

from gi.repository import Gtk, Gst, GLib, GstAudio, Gdk, Grl, Gio, GstPbutils, GObject
from random import randint
from gnomemusic.albumArtCache import AlbumArtCache

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
    playing = False

    __gsignals__ = {
        'playing-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'playlist-item-changed': (GObject.SIGNAL_RUN_FIRST, None, (Gtk.ListStore, Gtk.TreeIter)),
        'current-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'playback-status-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'repeat-mode-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'volume-changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'prev-next-invalidated': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'seeked': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.playlist = None
        self.playlistType = None
        self.playlistId = None
        self.playlistField = None
        self.currentTrack = None
        self._lastState = Gst.State.PAUSED
        self.cache = AlbumArtCache.get_default()
        self._symbolicIcon = self.cache.make_default_icon(ART_SIZE, ART_SIZE)

        Gst.init(None)
        self.discoverer = GstPbutils.Discoverer()
        self.player = Gst.ElementFactory.make("playbin", "player")
        self.bus = self.player.get_bus()
        self.bus.add_signal_watch()

        self._settings = Gio.Settings.new('org.gnome.Music')
        self._settings.connect('changed::repeat', self._on_settings_changed)
        self.repeat = self._settings.get_enum('repeat')

        self.bus.connect("message::state-changed", self._on_bus_state_changed)
        self.bus.connect("message::error", self._onBusError)
        self.bus.connect("message::eos", self._on_bus_eos)
        self._setup_view()

    def _on_settings_changed(self, settings, value):
        self.repeat = settings.get_enum('repeat')
        self._sync_prev_next()
        self._sync_repeat_image()

    def _on_bus_state_changed(self, bus, message):
        #Note: not all state changes are signaled through here, in particular
        #transitions between Gst.State.READY and Gst.State.NULL are never async
        #and thus don't cause a message
        #In practice, self means only Gst.State.PLAYING and Gst.State.PAUSED are
        self._sync_playing()
        self.emit('playing-changed')

    def _onBusError(self, bus, message):
        media = self.playlist.get_value(self.currentTrack, self.playlistField)
        if media is not None:
            uri = media.get_url()
        else:
            uri = "none"
            print("URI: " + uri)
        error, debug = message.parse_error()
        debug = debug.split('\n')
        debug = [('     ') + line.lstrip() for line in debug]
        debug = '\n'.join(debug)
        print("Error from element " + message.src.get_name() + ": " + error.message)
        print("Debugging info:\n" + debug)
        self.play_next()
        return True

    def _on_bus_eos(self, bus, message):
        self.nextTrack = self._get_next_track()

        if self.nextTrack:
            GLib.idle_add(self._on_glib_idle)
        elif (self.repeat == RepeatType.NONE):
            self.stop()
            self.playBtn.set_image(self._playImage)
            self.progressScale.set_value(0)
            self.progressScale.set_sensitive(False)
            if self.playlist is not None:
                self.currentTrack = self.playlist.get_iter_first()
                self.load(self.playlist.get_value(self.currentTrack, self.playlistField))
        else:
            #Stop playback
            self.stop()
            self.playBtn.set_image(self._playImage)
            self.progressScale.set_value(0)
            self.progressScale.set_sensitive(False)
            self.emit('playback-status-changed')

    def _on_glib_idle(self):
        self.currentTrack = self.nextTrack
        self.play()

    def _get_next_track(self):
        currentTrack = self.currentTrack
        nextTrack = None
        if self.repeat == RepeatType.SONG:
            nextTrack = currentTrack
        elif self.repeat == RepeatType.ALL:
            nextTrack = self.playlist.iter_next(currentTrack)
            if nextTrack is None:
                nextTrack = self.playlist.get_iter_first()
        elif self.repeat == RepeatType.NONE:
            nextTrack = self.playlist.iter_next(currentTrack)
        elif self.repeat == RepeatType.SHUFFLE:
            nextTrack = self.playlist.get_iter_first()
            rows = self.playlist.iter_n_children(None)
            for i in range(1, randint(1, rows)):
                nextTrack = self.playlist.iter_next(nextTrack)

        return nextTrack

    def _get_iter_last(self):
        iter = self.playlist.get_iter_first()
        last = None

        while iter is not None:
            last = iter
            iter = self.playlist.iter_next(iter)

        return last

    def _get_previous_track(self):
        currentTrack = self.currentTrack
        previousTrack = None

        if self.repeat == RepeatType.SONG:
            previousTrack = currentTrack
        elif self.repeat == RepeatType.ALL:
            previousTrack = self.playlist.iter_previous(currentTrack)
            if previousTrack is None:
                previousTrack = self._get_iter_last()
        elif self.repeat == RepeatType.NONE:
            previousTrack = self.playlist.iter_previous(currentTrack)
        elif self.repeat == RepeatType.SHUFFLE:
            previousTrack = self.playlist.get_iter_first()
            rows = self.playlist.iter_n_children(None)
            for i in range(1, randint(1, rows)):
                previousTrack = self.playlist.iter_next(previousTrack)

        return previousTrack

    def has_next(self):
        if self.repeat in [RepeatType.ALL, RepeatType.SONG, RepeatType.SHUFFLE]:
            return True
        else:
            tmp = self.currentTrack.copy()
            return self.playlist.iter_next(tmp) is not None

    def has_previous(self):
        if self.repeat in [RepeatType.ALL, RepeatType.SONG, RepeatType.SHUFFLE]:
            return True
        else:
            tmp = self.currentTrack.copy()
            return self.playlist.iter_previous(tmp) is not None

    def _get_playing(self):
        ok, state, pending = self.player.get_state(0)
        #log('get playing(), [ok, state, pending] = [%s, %s, %s]'.format(ok, state, pending))
        if ok == Gst.StateChangeReturn.ASYNC:
            return pending == Gst.State.PLAYING
        elif ok == Gst.StateChangeReturn.SUCCESS:
            return state == Gst.State.PLAYING
        else:
            return False

    def _sync_playing(self):
        image = self._pauseImage if self._get_playing() else self._playImage
        if self.playBtn.get_image() != image:
            self.playBtn.set_image(image)

    def _sync_prev_next(self):
        hasNext = self.has_next()
        hasPrevious = self.has_previous()

        self.nextBtn.set_sensitive(hasNext)
        self.prevBtn.set_sensitive(hasPrevious)

        self.emit('prev-next-invalidated')

    def set_playing(self, value):
        self.eventBox.show()

        if value:
            self.play()
        else:
            self.pause()

        media = self.playlist.get_value(self.currentTrack, self.playlistField)
        self.playBtn.set_image(self._pauseImage)
        return media

    def load(self, media):
        self._set_duration(media.get_duration())
        self.songTotalTimeLabel.set_label(self.seconds_to_string(media.get_duration()))
        self.progressScale.set_sensitive(True)

        self.playBtn.set_sensitive(True)
        self._sync_prev_next()

        self.coverImg.set_from_pixbuf(self._symbolicIcon)
        self.cache.lookup(ART_SIZE, media.get_artist(), media.get_string(Grl.METADATA_KEY_ALBUM), self._on_cache_lookup)

        self.titleLabel.set_label(AlbumArtCache.get_media_title(media))

        if media.get_artist() is not None:
            self.artistLabel.set_label(media.get_artist())
        else:
            self.artistLabel.set_label("Unknown artist")

        url = media.get_url()
        if url != self.player.get_value("current-uri", 0):
            self.player.set_property("uri", url)

        #Store next available url
        #(not really useful because we can't connect to about-to-finish, but still)
        nextTrack = self._get_next_track()

        if nextTrack:
            nextMedia = self.playlist.get_value(self.currentTrack, self.playlistField)
            self.player.nextUrl = nextMedia.get_url()
        else:
            self.player.nextUrl = None

        self.emit("playlist-item-changed", self.playlist, self.currentTrack)
        self.emit('current-changed')

    def _on_cache_lookup(self, pixbuf, path):
        if pixbuf is not None:
            self.coverImg.set_from_pixbuf(pixbuf)

    def play(self):
        if self.playlist is None:
            return

        if self.player.get_state(1)[1] != Gst.State.PAUSED:
            self.stop()

        self.load(self.playlist.get_value(self.currentTrack, self.playlistField))

        self.player.set_state(Gst.State.PLAYING)
        self._update_position_callback()
        if not self.timeout:
            self.timeout = GLib.timeout_add(1000, self._update_position_callback)

        self.emit('playback-status-changed')

    def pause(self):
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None

        self.player.set_state(Gst.State.PAUSED)
        self.emit('playback-status-changed')
        self.emit('playing-changed')

    def stop(self):
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None

        self.player.set_state(Gst.State.NULL)
        self.emit('playing-changed')

    def play_next(self):
        if self.playlist is None:
            return True

        if not self.nextBtn.get_sensitive():
            return True

        self.stop()
        self.currentTrack = self._get_next_track()

        if self.currentTrack:
            self.play()

    def play_previous(self):
        if self.playlist is None:
            return

        if self.prevBtn.get_sensitive() is False:
            return

        self.stop()
        self.currentTrack = self._get_previous_track()

        if self.currentTrack:
            self.play()

    def play_pause(self):
        if self.player.get_state(1)[1] == Gst.State.PLAYING:
            self.set_playing(False)
        else:
            self.set_playing(True)

    def set_playlist(self, type, id, model, iter, field):
        self.stop()

        self.playlist = model
        self.playlistType = type
        self.playlistId = id
        self.currentTrack = iter
        self.playlistField = field
        self.emit('current-changed')

    def running_playlist(self, type, id):
        if type == self.playlistType and id == self.playlistId:
            return self.playlist
        else:
            return None

    def _setup_view(self):
        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Music/PlayerToolbar.ui')
        self.eventBox = self._ui.get_object('eventBox')
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
            color = Gdk.Color(red=65535, green=65535, blue=65535)
        else:
            color = Gdk.Color(red=0, green=0, blue=0)
        self._playImage.modify_fg(Gtk.StateType.ACTIVE, color)
        self._pauseImage.modify_fg(Gtk.StateType.ACTIVE, color)

        self._sync_repeat_image()

        self.prevBtn.connect("clicked", self._on_prev_btn_clicked)
        self.playBtn.connect("clicked", self._on_play_btn_clicked)
        self.nextBtn.connect("clicked", self._on_next_btn_clicked)
        self.progressScale.connect("button-press-event", self._on_progress_scale_event)
        self.progressScale.connect("value-changed", self._on_progress_value_changed)
        self.progressScale.connect("button-release-event", self._on_progress_scale_button_released)

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

    def _on_progress_scale_event(self, scale, data):
        self._lastState = self.player.get_state(1)[1]
        self.player.set_state(Gst.State.PAUSED)
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None
        return False

    def seconds_to_string(self, duration):
        seconds = duration
        minutes = seconds // 60
        seconds %= 60

        return "%i:%02i" % (minutes, seconds)

    def _on_play_btn_clicked(self, btn):
        if self._get_playing():
            self.pause()
        else:
            self.play()

    def _on_next_btn_clicked(self, btn):
        self.play_next()

    def _on_prev_btn_clicked(self, btn):
        self.play_previous()

    def _set_duration(self, duration):
        self.duration = duration
        self.progressScale.set_range(0.0, duration * 60)

    def _update_position_callback(self):
        position = self.player.query_position(Gst.Format.TIME)[1] / 1000000000
        if position >= 0:
            self.progressScale.set_value(position * 60)
        return True

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

    def on_progress_scale_change_value(self, scroll):
        seconds = scroll.get_value() / 60
        if seconds != self.duration:
            self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, seconds * 1000000000)
            self.emit('seeked', seconds * 1000000)
        else:
            duration = self.player.query_duration(Gst.Format.TIME)
            if duration:
                #Rewind a second back before the track end
                self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, duration[1] - 1000000000)
                self.emit('seeked', (duration[1] - 1000000000) / 1000)
        return True

    #MPRIS

    def Stop(self):
        self.progressScale.set_value(0)
        self.progressScale.set_sensitive(False)
        self.playBtn.set_image(self._playImage)
        self.stop()
        self.emit('playback-status-changed')

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

    def get_repeat_mode(self):
        return self.repeat

    def set_repeat_mode(self, mode):
        self.repeat = mode
        self._sync_repeat_image()

    def get_position(self):
        return self.player.query_position(Gst.Format.TIME)[1] / 1000

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

    def get_metadata(self):
        if self.currentTrack is None:
            return {}

        media = self.playlist.get_value(self.currentTrack, self.playlistField)
        metadata = {
            'mpris:trackid': '/org/mpris/MediaPlayer2/Track/%s' % media.get_id(),
            'xesam:url': media.get_url(),
            'mpris:length': media.get_duration() * 1000000,
            'xesam:trackNumber': media.get_track_number(),
            'xesam:useCount': media.get_play_count(),
            'xesam:userRating': media.get_rating(),
        }

        title = AlbumArtCache.get_media_title(media)
        if title:
            metadata['xesam:title'] = title

        album = media.get_album()
        if album:
            metadata['xesam:album'] = album

        artist = media.get_artist()
        if artist:
            metadata['xesam:artist'] = [artist]
            metadata['xesam:albumArtist'] = [artist]

        genre = media.get_genre()
        if genre:
            metadata['xesam:genre'] = [genre]

        last_played = media.get_last_played()
        if last_played:
            metadata['xesam:lastUsed'] = last_played

        thumbnail = media.get_thumbnail()
        if thumbnail:
            metadata['mpris:artUrl'] = thumbnail

        return metadata

    def get_volume(self):
        return self.player.get_volume(GstAudio.StreamVolumeFormat.LINEAR)

    def set_volume(self, rate):
        self.player.set_volume(GstAudio.StreamVolumeFormat.LINEAR, rate)
        self.emit('volume-changed')


class SelectionToolbar():
        def __init__(self):
            self._ui = Gtk.Builder()
            self._ui.add_from_resource('/org/gnome/Music/SelectionToolbar.ui')
            self.eventbox = self._ui.get_object("eventbox1")
            self._add_to_playlist_button = self._ui.get_object("button1")
            self.eventbox.set_visible(False)
