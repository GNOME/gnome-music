from gi.repository import GIRepository
GIRepository.Repository.prepend_search_path('libgd')

from gi.repository import Gtk, Gst, GLib, GstAudio, Gdk, Grl, Gio, GstPbutils, GObject
from random import randint
from gnomemusic.albumArtCache import AlbumArtCache

ART_SIZE = 34

MediaPlayer2PlayerIface = """
<interface name="org.mpris.MediaPlayer2.Player">
  <method name="Next"/>
  <method name="Previous"/>
  <method name="Pause"/>
  <method name="PlayPause"/>
  <method name="Stop"/>
  <method name="Play"/>
  <method name="Seek">
    <arg direction="in" name="Offset" type="x"/>
  </method>
  <method name="SetPosition">
    <arg direction="in" name="TrackId" type="o"/>
    <arg direction="in" name="Position" type="x"/>
  </method>
  <method name="OpenUri">
    <arg direction="in" name="Uri" type="s"/>
  </method>
  <signal name="Seeked">
    <arg name="Position" type="x"/>
  </signal>
  <property name="PlaybackStatus" type="s" access="read"/>
  <property name="LoopStatus" type="s" access="readwrite"/>
  <property name="Rate" type="d" access="readwrite"/>
  <property name="Shuffle" type="b" access="readwrite"/>
  <property name="Metadata" type="a{sv}" access="read"/>
  <property name="Volume" type="d" access="readwrite"/>
  <property name="Position" type="x" access="read"/>
  <property name="MinimumRate" type="d" access="read"/>
  <property name="MaximumRate" type="d" access="read"/>
  <property name="CanGoNext" type="b" access="read"/>
  <property name="CanGoPrevious" type="b" access="read"/>
  <property name="CanPlay" type="b" access="read"/>
  <property name="CanPause" type="b" access="read"/>
  <property name="CanSeek" type="b" access="read"/>
  <property name="CanControl" type="b" access="read"/>
</interface>
"""


MediaPlayer2PlayerIface = """
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
  <property name='Metadata' type='a{sv}' access='read'/>
  <property name='Volume' type='d' access='readwrite'/>
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
"""


class RepeatType:
    NONE = 0
    SONG = 1
    ALL = 2
    SHUFFLE = 3


class Player(GObject.GObject):
    nextTrack = None
    timeout = None

    __gsignals__ = {
        'playing-changed': (GObject.SIGNAL_RUN_FIRST, None, ())
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.playlist = None
        self.playlistType = None
        self.playlistId = None
        self.playlistField = None
        self.currentTrack = None
        self._lastState = Gst.State.PAUSED
        self.cache = AlbumArtCache.getDefault()
        self._symbolicIcon = self.cache.makeDefaultIcon(ART_SIZE, ART_SIZE)

        Gst.init(None)
        self.discoverer = GstPbutils.Discoverer()
        self.player = Gst.ElementFactory.make("playbin", "player")
        self.bus = self.player.get_bus()
        self.bus.add_signal_watch()

        self._settings = Gio.Settings.new('org.gnome.Music')
        self._settings.connect('changed::repeat', self._onSettingsChanged)
        self.repeat = self._settings.get_enum('repeat')

        #self._dbusImpl = Gio.DBusExportedObject.wrapJSObject(MediaPlayer2PlayerIface, self)
        #self._dbusImpl.export(Gio.DBus.session, '/org/mpris/MediaPlayer2')

        self.bus.connect("message::state-changed", self._onBusStateChanged)
        self.bus.connect("message::error", self._onBusError)
        self.bus.connect("message::eos", self._onBusEos)
        self._setupView()
        if self.nextTrack:
            GLib.idle_add(GLib.PRIORITY_HIGH, self._onGLibIdle)
        elif (self.repeat == RepeatType.NONE):
            self.stop()
            self.playBtn.set_image(self._playImage)
            self.progressScale.set_value(0)
            self.progressScale.sensitive = False
            self.currentTrack = self.playlist.get_iter_first()[1]
            self.load(self.playlist.get_value(self.currentTrack, self.playlistField))
        else:
            #Stop playback
            self.stop()
            self.playBtn.set_image(self._playImage)
            self.progressScale.set_value(0)
            self.progressScale.sensitive = False

    def _onSettingsChanged(self):
        self.repeat = self.settings.get_enum('repeat')
        self._syncPrevNext()
        self._syncRepeatImage()

    def _onBusStateChanged(self, bus, message):
        #Note: not all state changes are signaled through here, in particular
        #transitions between Gst.State.READY and Gst.State.NULL are never async
        #and thus don't cause a message
        #In practice, self means only Gst.State.PLAYING and Gst.State.PAUSED are
        self._syncPlaying()
        self.emit('playing-changed')

    def _onBusError(self, bus, message):
        media = self.playlist.get_value(self.currentTrack, self.playlistField)
        if media is not None:
            uri = media.get_url()
        else:
            uri = "none"
            print("URI:" + uri)
            print("Error:" + message.parse_error())
            self.stop()
            return True

    def _onBusEos(self, bus, message):
        self.nextTrack = self._getNextTrack()

    def _onGLibIdle(self):
        self.currentTrack = self.nextTrack
        self.play()

    def _getNextTrack(self):
        currentTrack = self.currentTrack
        nextTrack = None
        if self.repeat == RepeatType.SONG:
            nextTrack = currentTrack
        elif self.repeat == RepeatType.ALL:
            nextTrack = currentTrack.copy()
            if self.playlist.iter_next(nextTrack) is not None:
                nextTrack = self.playlist.get_iter_first()[1]
        elif self.repeat == RepeatType.NONE:
            nextTrack = currentTrack.copy()
            nextTrack = nextTrack if self.playlist.iter_next(nextTrack) else None
        elif self.repeat == RepeatType.SHUFFLE:
            nextTrack = self.playlist.get_iter_first()[1]
            rows = self.playlist.iter_n_children(None)
            random = randint(rows)
            for i in random:
                self.playlist.iter_next(nextTrack)

        return nextTrack

    def _getIterLast(self):
        ok, iter = self.playlist.get_iter_first()
        last = None

        while(ok):
            last = iter.copy()
            ok = self.playlist.iter_next(iter)

        return last

    def _getPreviousTrack(self):
        currentTrack = self.currentTrack

        if self.repeat == RepeatType.SONG:
            previousTrack = currentTrack
        elif self.repeat == RepeatType.ALL:
            previousTrack = currentTrack.copy()
            if self.playlist.iter_previous(previousTrack) is not None:
                previousTrack = self._getIterLast()
        elif self.repeat == RepeatType.NONE:
            previousTrack = currentTrack.copy()
            previousTrack = previousTrack if self.playlist.iter_previous(previousTrack) else None
        elif self.repeat == RepeatType.SHUFFLE:
            previousTrack = self.playlist.get_iter_first()[1]
            rows = self.playlist.iter_n_children(None)
            random = randint(0, rows)
            for i in random:
                self.playlist.iter_next(previousTrack)

        return previousTrack

    def _hasNext(self):
        if self.repeat in [RepeatType.ALL, RepeatType.SONG, RepeatType.SHUFFLE]:
            return True
        else:
            tmp = self.currentTrack.copy()
            return self.playlist.iter_next(tmp)

    def _hasPrevious(self):
        if self.repeat in [RepeatType.ALL, RepeatType.SONG, RepeatType.SHUFFLE]:
            return True
        else:
            tmp = self.currentTrack.copy()
            return self.playlist.iter_previous(tmp)

    def getPlaying(self):
        ok, state, pending = self.player.get_state(0)
        #log('get playing(), [ok, state, pending] = [%s, %s, %s]'.format(ok, state, pending))
        if ok == Gst.StateChangeReturn.ASYNC:
            return pending == Gst.State.PLAYING
        elif ok == Gst.StateChangeReturn.SUCCESS:
            return state == Gst.State.PLAYING
        else:
            return False

    def _syncPlaying(self):
        self.playBtn.image = self._playImage if self.playing is True else self._pauseImage

    def _syncPrevNext(self):
        hasNext = self._hasNext()
        hasPrevious = self._hasPrevious()

        self.nextBtn.sensitive = hasNext
        self.prevBtn.sensitive = hasPrevious

        #self._dbusImpl.emit_property_changed('CanGoNext', GLib.Variant.new('b', hasNext))
        #self._dbusImpl.emit_property_changed('CanGoPrevious', GLib.Variant.new('b', hasPrevious))

    def setPlaying(self, value):
        self.eventBox.show()

        if value:
            self.play()
        else:
            self.pause()

        media = self.playlist.get_value(self.currentTrack, self.playlistField)
        self.playBtn.set_image(self._pauseImage)
        return media

    def load(self, media):
        self._setDuration(media.get_duration())
        self.songTotalTimeLabel.label = self.secondsToString(media.get_duration())
        self.progressScale.sensitive = True

        self.playBtn.sensitive = True
        self._syncPrevNext()

        self.coverImg.set_from_pixbuf(self._symbolicIcon)
        self.cache.lookup(ART_SIZE, media.get_artist(), media.get_string(Grl.METADATA_KEY_ALBUM), self._onCacheLookup)

        if media.get_title() is not None:
            self.titleLabel.set_label(media.get_title())
        else:
            url = media.get_url(),
            filename = GLib.File.new_for_path(url),
            basename = filename.get_basename(),
            toShow = GLib.Uri.unescape_string(basename, None)
            self.titleLabel.set_label(toShow)

        if media.get_artist() is not None:
            self.artistLabel.set_label(media.get_artist())
        else:
            self.artistLabel.set_label("Unknown artist")

        url = media.get_url()
        if url != self.player.current_uri:
            self.player.uri = url

        #Store next available url
        #(not really useful because we can't connect to about-to-finish, but still)
        nextTrack = self._getNextTrack()

        if nextTrack:
            nextMedia = self.playlist.get_value(self.currentTrack, self.playlistField)
            self.player.nextUrl = nextMedia.get_url()
        else:
            self.player.nextUrl = None

        #self._dbusImpl.emit_property_changed('Metadata', GLib.Variant.new('a{sv}', self.Metadata))
        #self._dbusImpl.emit_property_changed('CanPlay', GLib.Variant.new('b', True))
        #self._dbusImpl.emit_property_changed('CanPause', GLib.Variant.new('b', True))

        self.emit("playlist-item-changed", self.playlist, self.currentTrack)
        self.emit('current-changed')

    def _onCacheLookup(self, pixbuf):
        if pixbuf is not None:
            self.coverImg.set_from_pixbuf(pixbuf)

    def play(self):
        if self.playlist is None:
            return

        if self.player.get_state(1)[1] != Gst.State.PAUSED:
            self.stop()

        self.load(self.playlist.get_value(self.currentTrack, self.playlistField))

        self.player.set_state(Gst.State.PLAYING)
        self._updatePositionCallback()
        if not self.timeout:
            self.timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, self._updatePositionCallback)

        #self._dbusImpl.emit_property_changed('PlaybackStatus', GLib.Variant.new('s', 'Playing'))

    def pause(self):
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = 0

        self.player.set_state(Gst.State.PAUSED)
        #self._dbusImpl.emit_property_changed('PlaybackStatus', GLib.Variant.new('s', 'Paused'))

    def stop(self):
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = 0

        self.player.set_state(Gst.State.NULL)
        #self._dbusImpl.emit_property_changed('PlaybackStatus', GLib.Variant.new('s', 'Stopped'))
        self.emit('playing-changed')

    def playNext(self):
        if self.playlist is None:
            return True

        if not self.nextBtn.sensitive:
            return True

        self.stop()
        self.currentTrack = self._getNextTrack()

        if self.currentTrack:
            self.play()

    def playPrevious(self):
        if self.playlist is None:
            return

        if self.prevBtn.sensitive is False:
            return

        self.stop()
        self.currentTrack = self._getPreviousTrack()

        if self.currentTrack:
            self.play()

    def setPlaylist(self, type, id, model, iter, field):
        self.stop()

        self.playlist = model
        self.playlistType = type
        self.playlistId = id
        self.currentTrack = iter
        self.playlistField = field
        self.emit('current-changed')

    def runningPlaylist(self, type, id, force):
        if type == self.playlistType and id == self.playlistId:
            return self.playlist
        else:
            return None

    def _setupView(self):
        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/music/PlayerToolbar.ui')
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

        if Gtk.Settings.get_default().gtk_application_prefer_dark_theme:
            color = Gdk.Color(red=65535, green=65535, blue=65535)
        else:
            color = Gdk.Color(red=0, green=0, blue=0)
        self._playImage.modify_fg(Gtk.StateType.ACTIVE, color)
        self._pauseImage.modify_fg(Gtk.StateType.ACTIVE, color)

        self._syncRepeatImage()

        self.prevBtn.connect("clicked", self._onPrevBtnClicked())
        self.playBtn.connect("clicked", self._onPlayBtnClicked())
        self.nextBtn.connect("clicked", self._onNextBtnClicked())
        self.progressScale.connect("button-press-event", self._onProgressScaleEvent)
        self.progressScale.connect("value-changed", self._onProgressValueChanged())
        self.progressScale.connect("button-release-event", self._onProgressScaleButtonReleased())

    def _onProgressScaleButtonReleased(self):
        self.onProgressScaleChangeValue(self.progressScale)
        self._updatePositionCallback()
        self.player.set_state(self._lastState)
        self.timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, self._updatePositionCallback)
        return False

    def _onProgressValueChanged(self):
        seconds = int(self.progressScale.get_value() / 60)
        self.songPlaybackTimeLabel.set_label(self.secondsToString(seconds))
        return False

    def _onProgressScaleEvent(self):
        self._lastState = self.player.get_state(1)[1]
        self.player.set_state(Gst.State.PAUSED)
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None
        return False

    def secondsToString(self, duration):
        minutes = int(duration / 60) % 60
        seconds = duration % 60

        if seconds < 10:
            return minutes + ":" + "0" + seconds
        else:
            return minutes + ":" + seconds

    def _onPlayBtnClicked(self, btn):
        if self.playing:
            self.pause()
        else:
            self.play()

    def _onNextBtnClicked(self, btn):
        self.playNext()

    def _onPrevBtnClicked(self, btn):
        self.playPrevious()

    def _setDuration(self, duration):
        self.duration = duration
        self.progressScale.set_range(0.0, duration * 60)

    def _updatePositionCallback(self):
        position = self.player.query_position(Gst.Format.TIME, None)[1] / 1000000000
        if position >= 0:
            self.progressScale.set_value(position * 60)
        return True

    def _syncRepeatImage(self):
        icon = None
        if self.repeat == RepeatType.NONE:
            icon = 'media-playlist-consecutive-symbolic'
        elif self.repeat == RepeatType.SHUFFLE:
            icon = 'media-playlist-shuffle-symbolic'
        elif self.repeat == RepeatType.ALL:
            icon = 'media-playlist-repeat-symbolic'
        elif self.repeat == RepeatType.SONG:
            icon = 'media-playlist-repeat-song-symbolic'

        self.repeatBtnImage.icon_name = icon
        #self._dbusImpl.emit_property_changed('LoopStatus', GLib.Variant.new('s', self.LoopStatus))
        #self._dbusImpl.emit_property_changed('Shuffle', GLib.Variant.new('b', self.Shuffle))

    def onProgressScaleChangeValue(self, scroll):
        seconds = scroll.get_value() / 60
        if seconds != self.duration:
            self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, seconds * 1000000000)
            #self._dbusImpl.emit_signal('Seeked', GLib.Variant.new('(x)', [seconds * 1000000]))
        else:
            duration = self.player.query_duration(Gst.Format.TIME, None)
            if duration:
                #Rewind a second back before the track end
                self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, duration[1] - 1000000000)
                #self._dbusImpl.emit_signal('Seeked', GLib.Variant.new('(x)', [(duration[1] - 1000000000) / 1000]))
        return True

    #MPRIS

    def Next(self):
        self.playNext()

    def Previous(self):
        self.playPrevious()

    def Pause(self):
        self.setPlaying(False)

    def PlayPause(self):
        if self.player.get_state(1)[1] == Gst.State.PLAYING:
            self.setPlaying(False)
        else:
            self.setPlaying(True)

    def Play(self):
        self.setPlaying(True)

    def Stop(self):
        self.progressScale.set_value(0)
        self.progressScale.sensitive = False
        self.playBtn.set_image(self._playImage)
        self.stop()

    def SeekAsync(self, params, invocation):
        offset = params

        duration = self.player.query_duration(Gst.Format.TIME, None)
        if duration is None:
            return

        if offset < 0:
            offset = 0

        if duration[1] >= offset * 1000:
            self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, offset * 1000)
            #self._dbusImpl.emit_signal('Seeked', GLib.Variant.new('(x)', [offset]))
        else:
            self.playNext()

    def SetPositionAsync(self, params, invocation):
        trackId, position = params

        if self.currentTrack is None:
            return

        media = self.playlist.get_value(self.currentTrack, self.playlistField)
        if trackId != '/org/mpris/MediaPlayer2/Track/' + media.get_id():
            return

        duration = self.player.query_duration(Gst.Format.TIME, None)
        if duration and position >= 0 and duration[1] >= position * 1000:
            self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, position * 1000)
            #self._dbusImpl.emit_signal('Seeked', GLib.Variant.new('(x)', [position]))

    def OpenUriAsync(self, params, invocation):
        uri = params
        return uri

    def getPlaybackStatus(self):
        ok, state, pending = self.player.get_state(0)
        if ok == Gst.StateChangeReturn.ASYNC:
            state = pending
        elif (ok != Gst.StateChangeReturn.SUCCESS):
            return 'Stopped'

        if state == Gst.State.PLAYING:
            return 'Playing'
        elif state == Gst.State.PAUSED:
            return 'Paused'
        else:
            return 'Stopped'

    def getLoopStatus(self):
        if self.repeat == RepeatType.NONE:
            return 'None'
        elif self.repeat == RepeatType.SONG:
            return 'Track'
        else:
            return 'Playlist'

    def setLoopStatus(self, mode):
        if mode == 'None':
            self.repeat = RepeatType.NONE
        elif mode == 'Track':
            self.repeat = RepeatType.SONG
        elif mode == 'Playlist':
            self.repeat = RepeatType.ALL
        self._syncRepeatImage()

    def getRate(self):
        return 1.0

    def setRate(self, rate):
        pass

    def getShuffle(self):
        return self.repeat == RepeatType.SHUFFLE

    def setShuffle(self, enable):
        if (enable and self.repeat != RepeatType.SHUFFLE):
            self.repeat = RepeatType.SHUFFLE
        elif enable is not None and self.repeat == RepeatType.SHUFFLE:
            self.repeat = RepeatType.NONE
        self._syncRepeatImage()

    def getMetadata(self):
        if self.currentTrack is None:
            return

        media = self.playlist.get_value(self.currentTrack, self.playlistField)
        metadata = {
            'mpris:trackid': GLib.Variant.new('s', '/org/mpris/MediaPlayer2/Track/' + media.get_id()),
            'xesam:url': GLib.Variant.new('s', media.get_url()),
            'mpris:length': GLib.Variant.new('x', media.get_duration() * 1000000),
            'xesam:trackNumber': GLib.Variant.new('i', media.get_track_number()),
            'xesam:useCount': GLib.Variant.new('i', media.get_play_count()),
            'xesam:userRating': GLib.Variant.new('d', media.get_rating()),
        }

        title = media.get_title()
        if title:
            metadata['xesam:title'] = GLib.Variant.new('s', title)

        album = media.get_album()
        if album:
            metadata['xesam:album'] = GLib.Variant.new('s', album)

        artist = media.get_artist()
        if artist:
            metadata['xesam:artist'] = GLib.Variant.new('as', [artist])
            metadata['xesam:albumArtist'] = GLib.Variant.new('as', [artist])

        genre = media.get_genre()
        if genre:
            metadata['xesam:genre'] = GLib.Variant.new('as', [genre])

        last_played = media.get_last_played()
        if last_played:
            metadata['xesam:lastUsed'] = GLib.Variant.new('s', last_played)

        thumbnail = media.get_thumbnail()
        if thumbnail:
            metadata['mpris:artUrl'] = GLib.Variant.new('s', thumbnail)

        return metadata

    def getVolume(self):
        return self.player.get_volume(GstAudio.StreamVolumeFormat.LINEAR)

    def setVolume(self, rate):
        self.player.set_volume(GstAudio.StreamVolumeFormat.LINEAR, rate)
        #self._dbusImpl.emit_property_changed('Volume', GLib.Variant.new('d', rate))

    def getPosition(self):
        return self.player.query_position(Gst.Format.TIME, None)[1] / 1000

    def getMinimumRate(self):
        return 1.0

    def getMaximumRate(self):
        return 1.0

    def getCanGoNext(self):
        return self._hasNext()

    def getCanGoPrevious(self):
        return self._hasPrevious()

    def getCanPlay(self):
        return self.currentTrack is not None

    def getCanPause(self):
        return self.currentTrack is not None

    def getCanSeek(self):
        return True

    def getCanControl(self):
        return True


class SelectionToolbar():
        def __init__(self):
            self._ui = Gtk.Builder()
            self._ui.add_from_resource('/org/gnome/music/SelectionToolbar.ui')
            self.eventbox = self._ui.get_object("eventbox1")
            self._add_to_playlist_button = self._ui.get_object("button1")
            self.eventbox.set_visible(False)
