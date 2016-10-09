# Copyright (c) 2016 The GNOME Music Developers
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

from gettext import gettext as _, ngettext
from gi.repository import Gd, Gdk, GdkPixbuf, GLib, GObject, Gtk, Pango

from gnomemusic import log
from gnomemusic.albumartcache import AlbumArtCache, DefaultIcon, ArtSize
from gnomemusic.grilo import grilo
from gnomemusic.player import DiscoveryStatus
from gnomemusic.widgets.starhandlerwidget import StarHandlerWidget
import gnomemusic.utils as utils

NOW_PLAYING_ICON_NAME = 'media-playback-start-symbolic'
ERROR_ICON_NAME = 'dialog-error-symbolic'


class AlbumWidget(Gtk.EventBox):
    """Album widget.

    The album widget consists of an image with the album art
    on the left and a list of songs on the right.
    """

    _duration = 0

    def __repr__(self):
        return '<AlbumWidget>'

    @log
    def __init__(self, player, parent_view):
        """Initialize the AlbumWidget.

        :param player: The player object
        :param parent_view: The view this widget is part of
        """
        Gtk.EventBox.__init__(self)

        scale = self.get_scale_factor()
        self._cache = AlbumArtCache(scale)
        self._loading_icon_surface = DefaultIcon(scale).get(
            DefaultIcon.Type.loading,
            ArtSize.small)
        self._no_artwork_icon_surface = DefaultIcon(scale).get(
            DefaultIcon.Type.music,
            ArtSize.small)

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
        self._star_handler = StarHandlerWidget(self, 9)
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
                title = utils.get_media_title(item)
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
        self._ui.get_object('cover').set_from_surface(
            self._loading_icon_surface)
        self._cache.lookup(item, ArtSize.large, self._on_lookup, None)
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
            title = utils.get_media_title(track)
            escaped_title = GLib.markup_escape_text(title)
            self.model[_iter][0, 1, 2, 3, 4, 5, 9] = [
                escaped_title,
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
    def _on_lookup(self, surface, data=None):
        """Albumart retrieved callback.

        :param surface: The Cairo surface retrieved
        :param path: The filesystem location the pixbuf
        :param data: User data
        """
        if not surface:
            surface = self._no_artwork_icon_surface
        self._ui.get_object('cover').set_from_surface(surface)

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
            escaped_title = GLib.markup_escape_text(utils.get_media_title(song))
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
