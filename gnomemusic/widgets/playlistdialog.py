# Copyright 2019 The GNOME Music Developers
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

from __future__ import annotations
from typing import List, Optional
import typing

from gi.repository import Adw, Gtk

from gnomemusic.grilowrappers.playlist import Playlist
from gnomemusic.widgets.playlistdialogrow import PlaylistDialogRow
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.coregrilo import CoreGrilo
    from gnomemusic.coresong import CoreSong


@Gtk.Template(resource_path="/org/gnome/Music/ui/PlaylistDialog.ui")
class PlaylistDialog(Adw.Dialog):
    """Dialog for adding items to a playlist"""

    __gtype_name__ = 'PlaylistDialog'

    _add_playlist_stack = Gtk.Template.Child()
    _bottom_bar = Gtk.Template.Child()
    _normal_box = Gtk.Template.Child()
    _empty_box = Gtk.Template.Child()
    _listbox = Gtk.Template.Child()
    _cancel_button = Gtk.Template.Child()
    _select_button = Gtk.Template.Child()
    _toolbar_view = Gtk.Template.Child()
    _new_playlist_button = Gtk.Template.Child()
    _new_playlist_entry = Gtk.Template.Child()
    _first_playlist_button = Gtk.Template.Child()
    _first_playlist_entry = Gtk.Template.Child()

    def __init__(
            self, application: Application,
            selected_songs: List[CoreSong]) -> None:
        """Initialize PlaylistDialog

        :param Application application: The application object
        :param List[CoreSong] selected_songs: A list of songs to be
            added
        """
        super().__init__()

        self._coregrilo: CoreGrilo = application.props.coregrilo
        self._selected_playlist: Optional[Playlist] = None
        self._selected_songs = selected_songs

        self._add_playlist_button = None
        self._add_playlist_entry = None

        self._user_playlists_available = False

        coremodel = application.props.coremodel
        self._listbox.bind_model(
            coremodel.props.user_playlists_sort, self._create_playlist_row)

        self._set_view()

    def _set_view(self):
        if self._user_playlists_available:
            self._normal_box.show()
            self._add_playlist_stack.props.visible_child = self._normal_box
            self._add_playlist_button = self._new_playlist_button
            self._add_playlist_entry = self._new_playlist_entry
            self._toolbar_view.props.reveal_bottom_bars = True
        else:
            self._empty_box.show()
            self._add_playlist_stack.props.visible_child = self._empty_box
            self._add_playlist_button = self._first_playlist_button
            self._add_playlist_entry = self._first_playlist_entry
            self._toolbar_view.props.reveal_bottom_bars = False

    def _create_playlist_row(self, playlist):
        """Adds (non-smart only) playlists to the model"""
        self._user_playlists_available = True
        self._set_view()

        row = PlaylistDialogRow(playlist)

        return row

    @Gtk.Template.Callback()
    def _on_selection(self, select_button):
        self._selected_playlist.add_songs(self._selected_songs)
        self.force_close()

    @Gtk.Template.Callback()
    def _on_cancel_button_clicked(self, cancel_button):
        self.force_close()

    @Gtk.Template.Callback()
    def _on_selected_rows_changed(self, klass):
        self._add_playlist_entry.props.text = ""
        self._add_playlist_button.props.sensitive = False
        selected_row = self._listbox.get_selected_row()
        if selected_row is not None:
            self._selected_playlist = selected_row.props.playlist
        self._select_button.props.sensitive = selected_row is not None

        for row in self._listbox:
            row.props.selected = (row == selected_row)

    @Gtk.Template.Callback()
    def _on_editing_done(self, sender, data=None):
        def select_and_close_dialog(playlist):
            for row in self._listbox:
                if row.props.playlist == playlist:
                    self._listbox.select_row(row)
                    break

            self._selected_playlist.add_songs(self._selected_songs)
            self.force_close()

        text = self._add_playlist_entry.props.text
        if text:
            self._coregrilo.create_playlist(text, select_and_close_dialog)

    @Gtk.Template.Callback()
    def _on_add_playlist_entry_changed(self, editable, data=None):
        if editable.props.text:
            self._add_playlist_button.props.sensitive = True
        else:
            self._add_playlist_button.props.sensitive = False

    @Gtk.Template.Callback()
    def _on_add_playlist_entry_focused(
            self, controller: Gtk.EventControllerFocus) -> None:
        self._listbox.unselect_all()
