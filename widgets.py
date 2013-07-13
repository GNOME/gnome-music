from gi.repository import Gtk, Gdk, Gd, Gio, GLib, GObject, Grl, Pango
from gi.repository import GdkPixbuf
import query
import grilo
import signals
from albumArtCache import *
import logging
ALBUM_ART_CACHE = AlbumArtCache.AlbumArtCache.getDefault()

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
        self.widget.connect('clicked', self._onLoadMoreClicked())
        self._onItemCountChanged()

    def _onLoadMoreClicked(self):
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
        self.player = player
        self.hbox = Gtk.HBox()
        self.iterToClean = None
        self._symbolicIcon = albumArtCache.makeDefaultIcon(256, 256)

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
        self.view.connect('item-activated', self._onItemActivated(widget, id,
                          path))

        self.super()

        view_box = self.ui.get_object("view")
        child_view = self.view.get_children()[0]
        child_view.set_margin_top(64)
        child_view.set_margin_bottom(64)
        child_view.set_margin_right(32)
        self.view.remove(child_view)
        view_box.add(child_view)

        self.add(self.ui.get_object("AlbumWidget"))
        self._addListRenderers()
        self.get_style_context().add_class("view")
        self.get_style_context().add_class("content-view")
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
        # self function is not needed, just add the renderer!
        listWidget.add_renderer(typeRenderer)
        cols[0].clear_attributes(typeRenderer)
        cols[0].add_attribute(typeRenderer, "markup", 0)

        durationRenderer = Gd.StyledTextRenderer(xpad=16)
        durationRenderer.add_class('dim-label')
        durationRenderer.ellipsize = Pango.EllipsizeMode.END
        durationRenderer.xalign = 1.0
        listWidget.add_renderer(durationRenderer, self._durationRendererText())

    def _durationRendererText(self):
        item = model.get_value(iter, 5)
        duration = item.get_duration()
        if item is None:
            return
        durationRenderer.text = self.player.secondsToString(duration)

    def update(self, artist, album, item, header_bar, selection_toolbar):
        released_date = item.get_publication_date()
        if released_date is not None:
            self.ui.get_object("released_label_info").set_text(
                released_date.get_year().toString())
        duration = 0
        self.album = album
        self.ui.get_object("cover").set_from_pixbuf(self._symbolicIcon)
        albumArtCache.lookup(256, artist,
                             item.get_string(Grl.METADATA_KEY_ALBUM),
                             self._onLookUp(pixbuf))

        # if the active queue has been set by self album,
        # use it as model, otherwise build the liststore
        cachedPlaylist = self.player.runningPlaylist("Album", album)
        if cachedPlaylist is not None:
            self.model = cachedPlaylist
            self.updateModel(self.player, cachedPlaylist,
                             self.player.currentTrack)
        else:
            self.model = Gtk.ListStore([
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
            ])
            tracks = []
            grilo.getAlbumSongs(item.get_id(), self._onGetAlbumSongs(source,
                                                                     prefs,
                                                                     track))
        header_bar._selectButton.connect(
            'toggled',
            self._onHeaderSelectButtonToggled(button))
        header_bar._cancelButton.connect(
            'clicked',
            self._onHeaderCancelButtonClicked(button))
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
        selection_toolbar._add_to_playlist_button.sensitive = items.length > 0

    def _onHeaderCancelButtonClicked(self, button):
        self.view.set_selection_mode(False)
        self.header_bar.setSelectionMode(False)
        self.header_bar.header_bar.title = self.album

    def _onHeaderSelectButtonToggled(self, button):
        if(button.get_active()):
                self.view.set_selection_mode(True)
                header_bar.setSelectionMode(True)
                self.player.eventBox.set_visible(False)
                selection_toolbar.eventbox.set_visible(True)
                selection_toolbar._add_to_playlist_button.sensitive = False
        else:
            self.view.set_selection_mode(False)
            header_bar.setSelectionMode(False)
            header_bar.title = self.album
            selection_toolbar.eventbox.set_visible(False)
            if(self.player.PlaybackStatus != 'Stopped'):
                self.player.eventBox.set_visible(True)

    def _onGetAlbumSongs(self, source, prefs, track):
        if track is not None:
            tracks.push(track)
            duration = duration + track.get_duration()
            iter = self.model.append()
            escapedTitle = GLib.markup_escape_text(track.get_title(), -1)
            try:
                self.player.discoverer.discover_uri(track.get_url())
                self.model.set(iter,
                               [0, 1, 2, 3, 4, 5, 7, 9],
                               [escapedTitle, "", "", "",
                               self._symbolicIcon, track,
                               nowPlayingIconName, False])
            except IOError as err:
                logging.debug(err.message)
                logging.debug("failed to discover url " + track.get_url())
                self.model.set(iter,
                               [0, 1, 2, 3, 4, 5, 7, 9],
                               [escapedTitle, "", "", "", self._symbolicIcon,
                                track, True, errorIconName, False])
            self.ui.get_object("running_length_label_info").set_text(
                (parseInt(duration / 60) + 1) + " min")
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
        iconVisible, title
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
