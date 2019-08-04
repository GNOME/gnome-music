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
from gi.repository import Gdk, Gtk, Pango

from gnomemusic.coresong import CoreSong
from gnomemusic.player import PlayerPlaylist
from gnomemusic.utils import SongStateIcon
from gnomemusic.views.baseview import BaseView
from gnomemusic.widgets.starhandlerwidget import StarHandlerWidget

import gnomemusic.utils as utils


class SongsView(BaseView):
    """Main view of all songs sorted artistwise

    Consists all songs along with songname, star, length, artist
    and the album name.
    """

    def __init__(self, application):
        """Initialize

        :param GtkApplication window: The application object
        """
        self._coremodel = application.props.coremodel
        super().__init__('songs', _("Songs"), application)

        self._iter_to_clean = None

        self._view.get_style_context().add_class('songs-list-old')

        self._add_list_renderers()

        self._playlist_model = self._coremodel.props.playlist_sort

        self._player = application.props.player
        self._player.connect('song-changed', self._update_model)

        self._model = self._view.props.model
        self._view.show()

    def _setup_view(self):
        view_container = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self._box.pack_start(view_container, True, True, 0)

        self._view = Gtk.TreeView()
        self._view.props.headers_visible = False
        self._view.props.valign = Gtk.Align.START
        self._view.props.model = self._coremodel.props.songs_gtkliststore
        self._view.props.activate_on_single_click = True

        self._ctrl = Gtk.GestureMultiPress().new(self._view)
        self._ctrl.props.propagation_phase = Gtk.PropagationPhase.CAPTURE
        self._ctrl.connect("released", self._on_view_clicked)

        self._view.get_selection().props.mode = Gtk.SelectionMode.SINGLE
        self._view.connect('row-activated', self._on_item_activated)

        view_container.add(self._view)

        self._view.props.visible = True
        view_container.props.visible = True

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
            "Selected", selection_renderer, active=1)
        column_selection.props.visible = False
        column_selection.props.fixed_width = 48
        self._view.append_column(column_selection)

        title_renderer = Gtk.CellRendererText(
            xpad=0, xalign=0.0, yalign=0.5, height=48,
            ellipsize=Pango.EllipsizeMode.END)
        column_title = Gtk.TreeViewColumn("Title", title_renderer, text=2)
        column_title.props.expand = True
        column_title.set_cell_data_func(
            title_renderer, self._on_list_widget_title_render, None)
        self._view.append_column(column_title)

        artist_renderer = Gtk.CellRendererText(
            xpad=32, ellipsize=Pango.EllipsizeMode.END)
        column_artist = Gtk.TreeViewColumn("Artist", artist_renderer, text=3)
        column_artist.props.expand = True
        column_artist.set_cell_data_func(
            artist_renderer, self._on_list_widget_artist_render, None)
        self._view.append_column(column_artist)

        album_renderer = Gtk.CellRendererText(
            xpad=32, ellipsize=Pango.EllipsizeMode.END)
        column_album = Gtk.TreeViewColumn("Album", album_renderer, text=4)
        column_album.props.expand = True
        column_album.set_cell_data_func(
            album_renderer, self._on_list_widget_album_render, None)
        self._view.append_column(column_album)

        attrs = Pango.AttrList()
        attrs.insert(Pango.AttrFontFeatures.new("tnum=1"))
        duration_renderer = Gtk.CellRendererText(xalign=1.0, attributes=attrs)
        column_duration = Gtk.TreeViewColumn(
            "Duration", duration_renderer, text=5)
        self._view.append_column(column_duration)

        self._star_handler = StarHandlerWidget(self, 6)
        column_star = Gtk.TreeViewColumn()
        self._view.append_column(column_star)
        self._star_handler.add_star_renderers(column_star)

    def _on_list_widget_album_render(self, coll, cell, model, itr, data):
        if not model.iter_is_valid(itr):
            return

        item = model[itr][7]
        if item:
            cell.props.text = utils.get_album_title(item.props.media)

    def _on_list_widget_artist_render(self, coll, cell, model, itr, data):
        if not model.iter_is_valid(itr):
            return

        item = model[itr][7]
        if item:
            cell.props.text = utils.get_artist_name(item.props.media)

    def _on_list_widget_title_render(self, coll, cell, model, itr, data):
        if not model.iter_is_valid(itr):
            return

        item = model[itr][7]
        if item:
            cell.props.text = utils.get_media_title(item.props.media)

    def _on_list_widget_icon_render(self, col, cell, model, itr, data):
        current_song = self._player.props.current_song
        if current_song is None:
            return

        coresong = model[itr][7]
        if coresong.props.validation == CoreSong.Validation.FAILED:
            cell.props.icon_name = SongStateIcon.ERROR.value
            cell.props.visible = True
        elif coresong.props.grlid == current_song.props.grlid:
            cell.props.icon_name = SongStateIcon.PLAYING.value
            cell.props.visible = True
        else:
            cell.props.visible = False

    def _on_selection_mode_changed(self, widget, data=None):
        if self.get_parent().get_visible_child() != self:
            return

        super()._on_selection_mode_changed(widget, data)

        cols = self._view.get_columns()
        cols[1].props.visible = self.props.selection_mode

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

        if self.props.selection_mode:
            return

        itr = self._view.props.model.get_iter(path)
        coresong = self._view.props.model[itr][7]
        self._coremodel.set_player_model(
            PlayerPlaylist.Type.SONGS, self._view.props.model)

        self._player.play(coresong)

    def _on_view_clicked(self, gesture, n_press, x, y):
        """Ctrl+click on self._view triggers selection mode."""
        _, state = Gtk.get_current_event_state()
        modifiers = Gtk.accelerator_get_default_mod_mask()
        if (state & modifiers == Gdk.ModifierType.CONTROL_MASK
                and not self.props.selection_mode):
            self.props.selection_mode = True

        # FIXME: In selection mode, star clicks might still trigger
        # activation.
        if self.props.selection_mode:
            path = self._view.get_path_at_pos(x, y)
            if path is None:
                return

            iter_ = self._view.props.model.get_iter(path[0])
            new_fav_status = not self._model[iter_][1]
            self._model[iter_][1] = new_fav_status
            self._model[iter_][7].props.selected = new_fav_status

    def _update_model(self, player):
        """Updates model when the song changes

        :param Player player: The main player object
        """
        # iter_to_clean is necessary because of a bug in GtkTreeView
        # See https://gitlab.gnome.org/GNOME/gtk/issues/503
        if self._iter_to_clean:
            self._view.props.model[self._iter_to_clean][9] = False

        index = self._player.props.position
        current_coresong = self._playlist_model[index]
        for idx, liststore in enumerate(self._view.props.model):
            if liststore[7] == current_coresong:
                break

        iter_ = self._view.props.model.get_iter_from_string(str(idx))
        path = self._view.props.model.get_path(iter_)
        self._view.props.model[iter_][9] = True
        self._view.scroll_to_cell(path, None, True, 0.5, 0.5)

        if self._view.props.model[iter_][0] != SongStateIcon.ERROR.value:
            self._iter_to_clean = iter_.copy()

        return False

    def _select(self, value):
        with self._model.freeze_notify():
            itr = self._model.iter_children(None)
            while itr is not None:
                self._model[itr][7].props.selected = value
                self._model[itr][1] = value

                itr = self._model.iter_next(itr)

    def select_all(self):
        self._select(True)

    def deselect_all(self):
        self._select(False)
