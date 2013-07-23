from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Gd
from gi.repository import Grl
from gi.repository import Pango
from gi.repository import GLib
from gi.repository import GdkPixbuf
from gi.repository import Tracker
from gnomemusic.grilo import grilo
import gnomemusic.widgets as Widgets
from gnomemusic.query import Query
from gnomemusic.albumArtCache import AlbumArtCache as albumArtCache
tracker = Tracker.SparqlConnection.get(None)


class ViewContainer(Gtk.Stack):
    nowPlayingIconName = 'media-playback-start-symbolic'
    errorIconName = 'dialog-error-symbolic'
    starIconName = 'starred-symbolic'
    countQuery = None

    def __init__(self, title, header_bar, selection_toolbar, useStack=False):
        Gtk.Stack.__init__(self,
                           transition_type=Gtk.StackTransitionType.CROSSFADE)
        self._grid = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL)
        self._iconWidth = -1
        self._iconHeight = 128
        self._offset = 0
        self._adjustmentValueId = 0
        self._adjustmentChangedId = 0
        self._scrollbarVisibleId = 0
        self._model = Gtk.ListStore.new([
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GdkPixbuf.Pixbuf,
            GObject.TYPE_OBJECT,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT,
            GObject.TYPE_STRING,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_BOOLEAN
        ])
        self.view = Gd.MainView(
            shadow_type=Gtk.ShadowType.NONE
        )
        self.view.set_view_type(Gd.MainViewType.ICON)
        self.view.set_model(self._model)
        self.selection_toolbar = selection_toolbar
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self.view, True, True, 0)
        if useStack:
            self.stack = Gd.Stack(
                transition_type=Gd.StackTransitionType.SLIDE_RIGHT,
            )
            dummy = Gtk.Frame(visible=False)
            self.stack.add_named(dummy, "dummy")
            self.stack.add_named(box, "artists")
            self.stack.set_visible_child_name("dummy")
            self._grid.add(self.stack)
        else:
            self._grid.add(box)

        self._loadMore = Widgets.LoadMoreButton(self._get_remaining_item_count)
        box.pack_end(self._loadMore.widget, False, False, 0)
        self._loadMore.widget.connect("clicked", self._populate)
        self.view.connect('item-activated', self._on_item_activated)
        self._cursor = None
        self.header_bar = header_bar
        self.header_bar._selectButton.connect(
            'toggled', self._on_header_bar_toggled)
        self.header_bar._cancelButton.connect(
            'clicked', self._on_cancel_button_clicked)

        self.title = title
        self.add(self._grid)

        self.show_all()
        self._items = []
        self._loadMore.widget.hide()
        self._connect_view()
        self.cache = albumArtCache.get_default()
        self._symbolicIcon = self.cache.make_default_icon(self._iconHeight,
                                                          self._iconWidth)

        self._init = False
        grilo.connect('ready', self._on_grilo_ready)
        self.header_bar.header_bar.connect('state-changed',
                                           self._on_state_changed)
        self.view.connect('view-selection-changed',
                          self._on_view_selection_changed)

    def _on_header_bar_toggled(self, button):
        if button.get_active():
            self.view.set_selection_mode(True)
            self.header_bar.set_selection_mode(True)
            self.selection_toolbar.eventbox.set_visible(True)
            self.selection_toolbar._add_to_playlist_button.sensitive = False
        else:
            self.view.set_selection_mode(False)
            self.header_bar.set_selection_mode(False)
            self.selection_toolbar.eventbox.set_visible(False)

    def _on_cancel_button_clicked(self, button):
        self.view.set_selection_mode(False)
        self.header_bar.set_selection_mode(False)

    def _on_grilo_ready(self, data=None):
        if (self.header_bar.get_stack().get_visible_child() == self
                and not self._init):
            self._populate()
        self.header_bar.get_stack().connect('notify::visible-child',
                                            self._on_headerbar_visible)

    def _on_headerbar_visible(self, widget, param):
        if self == widget.get_visible_child() and not self._init:
            self._populate()

    def _on_view_selection_changed(self, widget):
        items = self.view.get_selection()
        self.selection_toolbar\
            ._add_to_playlist_button.set_sensitive(len(items) > 0)

    def _populate(self, data=None):
        self._init = True
        self.populate()

    def _on_state_changed(self, widget, data=None):
        pass

    def _connect_view(self):
        vadjustment = self.view.get_vadjustment()
        self._adjustmentValueId = vadjustment.connect(
            'value-changed',
            self._on_scrolled_win_change)

    def _on_scrolled_win_change(self, data=None):
        vScrollbar = self.view.get_vscrollbar()
        adjustment = self.view.get_vadjustment()
        revealAreaHeight = 32

        #if there's no vscrollbar, or if it's not visible, hide the button
        if not vScrollbar or not vScrollbar.get_visible():
            self._loadMore.set_block(True)
            return

        value = adjustment.get_value()
        upper = adjustment.get_upper()
        page_size = adjustment.get_page_size()

        end = False
        #special case self values which happen at construction
        if (value == 0) and (upper == 1) and (page_size == 1):
            end = False
        else:
            end = not (value < (upper - page_size - revealAreaHeight))
        if self._get_remaining_item_count() <= 0:
            end = False
        self._loadMore.set_block(not end)

    def populate(self):
        print("populate")

    def _add_item(self, source, param, item):
        if item:
            self._offset += 1
            itr = self._model.append()
            artist = "Unknown"
            if item.get_author():
                artist = item.get_author()
            if item.get_string(Grl.METADATA_KEY_ARTIST):
                artist = item.get_string(Grl.METADATA_KEY_ARTIST)
            title = albumArtCache.get_media_title(item)
            item.set_title(title)
            try:
                if item.get_url():
                    self.player.discoverer.discover_uri(item.get_url())
                self._model.set(itr,
                                [0, 1, 2, 3, 4, 5, 7, 8, 9, 10],
                                [str(item.get_id()), "", title,
                                 artist, self._symbolicIcon, item,
                                 -1, self.nowPlayingIconName, False, False])
            except:
                print("failed to discover url " + item.get_url())
                self._model.set(iter,
                                [0, 1, 2, 3, 4, 5, 7, 8, 9, 10],
                                [str(item.get_id()), "", title,
                                 artist, self._symbolicIcon, item,
                                 -1, self.errorIconName, False, True])
        GLib.idle_add(self.show_album_art_data)

    def _get_remaining_item_count(self):
        count = -1
        if self.countQuery:
            cursor = tracker.query(self.countQuery, None)
            if cursor and cursor.next(None):
                count = cursor.get_integer(0)
        return count - self._offset

    def _update_album_art(self, item, itr):
        albumArtCache.get_default().lookup_or_resolve(
            item,
            self._iconWidth,
            self._iconHeight,
            lambda icon, data: self._model.set_value(
                itr, 4,
                albumArtCache.get_default()._make_icon_frame(icon)
                if icon else None))
        return False

    def _add_list_renderers(self):
        pass

    def _on_item_activated(self, widget, id, path):
        pass


#Class for the Empty View
class Empty(Gtk.Stack):
    def __init__(self, header_bar, player):
        Gtk.Stack.__init__(self,
                           transition_type=Gtk.StackTransitionType.CROSSFADE)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Music/NoMusic.ui')
        widget = builder.get_object('container')
        self.add(widget)
        self.show_all()


class Albums(ViewContainer):
    def __init__(self, header_bar, selection_toolbar, player):
        ViewContainer.__init__(self, "Albums", header_bar, selection_toolbar)
        self.view.set_view_type(Gd.MainViewType.ICON)
        self.countQuery = Query.ALBUMS_COUNT
        self._albumWidget = Widgets.AlbumWidget(player)
        self.add(self._albumWidget)

    def _back_button_clicked(self, widget, data=None):
        self.set_visible_child(self._grid)

    def _on_item_activated(self, widget, id, path):
        iter = self._model.get_iter(path)
        title = self._model.get_value(iter, 2)
        artist = self._model.get_value(iter, 3)
        item = self._model.get_value(iter, 5)
        self._albumWidget.update(artist, title, item,
                                 self.header_bar, self.selection_toolbar)
        self.header_bar.set_state(0)
        escaped_title = albumArtCache.get_media_title(item)
        self.header_bar.header_bar.set_title(escaped_title)
        self.header_bar.header_bar.sub_title = artist
        self.set_visible_child(self._albumWidget)

    def populate(self):
        if grilo.tracker:
            grilo.populate_albums(self._offset, self._add_item)

    def show_album_art_data(self):
        itr = self._model.get_iter_first()
        while itr:
            item = self._model.get_value(itr, 5)
            GLib.idle_add(self._update_album_art, item, itr)
            itr = self._model.iter_next(itr)


class Songs(ViewContainer):
    def __init__(self, header_bar, selection_toolbar, player):
        ViewContainer.__init__(self, "Songs", header_bar, selection_toolbar)
        self.countQuery = Query.SONGS_COUNT
        self._items = {}
        self.isStarred = None
        self.iter_to_clean = None
        self.view.set_view_type(Gd.MainViewType.LIST)
        self.view.get_generic_view().get_style_context()\
            .add_class("songs-list")
        self._iconHeight = 32
        self._iconWidth = 32
        self.cache = albumArtCache.get_default()
        self._symbolicIcon = self.cache.make_default_icon(self._iconHeight,
                                                          self._iconWidth)
        self._add_list_renderers()
        self.player = player
        self.player.connect('playlist-item-changed', self.update_model)

    def _on_item_activated(self, widget, id, path):
        itr = self._model.get_iter(path)
        if self._model.get_value(itr, 8) != self.errorIconName:
            self.player.set_playlist("Songs", None, self._model, itr, 5)
            self.player.set_playing(True)

    def update_model(self, player, playlist, currentIter):
        if self.iter_to_clean:
            self._model.set_value(self.iter_to_clean, 10, False)
        if playlist != self._model:
            return False

        self._model.set_value(currentIter, 10, True)
        if self._model.get_value(currentIter, 8) != self.errorIconName:
            self.iter_to_clean = currentIter.copy()
        return False

    def _add_item(self, source, param, item):
        if item:
            self._offset += 1
            itr = self._model.append()
            item.set_title(albumArtCache.get_media_title(item))
            try:
                if item.get_url():
                    self.player.discoverer.discover_uri(item.get_url())
                self._model.set(itr,
                                [5, 8, 9, 10],
                                [item, self.nowPlayingIconName, False, False])
            except:
                print("failed to discover url " + item.get_url())
                self._model.set(itr,
                                [5, 8, 9, 10],
                                [item, self.errorIconName, False, True])

    def _add_list_renderers(self):
        list_widget = self.view.get_generic_view()
        cols = list_widget.get_columns()
        cells = cols[0].get_cells()
        cells[2].set_visible(False)
        now_playing_symbol_renderer = Gtk.CellRendererPixbuf(xalign=1.0)

        column_now_playing = Gtk.TreeViewColumn()
        column_now_playing.set_property("fixed_width", 24)
        column_now_playing.pack_start(now_playing_symbol_renderer, False)
        column_now_playing.add_attribute(now_playing_symbol_renderer,
                                         "visible", 10)
        column_now_playing.add_attribute(now_playing_symbol_renderer,
                                         "icon_name", 8)
        list_widget.insert_column(column_now_playing, 0)

        title_renderer = Gtk.CellRendererText(xpad=0)
        list_widget.add_renderer(title_renderer,
                                 self._on_list_widget_title_render, None)

        star_renderer = Gtk.CellRendererPixbuf(xpad=32)
        list_widget.add_renderer(star_renderer,
                                 self._on_list_widget_star_render, None)

        duration_renderer = Gd.StyledTextRenderer(xpad=32)
        duration_renderer.add_class('dim-label')
        list_widget.add_renderer(duration_renderer,
                                 self._on_list_widget_duration_render, None)

        artist_renderer = Gd.StyledTextRenderer(
            xpad=32,
            ellipsize=Pango.EllipsizeMode.END
        )
        artist_renderer.add_class('dim-label')
        list_widget.add_renderer(artist_renderer,
                                 self._on_list_widget_artist_render, None)

        type_renderer = Gd.StyledTextRenderer(
            xpad=32,
            ellipsize=Pango.EllipsizeMode.END
        )
        type_renderer.add_class('dim-label')
        list_widget.add_renderer(type_renderer,
                                 self._on_list_widget_type_render, None)

    def _on_list_widget_title_render(self, col, cell, model, itr, data):
        item = model.get_value(itr, 5)
        cell.set_property("xalign", 0.0)
        cell.set_property("yalign", 0.5)
        cell.set_property("height", 48)
        cell.set_property("ellipsize", Pango.EllipsizeMode.END)
        cell.set_property("text", albumArtCache.get_media_title(item))

    def _on_list_widget_star_render(self, col, cell, model, itr, data):
        showstar = model.get_value(itr, 9)
        if(showstar):
            cell.set_property("icon_name", self.starIconName)
        else:
            cell.set_property("pixbuf", None)

    def _on_list_widget_duration_render(self, col, cell, model, itr, data):
        item = model.get_value(itr, 5)
        if item:
            seconds = item.get_duration()
            minutes = seconds // 60
            seconds %= 60
            cell.set_property("xalign", 1.0)
            cell.set_property("text", "%i:%02i" % (minutes, seconds))

    def _on_list_widget_artist_render(self, col, cell, model, itr, data):
        item = model.get_value(itr, 5)
        if item:
            cell.set_property("ellipsize", Pango.EllipsizeMode.END)
            cell.set_property("text", item.get_string(Grl.METADATA_KEY_ARTIST))

    def _on_list_widget_type_render(self, coll, cell, model, itr, data):
        item = model.get_value(itr, 5)
        if item:
            cell.set_property("ellipsize", Pango.EllipsizeMode.END)
            cell.set_property("text", item.get_string(Grl.METADATA_KEY_ALBUM))

    def populate(self):
        if grilo.tracker:
            GLib.idle_add(grilo.populate_songs, self._offset, self._add_item)


class Playlist(ViewContainer):
    def __init__(self, header_bar, selection_toolbar, player):
        ViewContainer.__init__(self, "Playlists", header_bar,
                               selection_toolbar)


class Artists (ViewContainer):
    def __init__(self, header_bar, selection_toolbar, player):
        ViewContainer.__init__(self, "Artists", header_bar,
                               selection_toolbar, True)
        self.player = player
        self._artists = {}
        self.countQuery = Query.ARTISTS_COUNT
        self._artistAlbumsWidget = Gtk.Frame(
            shadow_type=Gtk.ShadowType.NONE,
            hexpand=True
        )
        self.view.set_view_type(Gd.MainViewType.LIST)
        self.view.set_hexpand(False)
        self.view.get_style_context().add_class("artist-panel")
        self.view.get_generic_view().get_selection().set_mode(
            Gtk.SelectionMode.SINGLE)
        self._grid.attach(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL),
                          1, 0, 1, 1)
        self._grid.attach(self._artistAlbumsWidget, 2, 0, 2, 2)
        self._add_list_renderers()
        if (Gtk.Settings.get_default().get_property(
                'gtk_application_prefer_dark_theme')):
            self.view.get_generic_view().get_style_context().\
                add_class("artist-panel-dark")
        else:
            self.view.get_generic_view().get_style_context().\
                add_class("artist-panel-white")
        self.show_all()

    def _populate(self, data=None):
        selection = self.view.get_generic_view().get_selection()
        if not selection.get_selected()[1]:
            self._allIter = self._model.append()
            self._last_selection = self._allIter
            self._artists["All Artists".lower()] =\
                {"iter": self._allIter, "albums": []}
            self._model.set(self._allIter, 2, "All Artists")
            selection.select_path(self._model.get_path(self._allIter))
            self.view.emit('item-activated', "0",
                           self._model.get_path(self._allIter))
        self._init = True
        self.populate()

    def _add_list_renderers(self):
        list_widget = self.view.get_generic_view()

        cols = list_widget.get_columns()
        cells = cols[0].get_cells()
        cells[1].set_visible(False)
        cells[2].set_visible(False)
        type_renderer = Gd.StyledTextRenderer(
            xpad=16,
            ypad=16,
            ellipsize=Pango.EllipsizeMode.END,
            xalign=0.0,
            width=220
        )
        list_widget.add_renderer(type_renderer, lambda *args: None, None)
        cols[0].clear_attributes(type_renderer)
        cols[0].add_attribute(type_renderer, "text", 2)

    def _on_item_activated(self, widget, item_id, path):
        children = self._artistAlbumsWidget.get_children()
        for child in children:
            self._artistAlbumsWidget.remove(child)
        itr = self._model.get_iter(path)
        self._last_selection = itr
        artist = self._model.get_value(itr, 2)
        albums = self._artists[artist.lower()]["albums"]
        self.artistAlbums = None
        if (self._model.get_string_from_iter(itr) ==
                self._model.get_string_from_iter(self._allIter)):
            self.artistAlbums = Widgets.AllArtistsAlbums(self.player)
        else:
            self.artistAlbums = Widgets.ArtistAlbums(artist, albums,
                                                     self.player)
        self._artistAlbumsWidget.add(self.artistAlbums)

    def _add_item(self, source, param, item):
        self._offset += 1
        if item is None:
            return
        artist = "Unknown"
        if item.get_author():
            artist = item.get_author()
        if item.get_string(Grl.METADATA_KEY_ARTIST):
            artist = item.get_string(Grl.METADATA_KEY_ARTIST)
        if not artist.lower() in self._artists:
            itr = self._model.append()
            self._artists[artist.lower()] = {"iter": itr, "albums": []}
            self._model.set(itr, 2, artist)

        self._artists[artist.lower()]["albums"].append(item)

    def populate(self):
        if grilo.tracker:
            GLib.idle_add(grilo.populate_artists, self._offset, self._add_item)

    def _on_header_bar_toggled(self, button):
        ViewContainer._on_header_bar_toggled(self, button)

        if button.get_active():
            self._last_selection =\
                self.view.get_generic_view().get_selection().get_selected()[1]
            self.view.get_generic_view().get_selection().set_mode(
                Gtk.SelectionMode.NONE)
        else:
            self.view.get_generic_view().get_selection().set_mode(
                Gtk.SelectionMode.SINGLE)
            if self._last_selection is not None:
                self.view.get_generic_view().get_selection().select_iter(
                    self._last_selection)
