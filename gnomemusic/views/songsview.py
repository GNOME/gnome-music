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

import logging
from gettext import gettext as _
from gi.repository import Gdk, GLib, Gtk, Pango

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.player import DiscoveryStatus
from gnomemusic.views.baseview import BaseView
import gnomemusic.utils as utils

logger = logging.getLogger(__name__)


class SongsView(BaseView):
    """Main view of all songs sorted artistwise

    Consists all songs along with songname, star, length, artist
    and the album name.
    """

    def __repr__(self):
        return '<SongsView>'

    @log
    def __init__(self, window, player):
        """Initialize

        :param GtkWidget window: The main window
        :param player: The main player object
        """
        super().__init__('songs', _("Songs"), window)

        self._offset = 0
        self._iter_to_clean = None

        self._view.get_style_context().add_class('songs-list')

        self._add_list_renderers()

        self.player = player
        self.player.connect('song-changed', self._update_model)

    @log
    def _setup_view(self):
        view_container = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self._box.pack_start(view_container, True, True, 0)

        self._view = Gtk.TreeView()
        self._view.props.headers_visible = False
        self._view.props.valign = Gtk.Align.START
        self._view.props.model = self.model
        self._view.props.activate_on_single_click = True

        self._view.get_selection().props.mode = Gtk.SelectionMode.SINGLE
        self._view.connect('row-activated', self._on_item_activated)
        self._view.connect('button-release-event', self._on_view_clicked)

        view_container.add(self._view)

    @log
    def _add_list_renderers(self):
        now_playing_symbol_renderer = Gtk.CellRendererPixbuf(
            xpad=0, xalign=0.5, yalign=0.5)
        column_now_playing = Gtk.TreeViewColumn()
        column_now_playing.props.fixed_width = 48
        column_now_playing.pack_start(now_playing_symbol_renderer, False)
        column_now_playing.set_cell_data_func(
            now_playing_symbol_renderer, self._on_list_widget_icon_render,
            None)
        self._view.append_column(column_now_playing)

        selection_renderer = Gtk.CellRendererToggle()
        column_selection = Gtk.TreeViewColumn(
            "Selected", selection_renderer, active=6)
        column_selection.props.visible = False
        column_selection.props.fixed_width = 48
        self._view.append_column(column_selection)

        title_renderer = Gtk.CellRendererText(
            xpad=0, xalign=0.0, yalign=0.5, height=48,
            ellipsize=Pango.EllipsizeMode.END)
        column_title = Gtk.TreeViewColumn("Title", title_renderer, text=2)
        column_title.props.expand = True
        self._view.append_column(column_title)

        column_star = Gtk.TreeViewColumn()
        self._view.append_column(column_star)
        self._star_handler.add_star_renderers(column_star)

        duration_renderer = Gtk.CellRendererText(xpad=32, xalign=1.0)
        column_duration = Gtk.TreeViewColumn()
        column_duration.pack_start(duration_renderer, False)
        column_duration.set_cell_data_func(
            duration_renderer, self._on_list_widget_duration_render, None)
        self._view.append_column(column_duration)

        artist_renderer = Gtk.CellRendererText(
            xpad=32, ellipsize=Pango.EllipsizeMode.END)
        column_artist = Gtk.TreeViewColumn("Artist", artist_renderer, text=3)
        column_artist.props.expand = True
        self._view.append_column(column_artist)

        album_renderer = Gtk.CellRendererText(
            xpad=32, ellipsize=Pango.EllipsizeMode.END)
        column_album = Gtk.TreeViewColumn()
        column_album.props.expand = True
        column_album.pack_start(album_renderer, True)
        column_album.set_cell_data_func(
            album_renderer, self._on_list_widget_album_render, None)
        self._view.append_column(column_album)

    def _on_list_widget_duration_render(self, col, cell, model, itr, data):
        item = model[itr][5]
        if item:
            seconds = item.get_duration()
            track_time = utils.seconds_to_string(seconds)
            cell.props.text = '{}'.format(track_time)

    def _on_list_widget_album_render(self, coll, cell, model, _iter, data):
        if not model.iter_is_valid(_iter):
            return

        item = model[_iter][5]
        if item:
            cell.props.text = utils.get_album_title(item)

    def _on_list_widget_icon_render(self, col, cell, model, itr, data):
        track_uri = self.player.url
        if not track_uri:
            cell.props.visible = False
            return

        if model[itr][11] == DiscoveryStatus.FAILED:
            cell.props.icon_name = self._error_icon_name
            cell.props.visible = True
        elif model[itr][5].get_url() == track_uri:
            cell.props.icon_name = self._now_playing_icon_name
            cell.props.visible = True
        else:
            cell.props.visible = False

    @log
    def _on_changes_pending(self, data=None):
        if (self._init
                and not self.selection_mode):
            self.model.clear()
            self._offset = 0
            GLib.idle_add(self.populate)
            grilo.changes_pending['Songs'] = False

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        cols = self._view.get_columns()
        cols[1].props.visible = self.selection_mode

        if (not self.selection_mode
                and grilo.changes_pending['Songs']):
            self._on_changes_pending()

    @log
    def _on_item_activated(self, treeview, path, column):
        """Action performed when clicking on a song

        clicking on star column toggles favorite
        clicking on an other columns launches player

        :param Gtk.TreeView treeview: self._view
        :param Gtk.TreePath path: activated row index
        :param Gtk.TreeViewColumn column: activated column
        """
        if self._star_handler.star_renderer_click:
            self._star_handler.star_renderer_click = False
            return

        if self.selection_mode:
            return

        itr = self.model.get_iter(path)
        if self.model[itr][8] != self._error_icon_name:
            self.player.set_playlist('Songs', None, self.model, itr)
            self.player.set_playing(True)

    @log
    def _on_view_clicked(self, treeview, event):
        """Ctrl+click on self._view triggers selection mode.

        :param Gtk.TreeView treeview: self._view
        :param Gdk.EventButton event: clicked event
        """
        modifiers = Gtk.accelerator_get_default_mod_mask()
        if ((event.state & modifiers) == Gdk.ModifierType.CONTROL_MASK
                and not self.selection_mode):
            self._on_selection_mode_request()

        if self.selection_mode:
            path, col, cell_x, cell_y = treeview.get_path_at_pos(
                event.x, event.y)
            iter_ = self.model.get_iter(path)
            self.model[iter_][6] = not self.model[iter_][6]
            self.update_header_from_selection(len(self.get_selected_songs()))

    @log
    def _update_model(self, player, playlist, current_iter):
        """Updates model when the track changes

        :param player: The main player object
        :param playlist: The current playlist object
        :param current_iter: Iter of the current displayed song
        """
        if self._iter_to_clean:
            self.model[self._iter_to_clean][10] = False
        if not player.running_playlist('Songs', None):
            return False

        pos_str = playlist.get_path(current_iter).to_string()
        iter_ = self.model.get_iter_from_string(pos_str)
        self.model[iter_][10] = True
        path = self.model.get_path(iter_)
        self._view.scroll_to_cell(path, None, False, 0., 0.)
        if self.model[iter_][8] != self._error_icon_name:
            self._iter_to_clean = iter_.copy()
        return False

    def _add_item(self, source, param, item, remaining=0, data=None):
        """Adds track item to the model"""
        if not item and not remaining:
            self._view.set_model(self.model)
            self._window.notifications_popup.pop_loading()
            self._view.show()
            return

        self._offset += 1
        item.set_title(utils.get_media_title(item))
        artist = utils.get_artist_name(item)

        if not item.get_url():
            return

        self.model.insert_with_valuesv(
            -1, [2, 3, 5, 9],
            [utils.get_media_title(item), artist, item, item.get_favourite()])

    @log
    def populate(self):
        """Populates the view"""
        self._init = True
        if grilo.tracker:
            self._window.notifications_popup.push_loading()
            GLib.idle_add(grilo.populate_songs, self._offset, self._add_item)

    @log
    def get_selected_songs(self, callback=None):
        """Returns a list of selected songs

        In this view this will be the all the songs selected
        :returns: All selected songs
        :rtype: A list of songs
        """
        selected_songs = [row[5] for row in self.model if row[6]]
        if not callback:
            return selected_songs
        callback(selected_songs)
