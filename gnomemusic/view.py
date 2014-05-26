# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Eslam Mostafa <cseslam@gmail.com>
# Copyright (c) 2013 Sai Suman Prayaga <suman.sai14@gmail.com>
# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Shivani Poddar <shivani.poddar92@gmail.com>
# Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
# Copyright (c) 2013 Giovanni Campagna <scampa.giovanni@gmail.com>
# Copyright (c) 2013 Jackson Isaac <jacksonisaac2008@gmail.com>
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


from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Gd
from gi.repository import Grl
from gi.repository import Pango
from gi.repository import GLib
from gi.repository import GdkPixbuf
from gi.repository import Tracker
from gi.repository import Gio

from gettext import gettext as _, ngettext
from gnomemusic.grilo import grilo
from gnomemusic.toolbar import ToolbarState
import gnomemusic.widgets as Widgets
from gnomemusic.playlists import Playlists
from gnomemusic.query import Query
from gnomemusic.albumArtCache import AlbumArtCache as albumArtCache
from gnomemusic import log
import logging
logger = logging.getLogger(__name__)

try:
    tracker = Tracker.SparqlConnection.get(None)
except Exception as e:
    from sys import exit
    logger.error("Cannot connect to tracker, error '%s'\Exiting" % str(e))
    exit(1)

playlists = Playlists.get_default()

if Gtk.get_minor_version() > 8:
    from gi.repository.Gtk import Stack, StackTransitionType
else:
    from gi.repository.Gd import Stack, StackTransitionType


class ViewContainer(Stack):
    if Gtk.Widget.get_default_direction() is not Gtk.TextDirection.RTL:
        nowPlayingIconName = 'media-playback-start-symbolic'
    else:
        nowPlayingIconName = 'media-playback-start-rtl-symbolic'
    errorIconName = 'dialog-error-symbolic'
    starIconName = 'starred-symbolic'
    countQuery = None
    filter = None

    @log
    def __init__(self, title, header_bar, selection_toolbar, view_type, use_sidebar=False, sidebar=None):
        Stack.__init__(self,
                       transition_type=StackTransitionType.CROSSFADE)
        self._grid = Gtk.Grid(orientation=Gtk.Orientation.HORIZONTAL)
        self._iconWidth = 128
        self._iconHeight = 128
        self._offset = 0
        self._adjustmentValueId = 0
        self._adjustmentChangedId = 0
        self._scrollbarVisibleId = 0
        self._model = Gtk.ListStore(
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
        )
        self.view = Gd.MainView(
            shadow_type=Gtk.ShadowType.NONE
        )
        self.view.set_view_type(view_type)
        self.filter = self._model.filter_new(None)
        self.view.set_model(self.filter)
        self.vadjustment = self.view.get_vadjustment()
        self.selection_toolbar = selection_toolbar
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self.view, True, True, 0)
        if use_sidebar:
            self.stack = Stack(
                transition_type=StackTransitionType.SLIDE_RIGHT,
            )
            dummy = Gtk.Frame(visible=False)
            self.stack.add_named(dummy, 'dummy')
            if sidebar:
                self.stack.add_named(sidebar, 'sidebar')
            else:
                self.stack.add_named(box, 'sidebar')
            self.stack.set_visible_child_name('dummy')
            self._grid.add(self.stack)
        if not use_sidebar or sidebar:
            self._grid.add(box)

        self._cached_count = -1
        self._loadMore = Widgets.LoadMoreButton(self._get_remaining_item_count)
        box.pack_end(self._loadMore.widget, False, False, 0)
        self._loadMore.widget.connect('clicked', self._populate)
        self.view.connect('item-activated', self._on_item_activated)
        self._cursor = None
        self.header_bar = header_bar
        self.header_bar._select_button.connect(
            'toggled', self._on_header_bar_toggled)
        self.header_bar._cancel_button.connect(
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
        self.header_bar.connect('selection-mode-changed',
                                self._on_selection_mode_changed)
        self.view.connect('view-selection-changed',
                          self._on_view_selection_changed)

        self._discovering_urls = {}
        grilo.connect('changes-pending', self._on_changes_pending)

    @log
    def _on_changes_pending(self, data=None):
        pass

    @log
    def _get_remaining_item_count(self):
        if self._cached_count < 0:
            self._cached_count = Widgets.get_count(self.countQuery)
        return self._cached_count - self._offset

    @log
    def _on_header_bar_toggled(self, button):
        if button.get_active():
            self.view.set_selection_mode(True)
            self.header_bar.set_selection_mode(True)
            self.selection_toolbar.eventbox.set_visible(True)
            self.selection_toolbar._add_to_playlist_button.set_sensitive(False)
            self.selection_toolbar._remove_from_playlist_button.set_sensitive(False)
        else:
            self.view.set_selection_mode(False)
            self.header_bar.set_selection_mode(False)
            self.selection_toolbar.eventbox.set_visible(False)

    @log
    def _on_cancel_button_clicked(self, button):
        self.view.set_selection_mode(False)
        self.header_bar.set_selection_mode(False)

    @log
    def _on_grilo_ready(self, data=None):
        if (self.header_bar.get_stack().get_visible_child() == self
                and not self._init):
            self._populate()
        self.header_bar.get_stack().connect('notify::visible-child',
                                            self._on_headerbar_visible)

    @log
    def _on_headerbar_visible(self, widget, param):
        if self == widget.get_visible_child() and not self._init:
            self._populate()

    @log
    def _on_view_selection_changed(self, widget):
        items = self.view.get_selection()
        self.selection_toolbar._add_to_playlist_button.\
            set_sensitive(len(items) > 0)
        self.selection_toolbar._remove_from_playlist_button.\
            set_sensitive(len(items) > 0)
        if len(items) > 0:
            self.header_bar._selection_menu_label.set_text(
                ngettext("Selected %d item", "Selected %d items", len(items)) % len(items))
        else:
            self.header_bar._selection_menu_label.set_text(_("Click on items to select them"))

    @log
    def _populate(self, data=None):
        self._init = True
        self.populate()

    @log
    def _on_state_changed(self, widget, data=None):
        pass

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        pass

    @log
    def _connect_view(self):
        self._adjustmentValueId = self.vadjustment.connect(
            'value-changed',
            self._on_scrolled_win_change)

    @log
    def _on_scrolled_win_change(self, data=None):
        vScrollbar = self.view.get_vscrollbar()
        revealAreaHeight = 32

        # if there's no vscrollbar, or if it's not visible, hide the button
        if not vScrollbar or not vScrollbar.get_visible():
            self._loadMore.set_block(True)
            return

        value = self.vadjustment.get_value()
        upper = self.vadjustment.get_upper()
        page_size = self.vadjustment.get_page_size()

        end = False
        # special case self values which happen at construction
        if (value == 0) and (upper == 1) and (page_size == 1):
            end = False
        else:
            end = not (value < (upper - page_size - revealAreaHeight))
        if self._get_remaining_item_count() <= 0:
            end = False
        self._loadMore.set_block(not end)

    @log
    def populate(self):
        print('populate')

    @log
    def _on_discovered(self, info, error, _iter):
        if error:
            print("Info %s: error: %s" % (info, error))
            self._model.set(_iter, [8, 10], [self.errorIconName, True])

    @log
    def _add_item(self, source, param, item, remaining):
        if not item:
            return
        self._offset += 1
        artist = item.get_string(Grl.METADATA_KEY_ARTIST)\
            or item.get_author()\
            or _("Unknown Artist")
        title = albumArtCache.get_media_title(item)
        item.set_title(title)

        def add_new_item():
            _iter = self._model.append(None)
            icon_name = self.nowPlayingIconName
            if item.get_url():
                try:
                    self.player.discoverer.discover_uri(item.get_url())
                except:
                    print('failed to discover url ' + item.get_url())
                    icon_name = self.errorIconName
            self._model.set(_iter,
                            [0, 1, 2, 3, 4, 5, 7, 8, 9, 10],
                            [str(item.get_id()), '', title,
                             artist, self._symbolicIcon, item,
                             0, icon_name, False, icon_name == self.errorIconName])
            GLib.idle_add(self._update_album_art, item, _iter)

        GLib.idle_add(add_new_item)

    @log
    def _insert_album_art(self, item, cb_item, itr, x=False):
        if item and cb_item and not item.get_thumbnail():
            if cb_item.get_thumbnail():
                item.set_thumbnail(cb_item.get_thumbnail())
            albumArtCache.get_default().lookup(
                item,
                self._iconWidth,
                self._iconHeight,
                self._on_lookup_ready, itr)

    @log
    def _update_album_art(self, item, itr):
        grilo.get_album_art_for_album_id(
            item.get_id(),
            lambda source, count, cb_item, x, y, z:
            self._insert_album_art(item, cb_item, itr, True)
        )

    @log
    def _on_lookup_ready(self, icon, path, _iter):
        if icon:
            self._model.set_value(
                _iter, 4,
                albumArtCache.get_default()._make_icon_frame(icon))
            self.view.queue_draw()

    @log
    def _add_list_renderers(self):
        pass

    @log
    def _on_item_activated(self, widget, id, path):
        pass

    @log
    def _on_selection_mode_request(self, *args):
        self.header_bar._select_button.clicked()

    @log
    def get_selected_track_uris(self, callback):
        callback([])


# Class for the Empty View
class Empty(Stack):
    @log
    def __init__(self, header_bar, player):
        Stack.__init__(self,
                       transition_type=StackTransitionType.CROSSFADE)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Music/NoMusic.ui')
        music_folder_path = GLib.get_user_special_dir(GLib.USER_DIRECTORY_MUSIC)
        widget = builder.get_object('container')
        label = builder.get_object('label1')
        label.set_label(_("No Music found!\n Put some files into the folder %s") % music_folder_path)
        self.add(widget)
        self.show_all()


class Albums(ViewContainer):
    @log
    def __init__(self, header_bar, selection_toolbar, player):
        ViewContainer.__init__(self, _("Albums"), header_bar,
                               selection_toolbar, Gd.MainViewType.ICON)
        self.countQuery = Query.get_albums_count()
        self._albumWidget = Widgets.AlbumWidget(player)
        self.player = player
        self.add(self._albumWidget)
        self.albums_selected = []
        self.items_selected = []
        self.items_selected_callback = None

    @log
    def _on_changes_pending(self, data=None):
        if (self._init and self.header_bar._selectionMode is False):
            self._offset = 0
            self._cached_count = -1
            self._model.clear()
            self.populate()
            grilo.changes_pending['Albums'] = False

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        if self.header_bar._selectionMode is False and grilo.changes_pending['Albums'] is True:
            self._on_changes_pending()

    @log
    def _back_button_clicked(self, widget, data=None):
        self.set_visible_child(self._grid)

    @log
    def _on_item_activated(self, widget, id, path):
        child_path = self.filter.convert_path_to_child_path(path)
        _iter = self._model.get_iter(child_path)
        title = self._model.get_value(_iter, 2)
        artist = self._model.get_value(_iter, 3)
        item = self._model.get_value(_iter, 5)
        self._albumWidget.update(artist, title, item,
                                 self.header_bar, self.selection_toolbar)
        self.header_bar.set_state(0)
        escaped_title = albumArtCache.get_media_title(item)
        self.header_bar.header_bar.set_title(escaped_title)
        self.header_bar.header_bar.sub_title = artist
        self.set_visible_child(self._albumWidget)

    @log
    def populate(self):
        if grilo.tracker:
            GLib.idle_add(grilo.populate_albums, self._offset, self._add_item)

    @log
    def get_selected_track_uris(self, callback):
        if self.header_bar._state == ToolbarState.SINGLE:
            uris = []
            for path in self._albumWidget.view.get_selection():
                _iter = self._albumWidget.model.get_iter(path)
                uris.append(self._albumWidget.model.get_value(_iter, 5).get_url())
            callback(uris)
        else:
            self.items_selected = []
            self.items_selected_callback = callback
            self.albums_index = 0
            self.albums_selected = [self.filter.get_value(self.filter.get_iter(path), 5)
                                    for path in self.view.get_selection()]
            if len(self.albums_selected):
                self._get_selected_album_songs()

    @log
    def _get_selected_album_songs(self):
        grilo.populate_album_songs(
            self.albums_selected[self.albums_index].get_id(),
            self._add_selected_item)
        self.albums_index += 1

    @log
    def _add_selected_item(self, source, param, item, remaining):
        if item:
            self.items_selected.append(item.get_url())
        if remaining == 0:
            if self.albums_index < len(self.albums_selected):
                self._get_selected_album_songs()
            else:
                self.items_selected_callback(self.items_selected)


class Songs(ViewContainer):
    @log
    def __init__(self, header_bar, selection_toolbar, player):
        ViewContainer.__init__(self, _("Songs"), header_bar, selection_toolbar, Gd.MainViewType.LIST)
        self.countQuery = Query.get_songs_count()
        self._items = {}
        self.monitors = []
        self.isStarred = None
        self.iter_to_clean = None
        self.view.get_generic_view().get_style_context()\
            .add_class('songs-list')
        self._iconHeight = 32
        self._iconWidth = 32
        self.cache = albumArtCache.get_default()
        self._symbolicIcon = self.cache.make_default_icon(self._iconHeight,
                                                          self._iconWidth)
        self._add_list_renderers()
        self.player = player
        self.player.connect('playlist-item-changed', self.update_model)

    @log
    def _on_changes_pending(self, data=None):
        if (self._init and self.header_bar._selectionMode is False):
            self._model.clear()
            self._offset = 0
            self._cached_count = -1
            self.populate()
            grilo.changes_pending['Songs'] = False

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        if self.header_bar._selectionMode is False and grilo.changes_pending['Songs'] is True:
            self._on_changes_pending()

    @log
    def _on_item_activated(self, widget, id, path):
        _iter = self.filter.get_iter(path)
        child_iter = self.filter.convert_iter_to_child_iter(_iter)
        if self._model.get_value(child_iter, 8) != self.errorIconName:
            self.player.set_playlist('Songs', None, self.filter, _iter, 5)
            self.player.set_playing(True)

    @log
    def update_model(self, player, playlist, currentIter):
        if self.iter_to_clean:
            self._model.set_value(self.iter_to_clean, 10, False)
        if playlist != self.filter:
            return False

        child_iter = self.filter.convert_iter_to_child_iter(currentIter)
        self._model.set_value(child_iter, 10, True)
        path = self._model.get_path(child_iter)
        self.view.get_generic_view().scroll_to_path(path)
        if self._model.get_value(child_iter, 8) != self.errorIconName:
            self.iter_to_clean = child_iter.copy()
        return False

    @log
    def _add_item(self, source, param, item, remaining):
        if not item:
            return
        self._offset += 1
        item.set_title(albumArtCache.get_media_title(item))
        artist = item.get_string(Grl.METADATA_KEY_ARTIST)\
            or item.get_author()\
            or _("Unknown Artist")
        _iter = self._model.insert_with_valuesv(
            -1,
            [2, 3, 5, 8, 9, 10],
            [albumArtCache.get_media_title(item),
             artist, item, self.nowPlayingIconName, False, False])
        self.player.discover_item(item, self._on_discovered, _iter)
        g_file = Gio.file_new_for_uri(item.get_url())
        self.monitors.append(g_file.monitor_file(Gio.FileMonitorFlags.NONE,
                                                 None))
        self.monitors[(self._offset - 1)].connect('changed',
                                                  self._on_item_changed, _iter)

    def _on_item_changed(self, monitor, file1, file2, event, _iter):
        if self._model.iter_is_valid(_iter):
            if event == Gio.FileMonitorEvent.DELETED:
                self._model.set(_iter, [8, 10], [self.errorIconName, True])

    @log
    def _add_list_renderers(self):
        list_widget = self.view.get_generic_view()
        cols = list_widget.get_columns()
        cells = cols[0].get_cells()
        cells[2].set_visible(False)
        now_playing_symbol_renderer = Gtk.CellRendererPixbuf(xalign=1.0)

        column_now_playing = Gtk.TreeViewColumn()
        column_now_playing.set_property('fixed_width', 24)
        column_now_playing.pack_start(now_playing_symbol_renderer, False)
        column_now_playing.add_attribute(now_playing_symbol_renderer,
                                         'visible', 10)
        column_now_playing.add_attribute(now_playing_symbol_renderer,
                                         'icon_name', 8)
        list_widget.insert_column(column_now_playing, 0)

        title_renderer = Gtk.CellRendererText(
            xpad=0,
            xalign=0.0,
            yalign=0.5,
            height=48,
            ellipsize=Pango.EllipsizeMode.END
        )
        list_widget.add_renderer(title_renderer,
                                 self._on_list_widget_title_render, None)
        cols[0].add_attribute(title_renderer, 'text', 2)

        star_renderer = Gtk.CellRendererPixbuf(
            xpad=32,
            icon_name=self.starIconName
        )
        list_widget.add_renderer(star_renderer,
                                 self._on_list_widget_star_render, None)
        cols[0].add_attribute(star_renderer, 'visible', 9)

        duration_renderer = Gd.StyledTextRenderer(
            xpad=32,
            xalign=1.0
        )
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
        cols[0].add_attribute(artist_renderer, 'text', 3)

        type_renderer = Gd.StyledTextRenderer(
            xpad=32,
            ellipsize=Pango.EllipsizeMode.END
        )
        type_renderer.add_class('dim-label')
        list_widget.add_renderer(type_renderer,
                                 self._on_list_widget_type_render, None)

    def _on_list_widget_title_render(self, col, cell, model, _iter, data):
        pass

    def _on_list_widget_star_render(self, col, cell, model, _iter, data):
        pass

    def _on_list_widget_duration_render(self, col, cell, model, _iter, data):
        item = model.get_value(_iter, 5)
        if item:
            seconds = item.get_duration()
            minutes = seconds // 60
            seconds %= 60
            cell.set_property('text', '%i:%02i' % (minutes, seconds))

    def _on_list_widget_artist_render(self, col, cell, model, _iter, data):
        pass

    def _on_list_widget_type_render(self, coll, cell, model, _iter, data):
        item = model.get_value(_iter, 5)
        if item:
            cell.set_property('text', item.get_string(Grl.METADATA_KEY_ALBUM) or _("Unknown Album"))

    @log
    def populate(self):
        if grilo.tracker:
            GLib.idle_add(grilo.populate_songs, self._offset, self._add_item)

    @log
    def get_selected_track_uris(self, callback):
        callback([self.filter.get_value(self.filter.get_iter(path), 5).get_url()
                  for path in self.view.get_selection()])


class Artists (ViewContainer):
    @log
    def __init__(self, header_bar, selection_toolbar, player):
        ViewContainer.__init__(self, _("Artists"), header_bar,
                               selection_toolbar, Gd.MainViewType.LIST, True)
        self.artists_counter = 0
        self.player = player
        self._artists = {}
        self.albums_selected = []
        self.items_selected = []
        self.items_selected_callback = None
        self.countQuery = Query.ARTISTS_COUNT
        self.artistAlbumsStack = Stack(
            transition_type=StackTransitionType.CROSSFADE,
        )
        self._artistAlbumsWidget = Gtk.Frame(
            shadow_type=Gtk.ShadowType.NONE,
            hexpand=True
        )
        self.artistAlbumsStack.add_named(self._artistAlbumsWidget, "sidebar")
        self.artistAlbumsStack.set_visible_child_name("sidebar")
        self.view.set_hexpand(False)
        self.view.get_style_context().add_class('artist-panel')
        self.view.get_generic_view().get_selection().set_mode(
            Gtk.SelectionMode.SINGLE)
        self._grid.attach(self.artistAlbumsStack, 2, 0, 2, 2)
        self._add_list_renderers()
        if (Gtk.Settings.get_default().get_property(
                'gtk_application_prefer_dark_theme')):
            self.view.get_generic_view().get_style_context().\
                add_class('artist-panel-dark')
        else:
            self.view.get_generic_view().get_style_context().\
                add_class('artist-panel-white')
        self.show_all()

    @log
    def _on_changes_pending(self, data=None):
        if (self._init and self.header_bar._selectionMode is False):
            self._model.clear()
            self._artists.clear()
            self._offset = 0
            self._cached_count = -1
            self._populate()
            grilo.changes_pending['Artists'] = False

    @log
    def _populate(self, data=None):
        selection = self.view.get_generic_view().get_selection()
        if not selection.get_selected()[1]:
            self._allIter = self._model.insert_with_valuesv(-1, [2], [_("All Artists")])
            self._last_selection = self._allIter
            self._artists[_("All Artists").lower()] =\
                {'iter': self._allIter, 'albums': [], 'widget': None}
            selection.select_path(self._model.get_path(self._allIter))
            self.view.emit('item-activated', '0',
                           self._model.get_path(self._allIter))
        self._init = True
        self.populate()

    @log
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
        cols[0].add_attribute(type_renderer, 'text', 2)

    @log
    def _on_item_activated(self, widget, item_id, path):
        child_path = self.filter.convert_path_to_child_path(path)
        _iter = self._model.get_iter(child_path)
        self._last_selection = _iter
        artist = self._model.get_value(_iter, 2)
        albums = self._artists[artist.lower()]['albums']

        widget = self._artists[artist.lower()]['widget']
        if widget:
            if widget.model == self.player.running_playlist('Artist', widget.artist):
                self._artistAlbumsWidget = widget.get_parent()
                GLib.idle_add(self.artistAlbumsStack.set_visible_child,
                              self._artistAlbumsWidget)
                return
            elif widget.get_parent() == self._artistAlbumsWidget:
                return
            else:
                widget.get_parent().destroy()

        # Prepare a new artistAlbumsWidget here
        new_artistAlbumsWidget = Gtk.Frame(
            shadow_type=Gtk.ShadowType.NONE,
            hexpand=True
        )
        self.artistAlbumsStack.add(new_artistAlbumsWidget)

        artistAlbums = None
        if (self._model.get_string_from_iter(_iter) ==
                self._model.get_string_from_iter(self._allIter)):
            artistAlbums = Widgets.AllArtistsAlbums(self.player)
        else:
            artistAlbums = Widgets.ArtistAlbums(artist, albums, self.player)
        self._artists[artist.lower()]['widget'] = artistAlbums
        new_artistAlbumsWidget.add(artistAlbums)
        new_artistAlbumsWidget.show()

        # Replace previous widget
        self._artistAlbumsWidget = new_artistAlbumsWidget
        GLib.idle_add(self.artistAlbumsStack.set_visible_child, new_artistAlbumsWidget)

    @log
    def _add_item(self, source, param, item, remaining):
        if item is None:
            return
        self._offset += 1
        artist = item.get_string(Grl.METADATA_KEY_ARTIST)\
            or item.get_author()\
            or _("Unknown Artist")
        if not artist.lower() in self._artists:
            _iter = self._model.insert_with_valuesv(-1, [2], [artist])
            self._artists[artist.lower()] = {'iter': _iter, 'albums': [], 'widget': None}

        self._artists[artist.lower()]['albums'].append(item)

    @log
    def populate(self):
        if grilo.tracker:
            GLib.idle_add(grilo.populate_artists, self._offset, self._add_item)

    @log
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

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        self.artistAlbumsStack.set_sensitive(not self.header_bar._selectionMode)
        if self.header_bar._selectionMode is False and grilo.changes_pending['Artists'] is True:
            self._on_changes_pending()

    @log
    def get_selected_track_uris(self, callback):
        self.items_selected = []
        self.items_selected_callback = callback
        self.albums_index = 0
        self.albums_selected = []

        for path in self.view.get_selection():
            _iter = self.filter.get_iter(path)
            artist = self.filter.get_value(_iter, 2)
            albums = self._artists[artist.lower()]['albums']
            if (self.filter.get_string_from_iter(_iter) !=
                    self.filter.get_string_from_iter(self._allIter)):
                self.albums_selected.extend(albums)

        if len(self.albums_selected):
            self._get_selected_album_songs()

    @log
    def _get_selected_album_songs(self):
        grilo.populate_album_songs(
            self.albums_selected[self.albums_index].get_id(),
            self._add_selected_item)
        self.albums_index += 1

    @log
    def _add_selected_item(self, source, param, item, remaining):
        if item:
            self.items_selected.append(item.get_url())
        if remaining == 0:
            if self.albums_index < len(self.albums_selected):
                self._get_selected_album_songs()
            else:
                self.items_selected_callback(self.items_selected)


class Playlist(ViewContainer):
    playlists_list = playlists.get_playlists()

    @log
    def __init__(self, header_bar, selection_toolbar, player):
        self.playlists_sidebar = Gd.MainView(
            shadow_type=Gtk.ShadowType.NONE
        )

        ViewContainer.__init__(self, _("Playlists"), header_bar,
                               selection_toolbar, Gd.MainViewType.LIST, True, self.playlists_sidebar)

        self.view.get_generic_view().get_style_context()\
            .add_class('songs-list')
        self._add_list_renderers()

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Music/PlaylistControls.ui')
        self.headerbar = builder.get_object('grid')
        self.name_label = builder.get_object('playlist_name')
        self.songs_count_label = builder.get_object('songs_count')
        self.menubutton = builder.get_object('playlist_menubutton')
        self.play_menuitem = builder.get_object('menuitem_play')
        self.play_menuitem.connect('activate', self._on_play_activate)
        self.delete_menuitem = builder.get_object('menuitem_delete')
        self.delete_menuitem.connect('activate', self._on_delete_activate)
        self._grid.insert_row(0)
        self._grid.attach(self.headerbar, 1, 0, 1, 1)

        self.playlists_model = Gtk.ListStore(
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
        )
        self.playlists_sidebar.set_view_type(Gd.MainViewType.LIST)
        self.playlists_sidebar.set_model(self.playlists_model)
        self.playlists_sidebar.set_hexpand(False)
        self.playlists_sidebar.get_style_context().add_class('artist-panel')
        self.playlists_sidebar.get_generic_view().get_selection().set_mode(
            Gtk.SelectionMode.SINGLE)
        self.playlists_sidebar.connect('item-activated', self._on_playlist_activated)
        self._grid.insert_column(0)
        self._grid.child_set_property(self.stack, 'top-attach', 0)
        self._grid.child_set_property(self.stack, 'height', 2)
        self._add_sidebar_renderers()
        if (Gtk.Settings.get_default().get_property(
                'gtk_application_prefer_dark_theme')):
            self.playlists_sidebar.get_generic_view().get_style_context().\
                add_class("artist-panel-dark")
        else:
            self.playlists_sidebar.get_generic_view().get_style_context().\
                add_class("artist-panel-white")

        self.monitors = []
        self.iter_to_clean = None
        self.iter_to_clean_model = None
        self.current_playlist = None
        self.songs_count = 0
        self._update_songs_count()
        self.player = player
        self.player.connect('playlist-item-changed', self.update_model)
        playlists.connect('playlist-created', self._on_playlist_created)
        playlists.connect('song-added-to-playlist', self._on_song_added_to_playlist)
        playlists.connect('song-removed-from-playlist', self._on_song_removed_from_playlist)
        self.show_all()

    @log
    def _add_list_renderers(self):
        list_widget = self.view.get_generic_view()
        cols = list_widget.get_columns()
        cells = cols[0].get_cells()
        cells[2].set_visible(False)
        now_playing_symbol_renderer = Gtk.CellRendererPixbuf(xalign=1.0)

        column_now_playing = Gtk.TreeViewColumn()
        column_now_playing.set_property('fixed_width', 24)
        column_now_playing.pack_start(now_playing_symbol_renderer, False)
        column_now_playing.add_attribute(now_playing_symbol_renderer,
                                         'visible', 10)
        column_now_playing.add_attribute(now_playing_symbol_renderer,
                                         'icon_name', 8)
        list_widget.insert_column(column_now_playing, 0)

        title_renderer = Gtk.CellRendererText(
            xpad=0,
            xalign=0.0,
            yalign=0.5,
            height=48,
            ellipsize=Pango.EllipsizeMode.END
        )
        list_widget.add_renderer(title_renderer,
                                 self._on_list_widget_title_render, None)
        cols[0].add_attribute(title_renderer, 'text', 2)

        star_renderer = Gtk.CellRendererPixbuf(
            xpad=32,
            icon_name=self.starIconName
        )
        list_widget.add_renderer(star_renderer,
                                 self._on_list_widget_star_render, None)
        cols[0].add_attribute(star_renderer, 'visible', 9)

        duration_renderer = Gd.StyledTextRenderer(
            xpad=32,
            xalign=1.0
        )
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
        cols[0].add_attribute(artist_renderer, 'text', 3)

        type_renderer = Gd.StyledTextRenderer(
            xpad=32,
            ellipsize=Pango.EllipsizeMode.END
        )
        type_renderer.add_class('dim-label')
        list_widget.add_renderer(type_renderer,
                                 self._on_list_widget_type_render, None)

    @log
    def _add_sidebar_renderers(self):
        list_widget = self.playlists_sidebar.get_generic_view()

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

    def _on_list_widget_title_render(self, col, cell, model, _iter, data):
        pass

    def _on_list_widget_star_render(self, col, cell, model, _iter, data):
        pass

    def _on_list_widget_duration_render(self, col, cell, model, _iter, data):
        item = model.get_value(_iter, 5)
        if item:
            seconds = item.get_duration()
            minutes = seconds // 60
            seconds %= 60
            cell.set_property('text', '%i:%02i' % (minutes, seconds))

    def _on_list_widget_artist_render(self, col, cell, model, _iter, data):
        pass

    def _on_list_widget_type_render(self, coll, cell, model, _iter, data):
        item = model.get_value(_iter, 5)
        if item:
            cell.set_property('text', item.get_string(Grl.METADATA_KEY_ALBUM) or _("Unknown Album"))

    @log
    def _populate(self):
        self._init = True
        self.populate()

    @log
    def update_model(self, player, playlist, currentIter):
        if self.iter_to_clean:
            self.iter_to_clean_model.set_value(self.iter_to_clean, 10, False)
        if playlist != self.filter:
            return False

        child_iter = self.filter.convert_iter_to_child_iter(currentIter)
        self._model.set_value(child_iter, 10, True)
        if self._model.get_value(child_iter, 8) != self.errorIconName:
            self.iter_to_clean = child_iter.copy()
            self.iter_to_clean_model = self._model
        return False

    @log
    def _add_playlist_item(self, item):
        _iter = self.playlists_model.append()
        self.playlists_model.set(_iter, [2], [item])

    @log
    def _on_item_activated(self, widget, id, path):
        _iter = self.filter.get_iter(path)
        child_iter = self.filter.convert_iter_to_child_iter(_iter)
        if self._model.get_value(child_iter, 8) != self.errorIconName:
            self.player.set_playlist('Playlist', self.current_playlist, self.filter, _iter, 5)
            self.player.set_playing(True)

    @log
    def _on_item_changed(self, monitor, file1, file2, event, _iter):
        if self._model.iter_is_valid(_iter):
            if event == Gio.FileMonitorEvent.DELETED:
                self._model.set(_iter, [8, 10], [self.errorIconName, True])

    @log
    def _on_playlist_activated(self, widget, item_id, path):
        _iter = self.playlists_model.get_iter(path)
        playlist = self.playlists_model.get_value(_iter, 2)
        self.current_playlist = playlist
        self.name_label.set_text(playlist)

        # if the active queue has been set by this playlist,
        # use it as model, otherwise build the liststore
        cached_playlist = self.player.running_playlist('Playlist', playlist)
        if cached_playlist:
            self._model = cached_playlist.get_model()
            self.filter = cached_playlist
            currentTrack = self.player.playlist.get_iter(self.player.currentTrack.get_path())
            self.update_model(self.player, cached_playlist,
                              currentTrack)
            self.view.set_model(self.filter)
            self.songs_count = self._model.iter_n_children(None)
            self._update_songs_count()
        else:
            self._model = Gtk.ListStore(
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
            )
            self.filter = self._model.filter_new(None)
            self.view.set_model(self.filter)
            playlists.parse_playlist(playlist, self._add_item)
            self.songs_count = 0
            self._update_songs_count()

    @log
    def _add_item(self, source, param, item):
        self._add_item_to_model(item, self._model)

    @log
    def _add_item_to_model(self, item, model):
        if not item:
            return
        self._offset += 1
        item.set_title(albumArtCache.get_media_title(item))
        artist = item.get_string(Grl.METADATA_KEY_ARTIST)\
            or item.get_author()\
            or _("Unknown Artist")
        _iter = model.insert_with_valuesv(
            -1,
            [2, 3, 5, 8, 9, 10],
            [albumArtCache.get_media_title(item),
             artist, item, self.nowPlayingIconName, False, False])
        self.player.discover_item(item, self._on_discovered, _iter)
        g_file = Gio.file_new_for_uri(item.get_url())
        self.monitors.append(g_file.monitor_file(Gio.FileMonitorFlags.NONE,
                                                 None))
        self.monitors[(self._offset - 1)].connect('changed',
                                                  self._on_item_changed, _iter)
        self.songs_count += 1
        self._update_songs_count()

    @log
    def _update_songs_count(self):
        self.songs_count_label.set_text(
            ngettext("%d Song", "%d Songs", self.songs_count)
            % self.songs_count)

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        self.playlists_sidebar.set_sensitive(not self.header_bar._selectionMode)
        self.menubutton.set_sensitive(not self.header_bar._selectionMode)

    @log
    def _on_play_activate(self, menuitem, data=None):
        _iter = self._model.get_iter_first()
        if not _iter:
            return

        self.view.get_generic_view().get_selection().\
            select_path(self._model.get_path(_iter))
        self.view.emit('item-activated', '0',
                       self._model.get_path(_iter))

    @log
    def _on_delete_activate(self, menuitem, data=None):
        self._model.clear()
        _iter = self.playlists_sidebar.get_generic_view().get_selection().get_selected()[1]
        if not _iter:
            return

        playlist = self.playlists_model.get_value(_iter, 2)
        playlists.delete_playlist(playlist)
        self.playlists_model.remove(_iter)

    @log
    def _on_playlist_created(self, playlists, name):
        self._add_playlist_item(name)

    @log
    def _on_song_added_to_playlist(self, playlists, name, item):
        if name == self.current_playlist:
            self._add_item_to_model(item, self._model)
        else:
            cached_playlist = self.player.running_playlist('Playlist', name)
            if cached_playlist and cached_playlist != self._model:
                self._add_item_to_model(item, cached_playlist)

    @log
    def _on_song_removed_from_playlist(self, playlists, name, uri):
        if name == self.current_playlist:
            model = self._model
        else:
            cached_playlist = self.player.running_playlist('Playlist', name)
            if cached_playlist and cached_playlist != self._model:
                model = cached_playlist
            else:
                return

        update_playing_track = False
        for row in model:
            if row[5].get_url() == uri:
                # Is the removed track now being played?
                if name == self.current_playlist:
                    if self.player.currentTrack is not None:
                        currentTrackpath = self.player.currentTrack.get_path().to_string()
                        if row.path is not None and row.path.to_string() == currentTrackpath:
                            update_playing_track = True

                model.remove(row.iter)

                # Reload the model and switch to next song
                if update_playing_track:
                    if row.iter is None:
                        # Get first track if next track is not valid
                        row.iter = model.get_iter_first()
                        if row.iter is None:
                            # Last track was removed
                            return

                    self.iter_to_clean = None
                    # row.iter will give us next iter to start playing
                    # convert it to filter iter
                    row.iter = self.filter.convert_child_iter_to_iter(row.iter)[1]
                    self.update_model(self.player, self.filter, row.iter)
                    self.player.set_playlist('Playlist', name, self.filter, row.iter, 5)
                    self.player.set_playing(True)

                # Update songs count
                self.songs_count -= 1
                self._update_songs_count()
                return

    @log
    def populate(self):
        for item in sorted(self.playlists_list):
            self._add_playlist_item(item)

    @log
    def get_selected_track_uris(self, callback):
        callback([self.filter.get_value(self.filter.get_iter(path), 5).get_url()
                  for path in self.view.get_selection()])
