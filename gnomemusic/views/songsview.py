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
from gi.repository import Gd, GLib, Gtk, Pango

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
        BaseView.__init__(self, 'songs', _("Songs"),
                          window, Gd.MainViewType.LIST)

        self._offset = 0
        self._iter_to_clean = None

        view_style = self._view.get_generic_view().get_style_context()
        view_style.add_class('songs-list')
        view_style.remove_class('content-view')

        self._add_list_renderers()

        self.player = player
        self.player.connect('playlist-item-changed', self.update_model)

    @log
    def _on_changes_pending(self, data=None):
        if (self._init
                and not self._header_bar._selectionMode):
            self.model.clear()
            self._offset = 0
            GLib.idle_add(self.populate)
            grilo.changes_pending['Songs'] = False

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        if (not self._header_bar._selectionMode
                and grilo.changes_pending['Songs']):
            self._on_changes_pending()

    @log
    def _on_item_activated(self, widget, id, path):
        if self._star_handler.star_renderer_click:
            self._star_handler.star_renderer_click = False
            return

        try:
            itr = self.model.get_iter(path)
        except ValueError as err:
            logger.warn("Error: {}, {}".format(err.__class__, err))
            return

        if self.model[itr][8] != self._error_icon_name:
            self.player.set_playlist('Songs', None, self.model, itr, 5, 11)
            self.player.set_playing(True)

    @log
    def update_model(self, player, playlist, current_iter):
        """Updates model when the track changes

        :param player: The main player object
        :param playlist: The current playlist object
        :param current_iter: Iter of the current displayed song
        """
        if self._iter_to_clean:
            self.model[self._iter_to_clean][10] = False
        if playlist != self.model:
            return False

        self.model[current_iter][10] = True
        path = self.model.get_path(current_iter)
        self._view.get_generic_view().scroll_to_path(path)
        if self.model[current_iter][8] != self._error_icon_name:
            self._iter_to_clean = current_iter.copy()
        return False

    def _add_item(self, source, param, item, remaining=0, data=None):
        """Adds track item to the model"""
        if not item and not remaining:
            self._view.set_model(self.model)
            self._window.pop_loading_notification()
            self._view.show()
            return

        self._offset += 1
        item.set_title(utils.get_media_title(item))
        artist = utils.get_artist_name(item)

        if not item.get_url():
            return

        self.model.insert_with_valuesv(-1, [2, 3, 5, 9], [
            utils.get_media_title(item),
            artist,
            item,
            item.get_favourite()
        ])

    @log
    def _add_list_renderers(self):
        list_widget = self._view.get_generic_view()
        cols = list_widget.get_columns()
        cells = cols[0].get_cells()
        cells[2].set_visible(False)
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
        title_renderer = Gtk.CellRendererText(
            xpad=0, xalign=0.0, yalign=0.5, height=48,
            ellipsize=Pango.EllipsizeMode.END)

        list_widget.add_renderer(title_renderer,
                                 self._on_list_widget_title_render, None)
        cols[0].add_attribute(title_renderer, 'text', 2)
        cols[0].set_expand(True)

        col = Gtk.TreeViewColumn()
        col.set_expand(False)
        self._star_handler.add_star_renderers(list_widget, col)
        list_widget.append_column(col)

        duration_renderer = Gd.StyledTextRenderer(xpad=32, xalign=1.0)
        duration_renderer.add_class('dim-label')
        col = Gtk.TreeViewColumn()
        col.pack_start(duration_renderer, False)
        col.set_cell_data_func(duration_renderer,
                               self._on_list_widget_duration_render, None)
        list_widget.append_column(col)
        artist_renderer = Gd.StyledTextRenderer(
            xpad=32, ellipsize=Pango.EllipsizeMode.END)
        artist_renderer.add_class('dim-label')

        col = Gtk.TreeViewColumn()
        col.set_expand(True)
        col.pack_start(artist_renderer, True)
        col.set_cell_data_func(artist_renderer,
                               self._on_list_widget_artist_render, None)
        col.add_attribute(artist_renderer, 'text', 3)
        list_widget.append_column(col)

        type_renderer = Gd.StyledTextRenderer(
            xpad=32, ellipsize=Pango.EllipsizeMode.END)
        type_renderer.add_class('dim-label')

        col = Gtk.TreeViewColumn()
        col.set_expand(True)
        col.pack_start(type_renderer, True)
        col.set_cell_data_func(type_renderer, self._on_list_widget_type_render,
                               None)
        list_widget.append_column(col)

    def _on_list_widget_title_render(self, col, cell, model, itr, data):
        pass

    def _on_list_widget_duration_render(self, col, cell, model, itr, data):
        item = model[itr][5]
        if item:
            seconds = item.get_duration()
            track_time = utils.seconds_to_string(seconds)
            cell.set_property('text', '{}'.format(track_time))

    def _on_list_widget_artist_render(self, col, cell, model, itr, data):
        pass

    def _on_list_widget_type_render(self, coll, cell, model, itr, data):
        item = model[itr][5]
        if item:
            cell.set_property('text', utils.get_album_title(item))

    def _on_list_widget_icon_render(self, col, cell, model, itr, data):
        track_uri = self.player.currentTrackUri
        if not track_uri:
            cell.set_visible(False)
            return
        if model[itr][11] == DiscoveryStatus.FAILED:
            cell.set_property('icon-name', self._error_icon_name)
            cell.set_visible(True)
        elif model[itr][5].get_url() == track_uri:
            cell.set_property('icon-name', self._now_playing_icon_name)
            cell.set_visible(True)
        else:
            cell.set_visible(False)

    @log
    def populate(self):
        """Populates the view"""
        self._init = True
        if grilo.tracker:
            self._window.push_loading_notification()
            GLib.idle_add(grilo.populate_songs, self._offset, self._add_item)

    @log
    def get_selected_songs(self, callback):
        """Returns a list of selected songs

        In this view this will be the all the songs selected
        :returns: All selected songs
        :rtype: A list of songs
        """
        callback([self.model[self.model.get_iter(path)][5]
                  for path in self._view.get_selection()])
