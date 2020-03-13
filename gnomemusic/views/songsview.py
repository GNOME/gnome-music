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
from gi.repository import Gdk, GObject, Gtk, Pango

from gnomemusic.coresong import CoreSong
from gnomemusic.player import PlayerPlaylist
from gnomemusic.utils import SongStateIcon
from gnomemusic.widgets.starhandlerwidget import StarHandlerWidget


@Gtk.Template(resource_path="/org/gnome/Music/ui/SongsView.ui")
class SongsView(Gtk.Box):
    """Main view of all songs sorted artistwise

    Consists all songs along with songname, star, length, artist
    and the album name.
    """

    __gtype_name__ = "SongsView"

    title = GObject.Property(
        type=str, default=_("Songs"), flags=GObject.ParamFlags.READABLE)

    _duration_renderer = Gtk.Template.Child()
    _now_playing_column = Gtk.Template.Child()
    _now_playing_cell = Gtk.Template.Child()
    _songs_ctrlr = Gtk.Template.Child()
    _songs_view = Gtk.Template.Child()
    _star_column = Gtk.Template.Child()

    def __init__(self, application):
        """Initialize

        :param GtkApplication window: The application object
        """
        super().__init__()

        self.props.name = "songs"

        self._window = application.props.window
        self._coremodel = application.props.coremodel

        self._iter_to_clean = None
        self._set_list_renderers()

        self._playlist_model = self._coremodel.props.playlist_sort
        self._songs_view.props.model = self._coremodel.props.songs_gtkliststore
        self._model = self._songs_view.props.model

        self._player = application.props.player
        self._player.connect('song-changed', self._update_model)

        self._selection_mode = False

        self._window.bind_property(
            "selection-mode", self, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL)

    def _set_list_renderers(self):
        self._now_playing_column.set_cell_data_func(
            self._now_playing_cell, self._on_list_widget_icon_render, None)

        self._star_handler = StarHandlerWidget(self, 6)
        self._star_handler.add_star_renderers(self._star_column)

        attrs = Pango.AttrList()
        attrs.insert(Pango.AttrFontFeatures.new("tnum=1"))
        self._duration_renderer.props.attributes = attrs

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

    @GObject.Property(type=bool, default=False)
    def selection_mode(self):
        """selection mode getter

        :returns: If selection mode is active
        :rtype: bool
        """
        return self._selection_mode

    @selection_mode.setter
    def selection_mode(self, value):
        """selection-mode setter

        :param bool value: Activate selection mode
        """
        if (value == self._selection_mode
                or self.get_parent().get_visible_child() != self):
            return

        self._selection_mode = value
        if self._selection_mode is False:
            self.deselect_all()

        cols = self._songs_view.get_columns()
        cols[1].props.visible = self._selection_mode

    @Gtk.Template.Callback()
    def _on_item_activated(self, treeview, path, column):
        """Action performed when clicking on a song

        clicking on star column toggles favorite
        clicking on an other columns launches player

        :param Gtk.TreeView treeview: self._songs_view
        :param Gtk.TreePath path: activated row index
        :param Gtk.TreeViewColumn column: activated column
        """
        if self._star_handler.star_renderer_click:
            self._star_handler.star_renderer_click = False
            return

        if self.props.selection_mode:
            return

        itr = self._model.get_iter(path)
        coresong = self._model[itr][7]
        self._coremodel.set_player_model(
            PlayerPlaylist.Type.SONGS, self._model)

        self._player.play(coresong)

    @Gtk.Template.Callback()
    def _on_view_clicked(self, gesture, n_press, x, y):
        """Ctrl+click on self._songs_view triggers selection mode."""
        _, state = Gtk.get_current_event_state()
        modifiers = Gtk.accelerator_get_default_mod_mask()
        if (state & modifiers == Gdk.ModifierType.CONTROL_MASK
                and not self.props.selection_mode):
            self.props.selection_mode = True

        # FIXME: In selection mode, star clicks might still trigger
        # activation.
        if self.props.selection_mode:
            path = self._songs_view.get_path_at_pos(x, y)
            if path is None:
                return

            iter_ = self._model.get_iter(path[0])
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
            self._model[self._iter_to_clean][9] = False

        index = self._player.props.position
        current_coresong = self._playlist_model[index]
        for idx, liststore in enumerate(self._model):
            if liststore[7] == current_coresong:
                break

        iter_ = self._model.get_iter_from_string(str(idx))
        path = self._model.get_path(iter_)
        self._model[iter_][9] = True
        self._songs_view.scroll_to_cell(path, None, True, 0.5, 0.5)

        if self._model[iter_][0] != SongStateIcon.ERROR.value:
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
