from gi.repository import Gtk, Gst, GLib

ART_SIZE = 34

class Player():
    def __init__(self):
        self.playlist = None
        self.playlistType = None
        self.playlistId = None
        self.playlistField = None
        self.currentTrack = None
        self._lastState = Gst.State.PAUSED
        self.cache = AlbumArtCache.getDefault()
        self._symbolicIcon = self.cache.makeDefaultIcon(ART_SIZE, ART_SIZE)

        Gst.init(None, 0)
        self.discoverer = new GstPbutils.Discoverer()
        self.player = Gst.ElementFactory.make("playbin", "player")
        self.bus = self.player.get_bus()
        self.bus.add_signal_watch()

        self._settings = Gio.Settings.new('org.gnome.Music')
        self._settings.connect('changed::repeat', self._onSettingsChanged)
        self.repeat = self._settings.get_enum('repeat')

        self._dbusImpl = Gio.DBusExportedObject.wrapJSObject(MediaPlayer2PlayerIface, self)
        self._dbusImpl.export(Gio.DBus.session, '/org/mpris/MediaPlayer2')

        self.bus.connect("message::state-changed", self._onBusStateChanged)
        self.bus.connect("message::error", self._onBusError)
        self.bus.connect("message::eos", self._onBusEos)

        if(nextTrack):
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

        self._setupView()


    def _onSettingsChanged(self):
        self.repeat = settings.get_enum('repeat')
        self._syncPrevNext()
        self._syncRepeatImage()

    def _onBusStateChanged(self, bus, message):
        #Note: not all state changes are signaled through here, in particular
        #transitions between Gst.State.READY and Gst.State.NULL are never async
        #and thus don't cause a message
        #In practice, self means only Gst.State.PLAYING and Gst.State.PAUSED are
        self._syncPlaying()
        self.emit('playing-changed')

    def _onBussError(self, bus, message):
        let media =  self.playlist.get_value( self.currentTrack, self.playlistField)
        if(media != None):
            uri = media.get_url()
        else:
            uri = "none"
            log("URI:" + uri)
            log("Error:" + message.parse_error())
            self.stop()
            return True

    def _onBusEos(self, bus, message):
        nextTrack = self._getNextTrack()

    def _onGLibIdle(self):
        self.currentTrack = nextTrack
        self.play()


    def _getNextTrack(self):
        currentTrack = self.currentTrack
        nextTrack = None
        if self.repeat == RepeatType.SONG:
            nextTrack = currentTrack
        elif self.repeat == RepeatType.ALL:
            nextTrack = currentTrack.copy()
            if !self.playlist.iter_next(nextTrack):
                nextTrack = self.playlist.get_iter_first()[1]
        elif self.repeat == RepeatType.NONE:
            nextTrack = currentTrack.copy()
            nextTrack = self.playlist.iter_next(nextTrack) ? nextTrack : None
        elif self.repeat == RepeatType.SHUFFLE:
            nextTrack = self.playlist.get_iter_first()[1]
            let rows = self.playlist.iter_n_children(null)
            let random = Math.floor(Math.random() * rows)
            for i in random:
                self.playlist.iter_next(nextTrack)

        return nextTrack

    def _getIterLast():
        ok, iter = self.playlist.get_iter_first()
        last = None

        while(ok):
            last = iter.copy()
            ok = self.playlist.iter_next(iter)

        return last


    def _getPreviousTrack(self):
        let currentTrack = self.currentTrack
        let previousTrack

        if self.repeat = RepeatType.SONG:
            previousTrack = currentTrack
        elif self.repeat = RepeatType.ALL:
            previousTrack = currentTrack.copy()
            if !self.playlist.iter_previous(previousTrack):
                previousTrack = self._getIterLast()
        elif self.repeat = RepeatType.NONE:
            previousTrack = currentTrack.copy()
            previousTrack = self.playlist.iter_previous(previousTrack) ? previousTrack : null
        elif self.repeat = RepeatType.SHUFFLE:
            previousTrack = self.playlist.get_iter_first()[1]
            rows = self.playlist.iter_n_children(null)
            random = Math.floor(Math.random() * rows)
            for i in random:
                self.playlist.iter_next(previousTrack)

        return previousTrack


    def _hasNext(self):
        if self.repeat == RepeatType.ALL or
            self.repeat == RepeatType.SONG or
            self.repeat == RepeatType.SHUFFLE:
            return True
        else:
            tmp = self.currentTrack.copy()
            return self.playlist.iter_next(tmp)

    def _hasPrevious(self):
        if self.repeat == RepeatType.ALL or
            self.repeat == RepeatType.SONG or
            self.repeat == RepeatType.SHUFFLE:
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
        self.playBtn.image = self.playing ? self._pauseImage : self._playImage

    def _syncPrevNext(self):
        hasNext = self._hasNext()
        hasPrevious = self._hasPrevious()

        self.nextBtn.sensitive = hasNext
        self.prevBtn.sensitive = hasPrevious

        self._dbusImpl.emit_property_changed('CanGoNext', GLib.Variant.new('b', hasNext))
        self._dbusImpl.emit_property_changed('CanGoPrevious', GLib.Variant.new('b', hasPrevious))
    },

    def setPlaying(self, value):
        self.eventBox.show()

        if (value)
            self.play()
        else
            self.pause()

        media = self.playlist.get_value(self.currentTrack, self.playlistField)
        self.playBtn.set_image(self._pauseImage)

    def load(self, media):
        self._setDuration(media.get_duration())
        self.songTotalTimeLabel.label = self.secondsToString(media.get_duration())
        self.progressScale.sensitive = true

        self.playBtn.sensitive = True
        self._syncPrevNext()

        self.coverImg.set_from_pixbuf(self._symbolicIcon)
        self.cache.lookup(ART_SIZE, media.get_artist(), media.get_string(Grl.METADATA_KEY_ALBUM), _onCacheLookup)

        if media.get_title() != None:
            self.titleLabel.set_label(media.get_title())
        else:
            url = media.get_url(),
            filename = GLib.File.new_for_path(url),
            basename = filename.get_basename(),
            toShow = GLib.Uri.unescape_string(basename, None)
            self.titleLabel.set_label(toShow)

        if media.get_artist() != None:
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

        self._dbusImpl.emit_property_changed('Metadata', GLib.Variant.new('a{sv}', self.Metadata))
        self._dbusImpl.emit_property_changed('CanPlay', GLib.Variant.new('b', true))
        self._dbusImpl.emit_property_changed('CanPause', GLib.Variant.new('b', true))

        self.emit("playlist-item-changed", self.playlist, self.currentTrack)
        self.emit('current-changed')

    def _onCacheLookup(self, pixbuf):
        if (pixbuf != None) {
            self.coverImg.set_from_pixbuf(pixbuf)

    def play(self):
        if (self.playlist == None)
            return True

        if self.player.get_state(1)[1] != Gst.State.PAUSED:
            self.stop()

        self.load(self.playlist.get_value(self.currentTrack, self.playlistField))

        self.player.set_state(Gst.State.PLAYING)
        self._updatePositionCallback()
        if (!self.timeout)
            self.timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, self._updatePositionCallback)

        self._dbusImpl.emit_property_changed('PlaybackStatus', GLib.Variant.new('s', 'Playing'))

    def pause(self):
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = 0

        self.player.set_state(Gst.State.PAUSED)
        self._dbusImpl.emit_property_changed('PlaybackStatus', GLib.Variant.new('s', 'Paused'))

    def stop(self):
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = 0

        self.player.set_state(Gst.State.NULL)
        self._dbusImpl.emit_property_changed('PlaybackStatus', GLib.Variant.new('s', 'Stopped'))
        self.emit('playing-changed')

    def playNext(self):
        if self.playlist == None:
            return True

        if !self.nextBtn.sensitive:
            return True

        self.stop()
        self.currentTrack = self._getNextTrack()

        if self.currentTrack:
            self.play()

    def playPrevious(self):
        if self.playlist == None:
            return True

        if !self.prevBtn.sensitive:
            return True

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

    def runningPlaylist(self, type, id, force){
        if type == self.playlistType && id == self.playlistId:
            return self.playlist
        else:
            return None

    def _setupView(self):
        self._ui = new Gtk.Builder()
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
            color = new Gdk.Color(red=65535,green=65535,blue=65535)
        else:
            color = new Gdk.Color(red=0,green=0,blue=0)
        self._playImage.modify_fg(Gtk.StateType.ACTIVE,color)
        self._pauseImage.modify_fg(Gtk.StateType.ACTIVE,color)

        self._syncRepeatImage()

        self.prevBtn.connect("clicked", self._onPrevBtnClicked)
        self.playBtn.connect("clicked", self._onPlayBtnClicked)
        self.nextBtn.connect("clicked", self._onNextBtnClicked)
        self.progressScale.connect("button-press-event", _onProgrssScaleEvent)
        self.progressScale.connect("value-changed", Lang.bind(self,
            function() {
                let seconds = Math.floor(self.progressScale.get_value() / 60)
                self.songPlaybackTimeLabel.set_label(self.secondsToString(seconds))
                return false
            }))
        self.progressScale.connect("button-release-event", Lang.bind(self,
            function() {
                self.onProgressScaleChangeValue(self.progressScale)
                self._updatePositionCallback()
                self.player.set_state(self._lastState)
                self.timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, Lang.bind(self, self._updatePositionCallback))
                return false
            }))

    def _onProgressScaleEvent(self):
        self._lastState = self.player.get_state(1)[1]
        self.player.set_state(Gst.State.PAUSED)
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = None
        return False

    def secondsToString(self, duration):
        minutes = parseInt( duration / 60 ) % 60
        seconds = duration % 60

        return minutes + ":" + (seconds  < 10 ? "0" + seconds : seconds)
    },

    def _onPlayBtnClicked(self, btn):
        if self.playing:
            self.pause()
        else:
            self.play()

    def _onNextBtnClicked(self, btn):
        self.playNext()

    def _onPrevBtnClicked(self, btn:
        self.playPrevious()

    def _setDuration(self, duration):
        self.duration = duration
        self.progressScale.set_range(0.0, duration*60)

    def _updatePositionCallback(self):
        position = self.player.query_position(Gst.Format.TIME, null)[1]/1000000000
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
        self._dbusImpl.emit_property_changed('LoopStatus', GLib.Variant.new('s', self.LoopStatus))
        self._dbusImpl.emit_property_changed('Shuffle', GLib.Variant.new('b', self.Shuffle))


    def onProgressScaleChangeValue(self, scroll):
        seconds = scroll.get_value() / 60
        if seconds != self.duration:
            self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, seconds * 1000000000)
            self._dbusImpl.emit_signal('Seeked', GLib.Variant.new('(x)', [seconds * 1000000]))
        else:
            duration = self.player.query_duration(Gst.Format.TIME, None)
            if duration:
                #Rewind a second back before the track end
                self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, duration[1]-1000000000)
                self._dbusImpl.emit_signal('Seeked', GLib.Variant.new('(x)', [(duration[1]-1000000000)/1000]))
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
        self.progressScale.sensitive = false
        self.playBtn.set_image(self._playImage)
        self.stop()

    def SeekAsync(self, params, invocation):
        offset = params

        duration = self.player.query_duration(Gst.Format.TIME, null)
        if !duration:
            return False

        if offset < 0:
            offset = 0

        if duration[1] >= offset * 1000:
            self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, offset * 1000)
            self._dbusImpl.emit_signal('Seeked', GLib.Variant.new('(x)', [offset]))
        else:
            self.playNext()

    def SetPositionAsync(self, params, invocation):
        trackId, position = params

        if self.currentTrack == None:
            return True

        media = self.playlist.get_value(self.currentTrack, self.playlistField)
        if trackId != '/org/mpris/MediaPlayer2/Track/' + media.get_id():
            return True

        duration = self.player.query_duration(Gst.Format.TIME, None)
        if duration && position >= 0 && duration[1] >= position * 1000:
            self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, position * 1000)
            self._dbusImpl.emit_signal('Seeked', GLib.Variant.new('(x)', [position]))

    def OpenUriAsync(self, params, invocation):
        uri = params

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

    def getLoopStatus(self) {
        if self.repeat == RepeatType.NONE:
            return 'None'
        elif self.repeat == RepeatType.SONG:
            return 'Track'
        else:
            return 'Playlist'

    def setLoopStatus(mode) {
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
        if (enable && self.repeat != RepeatType.SHUFFLE) {
            self.repeat = RepeatType.SHUFFLE
        elif !enable and self.repeat == RepeatType.SHUFFLE:
            self.repeat = RepeatType.NONE
        self._syncRepeatImage()

    def getMetadata() {
        if self.currentTrack == None:
            return {}

        media = self.playlist.get_value(self.currentTrack, self.playlistField)
        metadata = {
            'mpris:trackid': GLib.Variant.new('s', '/org/mpris/MediaPlayer2/Track/' + media.get_id()),
            'xesam:url': GLib.Variant.new('s', media.get_url()),
            'mpris:length': GLib.Variant.new('x', media.get_duration()*1000000),
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

    def setVolume(self,rate):
        self.player.set_volume(GstAudio.StreamVolumeFormat.LINEAR, rate)
        self._dbusImpl.emit_property_changed('Volume', GLib.Variant.new('d', rate))

    def getPosition(self)
        return self.player.query_position(Gst.Format.TIME, None)[1]/1000

    def getMinimumRate(self):
        return 1.0

    def getMaximumRate(self):
        return 1.0

    def getCanGoNext(self):
        return self._hasNext()

    def getCanGoPrevious(self):
        return self._hasPrevious()

    def getCanPlay(self):
        return self.currentTrack != None

    def getCanPause(self):
        return self.currentTrack != None

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
            self.eventbox.set_visible(false)
