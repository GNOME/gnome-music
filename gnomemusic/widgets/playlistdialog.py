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

from gi.repository import Gtk, Gd, Pango

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists
import gnomemusic.utils as utils


class PlaylistDialog():
    """Dialog for adding items to a playlist"""

    def __repr__(self):
        return '<PlaylistDialog>'

    @log
    def __init__(self, parent, playlist_todelete):
        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Music/PlaylistDialog.ui')

        self._dialog_box = self._ui.get_object('dialog')
        self._dialog_box.set_transient_for(parent)

        self._add_playlist_stack = self._ui.get_object('add_playlist_stack')
        self._normal_state = self._ui.get_object('normal_state')
        self._empty_state = self._ui.get_object('empty_state')
        self._title_bar = self._ui.get_object('headerbar')
        self._dialog_box.set_titlebar(self._title_bar)
        self._setup_dialog()

        self._playlist_todelete = playlist_todelete

        self._playlist = Playlists.get_default()

    @log
    def run(self):
        """Run the playlist dialog"""
        return self._dialog_box.run()

    @log
    def destroy(self):
        """Destroy the playlist dialog"""
        return self._dialog_box.destroy()

    @log
    def _setup_dialog(self):
        self._view = self._ui.get_object('treeview')
        self._view.set_activate_on_single_click(False)
        self._selection = self._ui.get_object('treeview-selection')
        self._selection.connect('changed', self._on_selection_changed)
        self._add_list_renderers()
        self._view.connect('row-activated', self._on_item_activated)

        self._model = self._ui.get_object('liststore')
        self._populate()

        self._cancel_button = self._ui.get_object('cancel-button')
        self._select_button = self._ui.get_object('select-button')
        self._select_button.set_sensitive(False)
        self._cancel_button.connect('clicked', self._on_cancel_button_clicked)
        self._select_button.connect('clicked', self._on_selection)

        def playlists_available_cb(available):
            if available:
                self._add_playlist_stack.set_visible_child(self._normal_state)
                self._new_playlist_button = self._ui.get_object(
                    'new-playlist-button')
                self._new_playlist_entry = self._ui.get_object(
                    'new-playlist-entry')
            else:
                self._add_playlist_stack.set_visible_child(self._empty_state)
                self._new_playlist_button = self._ui.get_object(
                    'create-first-playlist-button')
                self._new_playlist_entry = self._ui.get_object(
                    'first-playlist-entry')

            self._new_playlist_button.set_sensitive(False)
            self._new_playlist_button.connect('clicked',
                                              self._on_editing_done)

            self._new_playlist_entry.connect(
                'changed', self._on_new_playlist_entry_changed)
            self._new_playlist_entry.connect('activate',
                                             self._on_editing_done)
            self._new_playlist_entry.connect(
                'focus-in-event', self._on_new_playlist_entry_focused)

            self._playlist.connect('playlist-created',
                                   self._on_playlist_created)

        grilo.playlists_available(playlists_available_cb)

    @log
    def get_selected(self):
        """Get the selected playlist"""
        _iter = self._selection.get_selected()[1]

        if not _iter or self._model[_iter][1]:
            return None

        return self._model[_iter][2]

    @log
    def _add_list_renderers(self):
        type_renderer = Gd.StyledTextRenderer(
            xpad=8, ypad=8, ellipsize=Pango.EllipsizeMode.END, xalign=0.0)

        cols = Gtk.TreeViewColumn()
        cols.pack_start(type_renderer, True)
        cols.add_attribute(type_renderer, "text", 0)
        cols.set_cell_data_func(type_renderer, self._on_list_text_render)
        self._view.append_column(cols)

    @log
    def _populate(self):
        grilo.populate_playlists(0, self._add_item)

    @log
    def _add_item(self, source, param, item, remaining=0, data=None):
        if item:
            self._add_item_to_model(item)

    @log
    def _add_item_to_model(self, item):
        """Adds (non-static only) playlists to the model"""

        # Don't show static playlists
        if self._playlist.is_static_playlist(item):
            return None

        # Hide playlist that is going to be deleted
        if (self._playlist_todelete is not None
                and item.get_id() == self._playlist_todelete.get_id()):
            return None

        new_iter = self._model.append()
        self._model[new_iter][0, 1, 2] = [
            utils.get_media_title(item), False, item
        ]

        return new_iter

    @log
    def _on_list_text_render(self, col, cell, model, _iter, data):
        editable = model[_iter][1]
        if editable:
            cell.add_class("dim-label")
        else:
            cell.remove_class("dim-label")

    @log
    def _on_selection(self, select_button):
        self._dialog_box.response(Gtk.ResponseType.ACCEPT)

    @log
    def _on_cancel_button_clicked(self, cancel_button):
        self._dialog_box.response(Gtk.ResponseType.REJECT)

    @log
    def _on_item_activated(self, view, path, column):
        self._new_playlist_entry.set_text("")
        self._new_playlist_button.set_sensitive(False)
        _iter = self._model.get_iter(path)
        if self._model[_iter][1]:
            self._view.set_cursor(path, column, True)
        else:
            self._dialog_box.response(Gtk.ResponseType.ACCEPT)

    @log
    def _on_selection_changed(self, selection):
        model, _iter = self._selection.get_selected()

        if _iter is None or self._model[_iter][1]:
            self._select_button.set_sensitive(False)
        else:
            self._select_button.set_sensitive(True)

    @log
    def _on_editing_done(self, sender, data=None):
        if self._new_playlist_entry.get_text() != '':
            self._playlist.create_playlist(self._new_playlist_entry.get_text())

    @log
    def _on_playlist_created(self, playlists, item):
        new_iter = self._add_item_to_model(item)
        if new_iter and self._view.get_columns():
            self._view.set_cursor(self._model.get_path(new_iter),
                                  self._view.get_columns()[0], False)
            self._view.row_activated(self._model.get_path(new_iter),
                                     self._view.get_columns()[0])
            self._dialog_box.response(Gtk.ResponseType.ACCEPT)

    @log
    def _on_new_playlist_entry_changed(self, editable, data=None):
        if editable.get_text() != '':
            self._new_playlist_button.set_sensitive(True)
        else:
            self._new_playlist_button.set_sensitive(False)

    @log
    def _on_new_playlist_entry_focused(self, editable, data=None):
        self._selection.unselect_all()
