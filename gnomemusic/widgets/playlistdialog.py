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

from gi.repository import Gtk, Pango

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists
import gnomemusic.utils as utils


@Gtk.Template(resource_path="/org/gnome/Music/PlaylistDialog.ui")
class PlaylistDialog(Gtk.Dialog):
    """Dialog for adding items to a playlist"""

    __gtype_name__ = 'PlaylistDialog'

    _add_playlist_stack = Gtk.Template.Child()
    _normal_box = Gtk.Template.Child()
    _empty_box = Gtk.Template.Child()
    _title_bar = Gtk.Template.Child()
    _view = Gtk.Template.Child()
    _selection = Gtk.Template.Child()
    _model = Gtk.Template.Child()
    _cancel_button = Gtk.Template.Child()
    _select_button = Gtk.Template.Child()
    _new_playlist_button = Gtk.Template.Child()
    _new_playlist_entry = Gtk.Template.Child()
    _first_playlist_button = Gtk.Template.Child()
    _first_playlist_entry = Gtk.Template.Child()

    def __repr__(self):
        return '<PlaylistDialog>'

    @log
    def __init__(self, parent, playlists_todelete):
        super().__init__()

        self._add_playlist_button = None
        self._add_playlist_entry = None

        self.props.transient_for = parent
        self.set_titlebar(self._title_bar)
        self._add_list_renderers()
        self._populate()

        self._playlists_todelete_ids = playlists_todelete.keys()

        self._user_playlists_available = False
        self._playlist = Playlists.get_default()
        self._playlist.connect('playlist-created', self._on_playlist_created)

    @log
    def get_selected(self):
        """Get the selected playlist"""
        _iter = self._selection.get_selected()[1]

        if not _iter:
            return None

        return self._model[_iter][1]

    @log
    def _add_list_renderers(self):
        type_renderer = Gtk.CellRendererText(
            xpad=8, ypad=8, ellipsize=Pango.EllipsizeMode.END, xalign=0.0)

        col = Gtk.TreeViewColumn("Name", type_renderer, text=0)
        self._view.append_column(col)

    @log
    def _set_view(self):
        if self._user_playlists_available:
            self._normal_box.show()
            self._add_playlist_stack.props.visible_child = self._normal_box
            self._add_playlist_button = self._new_playlist_button
            self._add_playlist_entry = self._new_playlist_entry
        else:
            self._empty_box.show()
            self._add_playlist_stack.props.visible_child = self._empty_box
            self._add_playlist_button = self._first_playlist_button
            self._add_playlist_entry = self._first_playlist_entry

    @log
    def _populate(self):
        grilo.populate_user_playlists(0, self._add_item)

    @log
    def _add_item(self, source, param, item, remaining=0, data=None):
        if item:
            self._add_item_to_model(item)
        if remaining == 0:
            self._set_view()

    @log
    def _add_item_to_model(self, item):
        """Adds (non-static only) playlists to the model"""

        # Hide playlists that are going to be deleted
        if item.get_id() in self._playlists_todelete_ids:
            return None

        self._user_playlists_available = True
        new_iter = self._model.insert_with_valuesv(
            -1, [0, 1], [utils.get_media_title(item), item])

        return new_iter

    @Gtk.Template.Callback()
    @log
    def _on_selection(self, select_button):
        self.response(Gtk.ResponseType.ACCEPT)

    @Gtk.Template.Callback()
    @log
    def _on_cancel_button_clicked(self, cancel_button):
        self.response(Gtk.ResponseType.REJECT)

    @Gtk.Template.Callback()
    @log
    def _on_item_activated(self, view, path, column):
        self._add_playlist_entry.props.text = ""
        self._add_playlist_button.props.sensitive = False

    @Gtk.Template.Callback()
    @log
    def _on_selection_changed(self, selection):
        model, _iter = self._selection.get_selected()
        self._select_button.props.sensitive = _iter is not None

    @Gtk.Template.Callback()
    @log
    def _on_editing_done(self, sender, data=None):
        text = self._add_playlist_entry.props.text
        if text:
            self._playlist.create_playlist(text)

    @log
    def _on_playlist_created(self, playlists, item):
        new_iter = self._add_item_to_model(item)
        if new_iter and self._view.get_columns():
            col0 = self._view.get_columns()[0]
            path = self._model.get_path(new_iter)
            self._view.set_cursor(path, col0, False)
            self._view.row_activated(path, col0)
            self.response(Gtk.ResponseType.ACCEPT)

    @Gtk.Template.Callback()
    @log
    def _on_add_playlist_entry_changed(self, editable, data=None):
        if editable.props.text:
            self._add_playlist_button.props.sensitive = True
        else:
            self._add_playlist_button.props.sensitive = False

    @Gtk.Template.Callback()
    @log
    def _on_add_playlist_entry_focused(self, editable, data=None):
        self._selection.unselect_all()
