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

        # When we create a playlist, Music has to automatically select the
        # new playlists. We use the following flag to know that the playlist
        # being added must be selected
        self._playlist_created = False

        self.listbox = self.ui.get_object('listbox')
        self.listbox.connect('row-selected', self._on_row_selected)
        self.listbox.set_sort_func(utils.compare_playlists_by_name, self)

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

        # Setup and fill the playlists' list
        self.playlists = Playlists.get_default()
        self.playlists.connect('playlist-added', self._on_playlist_added)

        for playlist in self.playlists.get_playlists():
            self._on_playlist_added(self.playlists, playlist)

    @log
    def _on_selection(self, select_button):
        self.dialog_box.response(Gtk.ResponseType.ACCEPT)

    @log
    def _on_cancel_button_clicked(self, cancel_button):
        self.dialog_box.response(Gtk.ResponseType.REJECT)

    @log
    def _on_row_selected(self, listbox, row):
        self._select_button.set_sensitive(row != None)

    @log
    def _on_editing_done(self, sender, data=None):
        if self._new_playlist_entry.get_text() != '':
            self.playlists.create_playlist(self._new_playlist_entry.get_text())
            self._playlist_created = True

    @log
    def _on_playlist_added(self, playlists, playlist):
        """Adds the playlist to the tree list"""

        # Skip static playlists since they're not writable
        if playlist.is_static:
            return

        row = Gtk.ListBoxRow()
        row.playlist = playlist

        label = Gtk.Label(label=playlist.title,
                          margin=12,
                          xalign=0.0)
        row.add(label)
        row.show_all()

        self.listbox.add(row)

        # If this particular playlist was created here, automatically
        # select it and notify the window that we're done
        if self._playlist_created:
            self.listbox.select_row(row)
            self.dialog_box.response(Gtk.ResponseType.ACCEPT)
            return

    @log
    def _on_new_playlist_entry_changed(self, editable, data=None):
        if editable.get_text() != '':
            self._new_playlist_button.set_sensitive(True)
        else:
            self._new_playlist_button.set_sensitive(False)

    @log
    def _on_new_playlist_entry_focused(self, editable, data=None):
        self.listbox.select_row(None)

    @log
    def get_selected(self):
        if self.listbox.get_selected_row():
            return self.listbox.get_selected_row().playlist
        else:
            return None
