from gi.repository import Gtk, Gd, GLib, GObject, Grl, Pango
from gi.repository import GdkPixbuf
from gnomemusic.grilo import grilo
import logging
from gnomemusic.query import Query
from gnomemusic.albumArtCache import AlbumArtCache
ALBUM_ART_CACHE = AlbumArtCache.getDefault()

NOW_PLAYING_ICON_NAME = 'media-playback-start-symbolic'
ERROR_ICON_NAME = 'dialog-error-symbolic'


class LoadMoreButton:
    def __init__(self, counter):
        self._block = False
        self._counter = counter
        child = Gtk.Grid(column_spacing=10,
                         hexpand=False,
                         halign=Gtk.Align.CENTER,
                         visible=True)
        self._spinner = Gtk.Spinner(halign=Gtk.Align.CENTER,
                                    no_show_all=True)
        self._spinner.set_size_request(16, 16)
        child.add(self._spinner)
        self._label = Gtk.Label(label="Load More",
                                visible=True)
        child.add(self._label)
        self.widget = Gtk.Button(no_show_all=True,
                                 child=child)
        self.widget.get_style_context().add_class('documents-load-more')
        self.widget.connect('clicked', self._onLoadMoreClicked)
        self._onItemCountChanged()

    def _onLoadMoreClicked(self, data=None):
        self._label.label = "Loading..."
        self._spinner.show()
        self._spinner.start()

    def _onItemCountChanged(self):
        remainingDocs = self._counter()
        visible = remainingDocs <= 0 or self._block
        self.widget.set_visible(visible)

        if visible:
            self._label.label = "Load More"
            self._spinner.stop()
            self._spinner.hide()

    def setBlock(self, block):
        if (self._block == block):
            return

        self._block = block
        self._onItemCountChanged()


class AlbumWidget(Gtk.EventBox):
    def __init__(self, player):
        super()
        self.player = player
        self.hbox = Gtk.HBox()
        self.iterToClean = None
        self.cache = AlbumArtCache.getDefault()
        self._symbolicIcon = self.cache.makeDefaultIcon(256, 256)

        self.ui = Gtk.Builder()
        self.ui.add_from_resource('/org/gnome/music/AlbumWidget.ui')
        self.model = Gtk.ListStore(
            GObject.TYPE_STRING,  # title
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GdkPixbuf.Pixbuf,    # icon
            GObject.TYPE_OBJECT,  # song object
            GObject.TYPE_BOOLEAN,  # item selected
            GObject.TYPE_STRING,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_BOOLEAN,  # icon shown
        )

        self.view = Gd.MainView(
            shadow_type=Gtk.ShadowType.NONE
        )
        self.view.set_view_type(Gd.MainViewType.LIST)
        self.album = None
        self.view.connect('item-activated', self._onItemActivated)

        view_box = self.ui.get_object("view")
        child_view = self.view.get_children()[0]
        child_view.set_margin_top(64)
        child_view.set_margin_bottom(64)
        child_view.set_margin_right(32)
        self.view.remove(child_view)
        view_box.add(child_view)

        self.add(self.ui.get_object("AlbumWidget"))
        self._addListRenderers()
        # TODO: make this work
        #self.get_style_context().add_class("view")
        #self.get_style_context().add_class("content-view")
        self.show_all()

    def _onItemActivated(self, widget, id, path):
        iter = self.model.get_iter(path)[1]
        if(self.model.get_value(iter, 7) != ERROR_ICON_NAME):
            if (self.iterToClean and self.player.playlistId == self.album):
                item = self.model.get_value(self.iterToClean, 5)
                self.model.set_value(self.iterToClean, 0, item.get_title())
                #Hide now playing icon
                self.model.set_value(self.iterToClean, 6, False)
            self.player.setPlaylist("Album", self.album, self.model, iter, 5)
            self.player.setPlaying(True)

    def _addListRenderers(self):
        listWidget = self.view.get_generic_view()

        cols = listWidget.get_columns()
        cols[0].set_min_width(310)
        cols[0].set_max_width(470)
        cells = cols[0].get_cells()
        cells[2].visible = False
        cells[1].visible = False

        nowPlayingSymbolRenderer = Gtk.CellRendererPixbuf(xpad=0)

        columnNowPlaying = Gtk.TreeViewColumn()
        nowPlayingSymbolRenderer.xalign = 1.0
        nowPlayingSymbolRenderer.yalign = 0.6
        columnNowPlaying.pack_start(nowPlayingSymbolRenderer, False)
        columnNowPlaying.fixed_width = 24
        columnNowPlaying.add_attribute(nowPlayingSymbolRenderer, "visible", 9)
        columnNowPlaying.add_attribute(nowPlayingSymbolRenderer, "icon_name",
                                       7)
        listWidget.insert_column(columnNowPlaying, 0)

        typeRenderer = Gd.StyledTextRenderer(xpad=16)
        typeRenderer.ellipsize = Pango.EllipsizeMode.END
        typeRenderer.xalign = 0.0
        listWidget.add_renderer(typeRenderer, self._typeRendererText, None)
        cols[0].clear_attributes(typeRenderer)
        cols[0].add_attribute(typeRenderer, "markup", 0)

        durationRenderer = Gd.StyledTextRenderer(xpad=16)
        durationRenderer.add_class('dim-label')
        durationRenderer.ellipsize = Pango.EllipsizeMode.END
        durationRenderer.xalign = 1.0
        listWidget.add_renderer(durationRenderer, self._durationRendererText, None)

    def _typeRendererText(self, col, cell, model, iter):
        pass

    def _durationRendererText(self):
        item = self.model.get_value(iter, 5)
        duration = item.get_duration()
        if item is None:
            return
        self.durationRenderer.text = self.player.secondsToString(duration)

    def update(self, artist, album, item, header_bar, selection_toolbar):
        released_date = item.get_publication_date()
        if released_date is not None:
            self.ui.get_object("released_label_info").set_text(
                released_date.get_year().toString())
        self.album = album
        self.ui.get_object("cover").set_from_pixbuf(self._symbolicIcon)
        ALBUM_ART_CACHE.lookup(256, artist,
                               item.get_string(Grl.METADATA_KEY_ALBUM),
                               self._onLookUp)

        # if the active queue has been set by self album,
        # use it as model, otherwise build the liststore
        cachedPlaylist = self.player.runningPlaylist("Album", album)
        if cachedPlaylist is not None:
            self.model = cachedPlaylist
            self.updateModel(self.player, cachedPlaylist,
                             self.player.currentTrack)
        else:
            self.model = Gtk.ListStore(
                GObject.TYPE_STRING,  # title
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
                GObject.TYPE_STRING,
                GdkPixbuf.Pixbuf,    # icon
                GObject.TYPE_OBJECT,  # song object
                GObject.TYPE_BOOLEAN,  # icon shown
                GObject.TYPE_STRING,
                GObject.TYPE_BOOLEAN,
                GObject.TYPE_BOOLEAN,
            )
            grilo.getAlbumSongs(item.get_id(), self._onGetAlbumSongs)
        header_bar._selectButton.connect(
            'toggled',
            self._onHeaderSelectButtonToggled(self.button))
        header_bar._cancelButton.connect(
            'clicked',
            self._onHeaderCancelButtonClicked(self.button))
        self.view.connect('view-selection-changed',
                          self._onViewSelectionChanged())
        self.view.set_model(self.model)
        escapedArtist = GLib.markup_escape_text(artist, -1)
        escapedAlbum = GLib.markup_escape_text(album, -1)
        self.ui.get_object("artist_label").set_markup(escapedArtist)
        self.ui.get_object("title_label").set_markup(escapedAlbum)
        if (item.get_creation_date()):
            self.ui.get_object("released_label_info").set_text(
                item.get_creation_date().get_year().toString())
        else:
            self.ui.get_object("released_label_info").set_text("----")
        self.player.connect('playlist-item-changed', self.updateModel())
        self.emit('loaded')

    def _onViewSelectionChanged(self):
        items = self.view.get_selection()
        self.selection_toolbar._add_to_playlist_button.sensitive = items.length

    def _onHeaderCancelButtonClicked(self, button):
        self.view.set_selection_mode(False)
        self.header_bar.setSelectionMode(False)
        self.header_bar.header_bar.title = self.album

    def _onHeaderSelectButtonToggled(self, button):
        if(button.get_active()):
            self.view.set_selection_mode(True)
            self.header_bar.setSelectionMode(True)
            self.player.eventBox.set_visible(False)
            self.selection_toolbar.eventbox.set_visible(True)
            self.selection_toolbar._add_to_playlist_button.sensitive = False
        else:
            self.view.set_selection_mode(False)
            self.header_bar.setSelectionMode(False)
            self.header_bar.title = self.album
            self.selection_toolbar.eventbox.set_visible(False)
            if(self.player.PlaybackStatus != 'Stopped'):
                self.player.eventBox.set_visible(True)

    def _onGetAlbumSongs(self, source, prefs, track):
        if track is not None:
            self.tracks.push(track)
            self.duration = self.duration + track.get_duration()
            iter = self.model.append()
            escapedTitle = GLib.markup_escape_text(track.get_title(), -1)
            try:
                self.player.discoverer.discover_uri(track.get_url())
                self.model.set(iter,
                               [0, 1, 2, 3, 4, 5, 7, 9],
                               [escapedTitle, "", "", "",
                                self._symbolicIcon, track,
                                NOW_PLAYING_ICON_NAME, False])
            except IOError as err:
                logging.debug(err.message)
                logging.debug("failed to discover url " + track.get_url())
                self.model.set(iter,
                               [0, 1, 2, 3, 4, 5, 7, 9],
                               [escapedTitle, "", "", "", self._symbolicIcon,
                                track, True, ERROR_ICON_NAME, False])
            self.ui.get_object("running_length_label_info").set_text(
                (int(self.duration / 60) + 1) + " min")
            self.emit("track-added")

    def _onLookUp(self, pixbuf):
        if pixbuf is not None:
            self.ui.get_object("cover").set_from_pixbuf(pixbuf)
            self.model.set(iter, [4], [pixbuf])

    def updateModel(self, player, playlist, currentIter):
        #self is not our playlist, return
        if (playlist != self.model):
            return False
        currentSong = playlist.get_value(currentIter, 5)
        [res, iter] = playlist.get_iter_first()
        if res is not None:
            return False
        songPassed = False
        while True:
            song = playlist.get_value(iter, 5)

            escapedTitle = GLib.markup_escape_text(song.get_title(), -1)
            if (song == currentSong):
                title = "<b>" + escapedTitle + "</b>"
                iconVisible = True
                songPassed = True
            elif (songPassed):
                title = "<span>" + escapedTitle + "</span>"
                iconVisible = False
            else:
                title = "<span color='grey'>" + escapedTitle + "</span>"
                iconVisible = False
            playlist.set_value(iter, 0, title)
            playlist.set_value(iter, 9, iconVisible)
            if playlist.iter_next(iter) is None:
                break
        return False


class ArtistAlbums(Gtk.VBox):
    def __init__(self, artist, albums, player):
        self.player = player
        self.artist = artist
        self.albums = albums
        self.ui = Gtk.Builder()
        self.ui.add_from_resource('/org/gnome/music/ArtistAlbumsWidget.ui')
        self.set_border_width(0)
        self.ui.get_object("artist").set_label(self.artist)
        self.widgets = []

        self.model = Gtk.ListStore.new([GObject.TYPE_STRING,   # title
                                        GObject.TYPE_STRING,
                                        GObject.TYPE_STRING,
                                        GObject.TYPE_BOOLEAN,  # icon shown
                                        GObject.TYPE_STRING,   # icon
                                        GObject.TYPE_OBJECT,   # song object
                                        GObject.TYPE_BOOLEAN
                                        ])

        self._hbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._albumBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                 spacing=48)
        self._scrolledWindow = Gtk.ScrolledWindow()
        self._scrolledWindow.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC)
        self._scrolledWindow.add(self._hbox)
        self._hbox.pack_start(self.ui.get_object('ArtistAlbumsWidget'),
                              False, False, 0)
        self._hbox.pack_start(self._albumBox, False, False, 16)
        self.pack_start(self._scrolledWindow, True, True, 0)

        for i in albums.length:
            self.addAlbum(albums[i])

        self.show_all()
        self.player.connect('playlist-item-changed', self.updateModel)
        self.emit("albums-loaded")

    def addAlbum(self, album):
        widget = ArtistAlbumWidget(self.artist, album, self.player, self.model)
        self._albumBox.pack_start(widget, False, False, 0)
        self.widgets.push(widget)

    def cleanModel(self):
        [res, iter] = self.model.get_iter_first()
        if not res:
            return False
        while self.model.iter_next(iter) is True:
            song = self.model.get_value(iter, 5)
            songWidget = song.songWidget
            escapedTitle = GLib.markup_escape_text(song.get_title(), -1)
            if songWidget.can_be_played is not None:
                songWidget.nowPlayingSign.hide()
            songWidget.title.set_markup("<span>" + escapedTitle + "</span>")
        return False


class AllArtistsAlbums(ArtistAlbums):

    def __init__(self, player):
        ArtistAlbums.__init__("All Artists", [], player)
        self._offset = 0
        self.countQuery = Query.album_count
        self._loadMore = LoadMoreButton(self, self._getRemainingItemCount)
        self.pack_end(self._loadMore.widget, False, False, 0)
        self._loadMore.widget.connect("clicked", self._populate)
        self._connectView()
        self._populate()

    def _connectView(self):
        self._adjustmentValueId = self._scrolledWindow.vadjustment.connect(
            'value-changed', self._onScrolledWinChange)
        self._adjustmentChangedId = self._scrolledWindow.vadjustment.connect(
            'changed', self._onScrolledWinChange)
        self._scrollbarVisibleId = self._scrolledWindow.get_vscrollbar().connect('notify::visible', self._onScrolledWinChange)
        self._onScrolledWinChange()

    def _onScrolledWinChange(self, data=None):
        vScrollbar = self._scrolledWindow.get_vscrollbar()
        adjustment = self._scrolledWindow.vadjustment
        revealAreaHeight = 32

        # if there's no vscrollbar, or if it's not visible, hide the button
        if not vScrollbar or not vScrollbar.get_visible():
            self._loadMore.setBlock(True)
            return

        value = adjustment.value
        upper = adjustment.upper
        page_size = adjustment.page_size
        end = False
        # special case self values which happen at construction
        if (value == 0) and (upper == 1) and (page_size == 1):
            end = False
        else:
            end = not (value < (upper - page_size - revealAreaHeight))
        if self._getRemainingItemCount() <= 0:
            end = False
        self._loadMore.setBlock(not end)

    def _populate(self):
        if grilo.tracker is not None:
            grilo.populateAlbums(self._offset, self.addItem, 5)

    def addItem(self, source, param, item, remaining):
        if item is not None:
            self._offset = self.offset + 1
            self.addAlbum(item)

    def _getRemainingItemCount(self):
        count = -1
        if self.countQuery is not None:
            cursor = grilo.tracker.query(self.countQuery, None)
            if cursor is not None and cursor.next(None):
                count = cursor.get_integer(0)
        return (count - self._offset)


class ArtistAlbumWidget(Gtk.HBox):

    def __init__(self, artist, album, player, model):
        self.player = player
        self.album = album
        self.artist = artist
        self.model = model
        self.songs = []

        self.ui = Gtk.Builder()
        self.ui.add_from_resource('/org/gnome/music/ArtistAlbumWidget.ui')

        self.cache = AlbumArtCache.getDefault()
        pixbuf = self.cache.makeDefaultIcon(128, 128)
        GLib.idle_add(self._updateAlbumArt)

        self.ui.get_object("cover").set_from_pixbuf(pixbuf)
        self.ui.get_object("title").set_label(album.get_title())
        if album.get_creation_date() is not None:
            self.ui.get_object("year").set_markup(
                "<span color='grey'>(" +
                album.get_creation_date().get_year() + ")</span>"
            )
        self.tracks = []
        grilo.getAlbumSongs(album.get_id(), self.getSongs)
        self.pack_start(self.ui.get_object("ArtistAlbumWidget"), True, True, 0)
        self.show_all()
        self.emit("artist-album-loaded")

    def getSongs(self, source, prefs, track):
        if track is not None:
            self.tracks.push(track)

        else:
            for i in self.tracks.length:
                track = self.tracks[i]
                ui = Gtk.Builder()
                ui.add_from_resource('/org/gnome/music/TrackWidget.ui')
                songWidget = ui.get_object("eventbox1")
                self.songs.push(songWidget)
                ui.get_object("num").set_markup("<span color='grey'>"
                                                + self.songs.length.toString()
                                                + "</span>")
                if track.get_title() is not None:
                    ui.get_object("title").set_text(track.get_title())
                ui.get_object("title").set_alignment(0.0, 0.5)
                self.ui.get_object("grid1").attach(
                    songWidget,
                    int(i / (self.tracks.length / 2)),
                    int((i) % (self.tracks.length / 2)), 1, 1
                )
                track.songWidget = songWidget
                iter = self.model.append()
                songWidget.iter = iter
                songWidget.model = self.model
                songWidget.title = ui.get_object("title")

                try:
                    self.player.discoverer.discover_uri(track.get_url())
                    self.model.set(iter,
                                   [0, 1, 2, 3, 4, 5],
                                   [track.get_title(), "", "", False,
                                    NOW_PLAYING_ICON_NAME, track])
                    songWidget.nowPlayingSign = ui.get_object("image1")
                    songWidget.nowPlayingSign.set_from_icon_name(
                        NOW_PLAYING_ICON_NAME,
                        Gtk.IconSize.SMALL_TOOLBAR)
                    songWidget.nowPlayingSign.set_no_show_all("true")
                    songWidget.nowPlayingSign.set_alignment(0.0, 0.6)
                    songWidget.can_be_played = True
                    songWidget.connect('button-release-event',
                                       self.trackSelected)

                except IOError as err:
                    print(err.message)
                    print("failed to discover url " + track.get_url())
                    self.model.set(iter, [0, 1, 2, 3, 4, 5],
                                   [track.get_title(), "", "", True,
                                    ERROR_ICON_NAME, track])
                    songWidget.nowPlayingSign = ui.get_object("image1")
                    songWidget.nowPlayingSign.set_from_icon_name(
                        ERROR_ICON_NAME,
                        Gtk.IconSize.SMALL_TOOLBAR)
                    songWidget.nowPlayingSign.set_alignment(0.0, 0.6)
                    songWidget.can_be_played = False
            self.ui.get_object("grid1").show_all()
            self.emit("tracks-loaded")

    def _updateAlbumArt(self):
        ALBUM_ART_CACHE.lookup(128, self.artist,
                               self.album.get_title(), self.getAlbumCover)

    def getAlbumCover(self, pixbuf):
        if pixbuf is not None:
            self.ui.get_object("cover").set_from_pixbuf(pixbuf)
        else:
            options = Grl.OperationOptions.new(None)
            options.set_flags(Grl.ResolutionFlags.FULL
                              | Grl.ResolutionFlags.IDLE_RELAY)
            grilo.tracker.resolve(self.album,
                                  [Grl.METADATA_KEY_THUMBNAIL],
                                  options, self.loadCover)

    def loadCover(self, source, param, item):
        uri = self.album.get_thumbnail()
        ALBUM_ART_CACHE.getFromUri(uri, self.artist,
                                   self.album.get_title(), 128, 128,
                                   self.getCover)

    def getCover(self, pixbuf):
        pixbuf = ALBUM_ART_CACHE.makeIconFrame(pixbuf)
        self.ui.get_object("cover").set_from_pixbuf(pixbuf)

    def trackSelected(self, widget, iter):
        self.player.stop()
        self.player.setPlaylist("Artist", self.album,
                                widget.model, widget.iter, 5)
        self.player.setPlaying(True)
