# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Shivani Poddar <shivani.poddar92@gmail.com>
# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
# Copyright (c) 2013 Sai Suman Prayaga <suman.sai14@gmail.com>
# Copyright (c) 2013 Jackson Isaac <jacksonisaac2008@gmail.com>
# Copyright (c) 2013 Felipe Borges <felipe10borges@gmail.com>
# Copyright (c) 2013 Giovanni Campagna <scampa.giovanni@gmail.com>
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

import logging

from gi.repository import Gtk, Gdk, Gd, GLib, GObject, Pango, Gio, GdkPixbuf
from gettext import gettext as _, ngettext

from gnomemusic.albumartcache import AlbumArtCache, DefaultIcon
from gnomemusic.grilo import grilo
from gnomemusic import log
from gnomemusic.player import DiscoveryStatus
from gnomemusic.playlists import Playlists, StaticPlaylists
import gnomemusic.utils as utils


logger = logging.getLogger(__name__)

ALBUM_ART_CACHE = AlbumArtCache.get_default()
NOW_PLAYING_ICON_NAME = 'media-playback-start-symbolic'
ERROR_ICON_NAME = 'dialog-error-symbolic'

try:
    settings = Gio.Settings.new('org.gnome.Music')
    MAX_TITLE_WIDTH = settings.get_int('max-width-chars')
except Exception as e:
    MAX_TITLE_WIDTH = 20
    logger.error("Error on setting widget max-width-chars: %s", str(e))

playlists = Playlists.get_default()


class StarHandler():
    """Handles the treeview column for favorites (stars)."""

    def __repr__(self):
        return '<StarHandler>'

    @log
    def __init__(self, parent, star_index):
        """Initialize.

        :param parent: The parent widget
        :param int star_index: The column of the stars
        """
        self.star_renderer_click = False
        self._star_index = star_index
        self._parent = parent

    @log
    def add_star_renderers(self, list_widget, cols, hidden=False):
        """Adds the star renderer column

        :param list_widget: The widget to add the favorites column
        :param cols: List of the widgets GtkTreeViewColumns
        :param hidden: Visible state of the column
        """
        star_renderer = CellRendererClickablePixbuf(self._parent.view,
                                                    hidden=hidden)
        star_renderer.connect("clicked", self._on_star_toggled)
        list_widget.add_renderer(star_renderer, lambda *args: None, None)

        cols[0].clear_attributes(star_renderer)
        cols[0].add_attribute(star_renderer, 'show_star', self._star_index)

    @log
    def _on_star_toggled(self, widget, path):
        """Called if a star is clicked"""
        try:
            _iter = self._parent.model.get_iter(path)
        except TypeError:
            return

        try:
            if self._parent.model[_iter][9] == 2:
                return
        except AttributeError:
            return

        new_value = not self._parent.model[_iter][self._star_index]
        self._parent.model[_iter][self._star_index] = new_value
        song_item = self._parent.model[_iter][5]
        grilo.toggle_favorite(song_item)
        playlists.update_static_playlist(StaticPlaylists.Favorites)

        # Use this flag to ignore the upcoming _on_item_activated call
        self.star_renderer_click = True


class AlbumWidget(Gtk.EventBox):
    """Album widget.

    The album widget consists of an image with the album art
    on the left and a list of songs on the right.
    """

    _duration = 0
    _loading_icon = DefaultIcon().get(256, 256, DefaultIcon.Type.loading)
    _no_artwork_icon = DefaultIcon().get(256, 256, DefaultIcon.Type.music)

    def __repr__(self):
        return '<AlbumWidget>'

    @log
    def __init__(self, player, parent_view):
        """Initialize the AlbumWidget.

        :param player: The player object
        :param parent_view: The view this widget is part of
        """
        Gtk.EventBox.__init__(self)
        self._player = player
        self._iter_to_clean = None

        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Music/AlbumWidget.ui')
        self._create_model()
        self.view = Gd.MainView(
            shadow_type=Gtk.ShadowType.NONE
        )
        self.view.set_view_type(Gd.MainViewType.LIST)
        self._album = None
        self._header_bar = None
        self.view.connect('item-activated', self._on_item_activated)

        view_box = self._ui.get_object('view')
        self._ui.get_object('scrolledWindow').set_placement(Gtk.CornerType.
                                                            TOP_LEFT)
        self.view.connect('selection-mode-request',
                          self._on_selection_mode_request)
        child_view = self.view.get_children()[0]
        child_view.set_margin_top(64)
        child_view.set_margin_bottom(64)
        child_view.set_margin_end(32)
        self.view.remove(child_view)
        view_box.add(child_view)

        self.add(self._ui.get_object('AlbumWidget'))
        self._star_handler = StarHandler(self, 9)
        self._add_list_renderers()
        self.get_style_context().add_class('view')
        self.get_style_context().add_class('content-view')
        self.view.get_generic_view().get_style_context().remove_class('view')
        self.show_all()

    @log
    def _on_selection_mode_request(self, *args):
        """Selection mode toggled."""
        self._header_bar._select_button.clicked()

    @log
    def _on_item_activated(self, widget, id, path):
        """List row activated."""
        if self._star_handler.star_renderer_click:
            self._star_handler.star_renderer_click = False
            return

        _iter = self.model.get_iter(path)

        if self.model[_iter][10] != DiscoveryStatus.FAILED:
            if (self._iter_to_clean
                    and self._player.playlistId == self._album):
                item = self.model[self._iter_to_clean][5]
                title = AlbumArtCache.get_media_title(item)
                self.model[self._iter_to_clean][0] = title
                # Hide now playing icon
                self.model[self._iter_to_clean][6] = False
            self._player.set_playlist('Album', self._album, self.model, _iter,
                                      5, 11)
            self._player.set_playing(True)

    @log
    def _add_list_renderers(self):
        """Create the ListView columns."""
        list_widget = self.view.get_generic_view()

        cols = list_widget.get_columns()
        cols[0].set_min_width(100)
        cols[0].set_max_width(200)
        cells = cols[0].get_cells()
        cells[2].set_visible(False)
        cells[1].set_visible(False)

        now_playing_symbol_renderer = Gtk.CellRendererPixbuf(xpad=0,
                                                             xalign=0.5,
                                                             yalign=0.5)

        column_now_playing = Gtk.TreeViewColumn()
        column_now_playing.set_fixed_width(48)
        column_now_playing.pack_start(now_playing_symbol_renderer, False)
        column_now_playing.set_cell_data_func(now_playing_symbol_renderer,
                                              self._on_list_widget_icon_render,
                                              None)
        list_widget.insert_column(column_now_playing, 0)

        type_renderer = Gd.StyledTextRenderer(
            xpad=16,
            ellipsize=Pango.EllipsizeMode.END,
            xalign=0.0
        )

        list_widget.add_renderer(type_renderer, lambda *args: None, None)
        cols[0].clear_attributes(type_renderer)
        cols[0].add_attribute(type_renderer, 'markup', 0)

        duration_renderer = Gd.StyledTextRenderer(
            xpad=16,
            ellipsize=Pango.EllipsizeMode.END,
            xalign=1.0
        )

        duration_renderer.add_class('dim-label')
        list_widget.add_renderer(duration_renderer, lambda *args: None, None)
        cols[0].clear_attributes(duration_renderer)
        cols[0].add_attribute(duration_renderer, 'markup', 1)

        self._star_handler.add_star_renderers(list_widget, cols)

    def _on_list_widget_icon_render(self, col, cell, model, _iter, data):
        if not self._player.currentTrackUri:
            cell.set_visible(False)
            return

        if model[_iter][10] == DiscoveryStatus.FAILED:
            cell.set_property('icon-name', ERROR_ICON_NAME)
            cell.set_visible(True)
        elif model[_iter][5].get_url() == self._player.currentTrackUri:
            cell.set_property('icon-name', NOW_PLAYING_ICON_NAME)
            cell.set_visible(True)
        else:
            cell.set_visible(False)

    @log
    def _create_model(self):
        """Create the ListStore model for this widget."""
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
            GObject.TYPE_INT,  # icon shown
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT
        )

    @log
    def update(self, artist, album, item, header_bar, selection_toolbar):
        """Update the album widget.

        :param str artist: The artist name
        :param str album: The album name
        :param item: The grilo media item
        :param header_bar: The header bar object
        :param selection_toolbar: The selection toolbar object
        """
        self.selection_toolbar = selection_toolbar
        self._header_bar = header_bar
        self._album = album
        real_artist = utils.get_artist_name(item)
        self._ui.get_object('cover').set_from_pixbuf(self._loading_icon)
        ALBUM_ART_CACHE.lookup(item, 256, 256, self._on_look_up, None,
                               real_artist, album)
        self._duration = 0
        self._create_model()
        GLib.idle_add(grilo.populate_album_songs, item, self.add_item)
        header_bar._select_button.connect(
            'toggled', self._on_header_select_button_toggled)
        header_bar._cancel_button.connect(
            'clicked', self._on_header_cancel_button_clicked)
        self.view.connect('view-selection-changed',
                          self._on_view_selection_changed)
        self.view.set_model(self.model)
        escaped_artist = GLib.markup_escape_text(artist)
        escaped_album = GLib.markup_escape_text(album)
        self._ui.get_object('artist_label').set_markup(escaped_artist)
        self._ui.get_object('title_label').set_markup(escaped_album)
        if (item.get_creation_date()):
            self._ui.get_object('released_label_info').set_text(
                str(item.get_creation_date().get_year()))
        else:
            self._ui.get_object('released_label_info').set_text('----')
        self._player.connect('playlist-item-changed', self._update_model)

    @log
    def _on_view_selection_changed(self, widget):
        items = self.view.get_selection()
        self.selection_toolbar._add_to_playlist_button.set_sensitive(
            len(items) > 0)
        if len(items) > 0:
            self._header_bar._selection_menu_label.set_text(
                ngettext("Selected %d item", "Selected %d items",
                         len(items)) % len(items))
        else:
            self._header_bar._selection_menu_label.set_text(
                _("Click on items to select them"))

    @log
    def _on_header_cancel_button_clicked(self, button):
        """Cancel selection mode callback."""
        self.view.set_selection_mode(False)
        self._header_bar.set_selection_mode(False)
        self._header_bar.header_bar.title = self._album

    @log
    def _on_header_select_button_toggled(self, button):
        """Selection mode button clicked callback."""
        if button.get_active():
            self.view.set_selection_mode(True)
            self._header_bar.set_selection_mode(True)
            self._player.actionbar.set_visible(False)
            self.selection_toolbar.actionbar.set_visible(True)
            self.selection_toolbar._add_to_playlist_button.set_sensitive(False)
            self._header_bar.header_bar.set_custom_title(
                self._header_bar._selection_menu_button)
        else:
            self.view.set_selection_mode(False)
            self._header_bar.set_selection_mode(False)
            self._header_bar.title = self._album
            self.selection_toolbar.actionbar.set_visible(False)
            if(self._player.get_playback_status() != 2):
                self._player.actionbar.set_visible(True)

    @log
    def add_item(self, source, prefs, track, remaining, data=None):
        """Add a song to the item to album list.

        :param source: The grilo source
        :param prefs:
        :param track: The grilo media object
        :param remaining: Remaining number of items to add
        :param data: User data
        """
        if track:
            self._duration = self._duration + track.get_duration()
            _iter = self.model.append()
            escapedTitle = AlbumArtCache.get_media_title(track, True)
            self.model[_iter][0, 1, 2, 3, 4, 5, 9] = [
                escapedTitle,
                self._player.seconds_to_string(track.get_duration()),
                '',
                '',
                None,
                track,
                bool(track.get_lyrics())
            ]
            self._ui.get_object('running_length_label_info').set_text(
                _("%d min") % (int(self._duration / 60) + 1))

    @log
    def _on_look_up(self, pixbuf, path, data=None):
        """Albumart retrieved callback.

        :param pixbuf: The GtkPixbuf retrieved
        :param path: The filesystem location the pixbuf
        :param data: User data
        """
        _iter = self._iter_to_clean
        if not pixbuf:
            pixbuf = self._no_artwork_icon
        self._ui.get_object('cover').set_from_pixbuf(pixbuf)
        if _iter:
            self.model[_iter][4] = pixbuf

    @log
    def _update_model(self, player, playlist, current_iter):
        """Player changed callback.

        :param player: The player object
        :param playlist: The current playlist
        :param current_iter: The current iter of the playlist model
        """
        # self is not our playlist, return
        if (playlist != self.model):
            return False

        current_song = playlist[current_iter][5]
        song_passed = False
        _iter = playlist.get_iter_first()
        self._duration = 0

        while _iter:
            song = playlist[_iter][5]
            self._duration += song.get_duration()
            escaped_title = AlbumArtCache.get_media_title(song, True)
            if (song == current_song):
                title = '<b>%s</b>' % escaped_title
                song_passed = True
            elif (song_passed):
                title = '<span>%s</span>' % escaped_title
            else:
                title = '<span color=\'grey\'>%s</span>' % escaped_title
            playlist[_iter][0] = title
            _iter = playlist.iter_next(_iter)
            self._ui.get_object('running_length_label_info').set_text(
                _("%d min") % (int(self._duration / 60) + 1))

        return False


class ArtistAlbums(Gtk.Box):

    def __repr__(self):
        return '<ArtistAlbums>'

    @log
    def __init__(self, artist, albums, player,
                 header_bar, selection_toolbar, window, selectionModeAllowed=False):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.player = player
        self.artist = artist
        self.albums = albums
        self.window = window
        self.selectionMode = False
        self.selectionModeAllowed = selectionModeAllowed
        self.selection_toolbar = selection_toolbar
        self.header_bar = header_bar
        self.ui = Gtk.Builder()
        self.ui.add_from_resource('/org/gnome/Music/ArtistAlbumsWidget.ui')
        self.set_border_width(0)
        self.ui.get_object('artist').set_label(self.artist)
        self.widgets = []

        self.model = Gtk.ListStore(GObject.TYPE_STRING,   # title
                                   GObject.TYPE_STRING,
                                   GObject.TYPE_STRING,
                                   GObject.TYPE_BOOLEAN,  # icon shown
                                   GObject.TYPE_STRING,   # icon
                                   GObject.TYPE_OBJECT,   # song object
                                   GObject.TYPE_BOOLEAN,
                                   GObject.TYPE_INT
                                   )
        self.row_changed_source_id = None

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
        self._coverSizeGroup = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)
        self._songsGridSizeGroup = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)
        self.pack_start(self._scrolledWindow, True, True, 0)

        self.hide()
        self.window._init_loading_notification()

        for album in albums:
            is_last_album = False
            if album == albums[-1]:
                is_last_album = True
            self.add_album(album, is_last_album)

        self.player.connect('playlist-item-changed', self.update_model)

    def _on_last_album_displayed(self, data=None):
        self.window.notification.dismiss()
        self.show_all()

    @log
    def add_album(self, album, is_last_album=False):
        self.window.notification.set_timeout(0)
        widget = ArtistAlbumWidget(
            self.artist, album, self.player, self.model,
            self.header_bar, self.selectionModeAllowed
        )
        self._coverSizeGroup.add_widget(widget.cover)
        self._songsGridSizeGroup.add_widget(widget.songsGrid)
        self._albumBox.pack_start(widget, False, False, 0)
        self.widgets.append(widget)

        if is_last_album:
            widget.connect('tracks-loaded', self._on_last_album_displayed)

    @log
    def update_model(self, player, playlist, currentIter):
        # this is not our playlist, return
        if playlist != self.model:
            # TODO, only clean once, but that can wait util we have clean
            # the code a bit, and until the playlist refactoring.
            # the overhead is acceptable for now
            self.clean_model()
            return False

        currentSong = playlist.get_value(currentIter, 5)
        song_passed = False
        itr = playlist.get_iter_first()

        while itr:
            song = playlist.get_value(itr, 5)
            song_widget = song.song_widget

            if not song_widget.can_be_played:
                itr = playlist.iter_next(itr)
                continue

            escapedTitle = AlbumArtCache.get_media_title(song, True)
            if (song == currentSong):
                song_widget.now_playing_sign.show()
                song_widget.title.set_markup('<b>%s</b>' % escapedTitle)
                song_passed = True
            elif (song_passed):
                song_widget.now_playing_sign.hide()
                song_widget.title.set_markup('<span>%s</span>' % escapedTitle)
            else:
                song_widget.now_playing_sign.hide()
                song_widget.title\
                    .set_markup('<span color=\'grey\'>%s</span>' % escapedTitle)
            itr = playlist.iter_next(itr)
        return False

    @log
    def clean_model(self):
        itr = self.model.get_iter_first()
        while itr:
            song = self.model.get_value(itr, 5)
            song_widget = song.song_widget
            escapedTitle = AlbumArtCache.get_media_title(song, True)
            if song_widget.can_be_played:
                song_widget.now_playing_sign.hide()
            song_widget.title.set_markup('<span>%s</span>' % escapedTitle)
            itr = self.model.iter_next(itr)
        return False

    @log
    def set_selection_mode(self, selectionMode):
        if self.selectionMode == selectionMode:
            return
        self.selectionMode = selectionMode
        try:
            if self.row_changed_source_id:
                self.model.disconnect(self.row_changed_source_id)
            self.row_changed_source_id = self.model.connect('row-changed', self._model_row_changed)
        except Exception as e:
            logger.warning("Exception while tracking row-changed: %s", e)

        for widget in self.widgets:
            widget.set_selection_mode(selectionMode)

    @log
    def _model_row_changed(self, model, path, _iter):
        if not self.selectionMode:
            return
        selected_items = 0
        for row in model:
            if row[6]:
                selected_items += 1
        self.selection_toolbar\
            ._add_to_playlist_button.set_sensitive(selected_items > 0)
        if selected_items > 0:
            self.header_bar._selection_menu_label.set_text(
                ngettext("Selected %d item", "Selected %d items", selected_items) % selected_items)
        else:
            self.header_bar._selection_menu_label.set_text(_("Click on items to select them"))


class AllArtistsAlbums(ArtistAlbums):

    def __repr__(self):
        return '<AllArtistsAlbums>'

    @log
    def __init__(self, player, header_bar, selection_toolbar, selectionModeAllowed=False):
        ArtistAlbums.__init__(self, _("All Artists"), [], player,
                              header_bar, selection_toolbar, selectionModeAllowed)
        self._offset = 0
        self._populate()

    @log
    def _populate(self, data=None):
        if grilo.tracker:
            GLib.idle_add(grilo.populate_albums,
                          self._offset, self.add_item)

    @log
    def add_item(self, source, param, item, remaining=0, data=None):
        if remaining == 0:
            self._on_last_album_displayed()

        if item:
            self._offset += 1
            self.add_album(item)


class ArtistAlbumWidget(Gtk.Box):

    __gsignals__ = {
        'tracks-loaded': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    _loading_icon = DefaultIcon().get(256, 256, DefaultIcon.Type.loading)
    _no_artwork_icon = DefaultIcon().get(256, 256, DefaultIcon.Type.music)

    def __repr__(self):
        return '<ArtistAlbumWidget>'

    @log
    def __init__(self, artist, album, player, model, header_bar, selectionModeAllowed):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)
        self.player = player
        self.album = album
        self.artist = artist
        self.model = model
        self.model.connect('row-changed', self._model_row_changed)
        self.header_bar = header_bar
        self.selectionMode = False
        self.selectionModeAllowed = selectionModeAllowed
        self.songs = []
        self.ui = Gtk.Builder()
        self.ui.add_from_resource('/org/gnome/Music/ArtistAlbumWidget.ui')

        GLib.idle_add(self._update_album_art)

        self.cover = self.ui.get_object('cover')
        self.cover.set_from_pixbuf(self._loading_icon)
        self.songsGrid = self.ui.get_object('grid1')
        self.ui.get_object('title').set_label(album.get_title())
        if album.get_creation_date():
            self.ui.get_object('year').set_markup(
                '<span color=\'grey\'>(%s)</span>' %
                str(album.get_creation_date().get_year())
            )
        self.tracks = []
        grilo.populate_album_songs(album, self.add_item)
        self.pack_start(self.ui.get_object('ArtistAlbumWidget'), True, True, 0)

    @log
    def add_item(self, source, prefs, track, remaining, data=None):
        if remaining == 0:
            self.songsGrid.show_all()
            self.emit("tracks-loaded")

        if track:
            self.tracks.append(track)
        else:
            for i, track in enumerate(self.tracks):
                ui = Gtk.Builder()
                ui.add_from_resource('/org/gnome/Music/TrackWidget.ui')
                song_widget = ui.get_object('eventbox1')
                self.songs.append(song_widget)
                ui.get_object('num')\
                    .set_markup('<span color=\'grey\'>%d</span>'
                                % len(self.songs))
                title = AlbumArtCache.get_media_title(track)
                ui.get_object('title').set_text(title)
                ui.get_object('title').set_alignment(0.0, 0.5)
                ui.get_object('title').set_max_width_chars(MAX_TITLE_WIDTH)

                self.songsGrid.attach(
                    song_widget,
                    int(i / (len(self.tracks) / 2)),
                    int(i % (len(self.tracks) / 2)), 1, 1
                )
                track.song_widget = song_widget
                itr = self.model.append(None)
                song_widget._iter = itr
                song_widget.model = self.model
                song_widget.title = ui.get_object('title')
                song_widget.checkButton = ui.get_object('select')
                song_widget.checkButton.set_visible(self.selectionMode)
                song_widget.checkButton.connect(
                    'toggled', self._check_button_toggled, song_widget
                )
                self.model.set(itr,
                               [0, 1, 2, 3, 5],
                               [title, '', '', False, track])
                song_widget.now_playing_sign = ui.get_object('image1')
                song_widget.now_playing_sign.set_from_icon_name(
                    NOW_PLAYING_ICON_NAME,
                    Gtk.IconSize.SMALL_TOOLBAR)
                song_widget.now_playing_sign.set_no_show_all('True')
                song_widget.now_playing_sign.set_alignment(1, 0.6)
                song_widget.can_be_played = True
                song_widget.connect('button-release-event',
                                    self.track_selected)

    @log
    def _update_album_art(self):
        artist = utils.get_artist_name(self.album)
        ALBUM_ART_CACHE.lookup(self.album, 128, 128, self._get_album_cover,
                               None, artist, self.album.get_title())

    @log
    def _get_album_cover(self, pixbuf, path, data=None):
        if not pixbuf:
            pixbuf = self._no_artwork_icon
        self.cover.set_from_pixbuf(pixbuf)

    @log
    def track_selected(self, widget, event):
        if not widget.can_be_played:
            return

        if not self.selectionMode and \
            (event.button == Gdk.BUTTON_SECONDARY or
                (event.button == 1 and event.state & Gdk.ModifierType.CONTROL_MASK)):
            if self.selectionModeAllowed:
                self.header_bar._select_button.set_active(True)
            else:
                return

        if self.selectionMode:
            self.model[widget._iter][6] = not self.model[widget._iter][6]
            return

        self.player.stop()
        self.player.set_playlist('Artist', self.artist,
                                 widget.model, widget._iter, 5, 6)
        self.player.set_playing(True)

    @log
    def set_selection_mode(self, selectionMode):
        if self.selectionMode == selectionMode:
            return
        self.selectionMode = selectionMode
        for songWidget in self.songs:
            songWidget.checkButton.set_visible(selectionMode)
            if not selectionMode:
                songWidget.model[songWidget._iter][6] = False

    @log
    def _check_button_toggled(self, button, songWidget):
        if songWidget.model[songWidget._iter][6] != button.get_active():
            songWidget.model[songWidget._iter][6] = button.get_active()

    @log
    def _model_row_changed(self, model, path, _iter):
        if not self.selectionMode:
            return
        if not model[_iter][5]:
            return
        songWidget = model[_iter][5].song_widget
        selected = model[_iter][6]

        if model[_iter][11] == DiscoveryStatus.FAILED:
            songWidget.now_playing_sign.set_from_icon_name(
                ERROR_ICON_NAME,
                Gtk.IconSize.SMALL_TOOLBAR)
            songWidget.now_playing_sign.show()
            songWidget.can_be_played = False

        if selected != songWidget.checkButton.get_active():
            songWidget.checkButton.set_active(selected)


class PlaylistDialog():

    def __repr__(self):
        return '<PlaylistDialog>'

    @log
    def __init__(self, parent):
        self.ui = Gtk.Builder()
        self.ui.add_from_resource('/org/gnome/Music/PlaylistDialog.ui')
        self.dialog_box = self.ui.get_object('dialog1')
        self.dialog_box.set_transient_for(parent)

        self.view = self.ui.get_object('treeview1')
        self.view.set_activate_on_single_click(False)
        self.selection = self.ui.get_object('treeview-selection1')
        self.selection.connect('changed', self._on_selection_changed)
        self._add_list_renderers()
        self.view.connect('row-activated', self._on_item_activated)

        self.model = self.ui.get_object('liststore1')
        self.populate()

        self.title_bar = self.ui.get_object('headerbar1')
        self.dialog_box.set_titlebar(self.title_bar)

        self._cancel_button = self.ui.get_object('cancel-button')
        self._select_button = self.ui.get_object('select-button')
        self._select_button.set_sensitive(False)
        self._cancel_button.connect('clicked', self._on_cancel_button_clicked)
        self._select_button.connect('clicked', self._on_selection)

        self._new_playlist_button = self.ui.get_object('new-playlist-button')
        self._new_playlist_button.connect('clicked', self._on_editing_done)

        self._new_playlist_entry = self.ui.get_object('new-playlist-entry')
        self._new_playlist_entry.connect('changed',
                                         self._on_new_playlist_entry_changed)
        self._new_playlist_entry.connect('activate',
                                         self._on_editing_done)
        self._new_playlist_entry.connect('focus-in-event',
                                         self._on_new_playlist_entry_focused)

        self.playlist = Playlists.get_default()
        self.playlist.connect('playlist-created', self._on_playlist_created)

    @log
    def get_selected(self):
        _iter = self.selection.get_selected()[1]

        if not _iter or self.model[_iter][1]:
            return None

        return self.model[_iter][2]

    @log
    def _add_list_renderers(self):
        cols = Gtk.TreeViewColumn()
        type_renderer = Gd.StyledTextRenderer(
            xpad=8,
            ypad=8,
            ellipsize=Pango.EllipsizeMode.END,
            xalign=0.0
        )
        cols.pack_start(type_renderer, True)
        cols.add_attribute(type_renderer, "text", 0)
        cols.set_cell_data_func(type_renderer, self._on_list_text_render)
        self.view.append_column(cols)

    @log
    def populate(self):
        if grilo.tracker:
            GLib.idle_add(grilo.populate_playlists, 0, self._add_item)

    @log
    def _add_item(self, source, param, item, remaining=0, data=None):
        if item:
            self._add_item_to_model(item)

    @log
    def _add_item_to_model(self, item):
        """Adds (non-static only) playlists to the model"""

        # Don't show static playlists
        if self.playlist.is_static_playlist(item):
            return None

        new_iter = self.model.append()
        self.model.set(
            new_iter,
            [0, 1, 2],
            [AlbumArtCache.get_media_title(item), False, item]
        )
        return new_iter

    @log
    def _on_list_text_render(self, col, cell, model, _iter, data):
        editable = model.get_value(_iter, 1)
        if editable:
            cell.add_class("dim-label")
        else:
            cell.remove_class("dim-label")

    @log
    def _on_selection(self, select_button):
        self.dialog_box.response(Gtk.ResponseType.ACCEPT)

    @log
    def _on_cancel_button_clicked(self, cancel_button):
        self.dialog_box.response(Gtk.ResponseType.REJECT)

    @log
    def _on_item_activated(self, view, path, column):
        self._new_playlist_entry.set_text("")
        self._new_playlist_button.set_sensitive(False)
        _iter = self.model.get_iter(path)
        if self.model.get_value(_iter, 1):
            self.view.set_cursor(path, column, True)
        else:
            self.dialog_box.response(Gtk.ResponseType.ACCEPT)

    @log
    def _on_selection_changed(self, selection):
        model, _iter = self.selection.get_selected()

        if _iter == None or self.model.get_value(_iter, 1):
            self._select_button.set_sensitive(False)
        else:
            self._select_button.set_sensitive(True)


    @log
    def _on_editing_done(self, sender, data=None):
        if self._new_playlist_entry.get_text() != '':
            self.playlist.create_playlist(self._new_playlist_entry.get_text())

    @log
    def _on_playlist_created(self, playlists, item):
        new_iter = self._add_item_to_model(item)
        if new_iter and self.view.get_columns():
            self.view.set_cursor(self.model.get_path(new_iter),
                                 self.view.get_columns()[0], False)
            self.view.row_activated(self.model.get_path(new_iter),
                                    self.view.get_columns()[0])
            self.dialog_box.response(Gtk.ResponseType.ACCEPT)

    @log
    def _on_new_playlist_entry_changed(self, editable, data=None):
        if editable.get_text() != '':
            self._new_playlist_button.set_sensitive(True)
        else:
            self._new_playlist_button.set_sensitive(False)

    @log
    def _on_new_playlist_entry_focused(self, editable, data=None):
        self.selection.unselect_all()


class CellRendererClickablePixbuf(Gtk.CellRendererPixbuf):

    __gsignals__ = {'clicked': (GObject.SignalFlags.RUN_LAST, GObject.TYPE_NONE,
                                (GObject.TYPE_STRING,))}
    __gproperties__ = {
        'show_star': (GObject.TYPE_INT, 'Show star', 'show star',0 ,2 ,1 , GObject.ParamFlags.READWRITE)}

    starIcon = 'starred-symbolic'
    nonStarIcon = 'non-starred-symbolic'

    def __repr__(self):
        return '<CellRendererClickablePixbuf>'

    def __init__(self, view, hidden=False, *args, **kwargs):
        Gtk.CellRendererPixbuf.__init__(self, *args, **kwargs)
        self.set_property('mode', Gtk.CellRendererMode.ACTIVATABLE)
        self.set_property('xpad', 32)
        self.set_property('icon_name', '')
        self.view = view
        self.hidden = hidden
        self.show_star = 0

    def do_activate(self, event, widget, path, background_area, cell_area, flags):
        self.show_star = 0
        self.emit('clicked', path)

    def do_get_property(self, property):
        if property.name == 'show-star':
            return self.show_star

    def do_set_property(self, property, value):
        if property.name == 'show-star':
            if self.show_star == 1:
                self.set_property('icon_name', self.starIcon)
            elif self.show_star == 0:
                self.set_property('icon_name', self.nonStarIcon)
            else:
                self.set_property('icon_name', '')
            self.show_star = value
