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

from gettext import gettext as _
from gi.repository import Gd, GLib, Gtk, Pango

from gnomemusic import log
from gnomemusic.albumartcache import ArtSize
from gnomemusic.grilo import grilo
from gnomemusic.player import DiscoveryStatus
from gnomemusic.views.baseview import BaseView
import gnomemusic.utils as utils


class SongsView(BaseView):

    def __repr__(self):
        return '<SongsView>'

    @log
    def __init__(self, window, player):
        BaseView.__init__(self, 'songs', _("Songs"), window, Gd.MainViewType.LIST)
        self._items = {}
        self.isStarred = None
        self.iter_to_clean = None
        self.view.get_generic_view().get_style_context()\
            .add_class('songs-list')
        self._iconHeight = 32
        self._iconWidth = 32
        self._add_list_renderers()
        self.view.get_generic_view().get_style_context().remove_class('content-view')
        self.player = player
        self.player.connect('playlist-item-changed', self.update_model)

    @log
    def _on_changes_pending(self, data=None):
        if (self._init and self.header_bar._selectionMode is False):
            self.model.clear()
            self._offset = 0
            GLib.idle_add(self.populate)
            grilo.changes_pending['Songs'] = False

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        if self.header_bar._selectionMode is False and grilo.changes_pending['Songs'] is True:
            self._on_changes_pending()

    @log
    def _on_item_activated(self, widget, id, path):
        if self.star_handler.star_renderer_click:
            self.star_handler.star_renderer_click = False
            return

        try:
            _iter = self.model.get_iter(path)
        except TypeError:
            return
        if self.model.get_value(_iter, 8) != self.errorIconName:
            self.player.set_playlist('Songs', None, self.model, _iter, 5, 11)
            self.player.set_playing(True)

    @log
    def update_model(self, player, playlist, currentIter):
        if self.iter_to_clean:
            self.model.set_value(self.iter_to_clean, 10, False)
        if playlist != self.model:
            return False

        self.model.set_value(currentIter, 10, True)
        path = self.model.get_path(currentIter)
        self.view.get_generic_view().scroll_to_path(path)
        if self.model.get_value(currentIter, 8) != self.errorIconName:
            self.iter_to_clean = currentIter.copy()

        return False

    def _add_item(self, source, param, item, remaining=0, data=None):
        self.window.notification.set_timeout(0)
        if not item:
            if remaining == 0:
                self.view.set_model(self.model)
                self.window.notification.dismiss()
                self.view.show()
            return
        self._offset += 1
        item.set_title(utils.get_media_title(item))
        artist = utils.get_artist_name(item)
        if item.get_url() is None:
            return
        self.model.insert_with_valuesv(
            -1,
            [2, 3, 5, 9],
            [utils.get_media_title(item),
             artist, item, bool(item.get_lyrics())])
        # TODO: change "bool(item.get_lyrics())" --> item.get_favourite() once query works properly

    @log
    def _add_list_renderers(self):
        list_widget = self.view.get_generic_view()
        list_widget.set_halign(Gtk.Align.CENTER)
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
                                              self._on_list_widget_icon_render, None)
        list_widget.insert_column(column_now_playing, 0)

        title_renderer = Gtk.CellRendererText(
            xpad=0,
            xalign=0.0,
            yalign=0.5,
            height=48,
            width=300,
            ellipsize=Pango.EllipsizeMode.END
        )

        list_widget.add_renderer(title_renderer,
                                 self._on_list_widget_title_render, None)
        cols[0].add_attribute(title_renderer, 'text', 2)

        self.star_handler.add_star_renderers(list_widget, cols)

        duration_renderer = Gd.StyledTextRenderer(
            xpad=32,
            xalign=1.0
        )
        duration_renderer.add_class('dim-label')

        col = Gtk.TreeViewColumn()
        col.pack_start(duration_renderer, False)
        col.set_cell_data_func(duration_renderer,
                               self._on_list_widget_duration_render, None)
        list_widget.append_column(col)

        artist_renderer = Gd.StyledTextRenderer(
            xpad=32,
            width=300,
            ellipsize=Pango.EllipsizeMode.END
        )
        artist_renderer.add_class('dim-label')

        col = Gtk.TreeViewColumn()
        col.set_expand(True)
        col.pack_start(artist_renderer, True)
        col.set_cell_data_func(artist_renderer,
                               self._on_list_widget_artist_render, None)
        col.add_attribute(artist_renderer, 'text', 3)
        list_widget.append_column(col)

        type_renderer = Gd.StyledTextRenderer(
            xpad=32,
            width=300,
            ellipsize=Pango.EllipsizeMode.END
        )
        type_renderer.add_class('dim-label')

        col.pack_end(type_renderer, True)
        col.set_cell_data_func(type_renderer,
                               self._on_list_widget_type_render, None)

    def _on_list_widget_title_render(self, col, cell, model, _iter, data):
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
            cell.set_property('text', utils.get_album_title(item))

    def _on_list_widget_icon_render(self, col, cell, model, _iter, data):
        if not self.player.currentTrackUri:
            cell.set_visible(False)
            return

        if model.get_value(_iter, 11) == DiscoveryStatus.FAILED:
            cell.set_property('icon-name', self.errorIconName)
            cell.set_visible(True)
        elif model.get_value(_iter, 5).get_url() == self.player.currentTrackUri:
            cell.set_property('icon-name', self.nowPlayingIconName)
            cell.set_visible(True)
        else:
            cell.set_visible(False)

    @log
    def populate(self):
        self._init = True
        self.window._init_loading_notification()
        GLib.idle_add(grilo.populate_songs, self._offset, self._add_item)

    @log
    def get_selected_tracks(self, callback):
        callback([self.model.get_value(self.model.get_iter(path), 5)
                  for path in self.view.get_selection()])

