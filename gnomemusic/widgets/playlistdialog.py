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

from gi.repository import Gtk, Gd, GLib, Pango, Gio

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists
import gnomemusic.utils as utils


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
            [utils.get_media_title(item), False, item]
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
