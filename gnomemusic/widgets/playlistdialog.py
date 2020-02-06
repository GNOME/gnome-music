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

from gi.repository import GObject, Gtk

from gnomemusic import log
from gnomemusic.grilowrappers.grltrackerplaylists import Playlist
from gnomemusic.widgets.playlistdialogrow import PlaylistDialogRow
from gnomemusic.widgets.notificationspopup import ErrorNotification


@Gtk.Template(resource_path="/org/gnome/Music/ui/PlaylistDialog.ui")
class PlaylistDialog(Gtk.Dialog):
    """Dialog for adding items to a playlist"""

    __gtype_name__ = 'PlaylistDialog'

    selected_playlist = GObject.Property(type=Playlist, default=None)

    _add_playlist_stack = Gtk.Template.Child()
    _normal_box = Gtk.Template.Child()
    _empty_box = Gtk.Template.Child()
    _title_bar = Gtk.Template.Child()
    _listbox = Gtk.Template.Child()
    _cancel_button = Gtk.Template.Child()
    _select_button = Gtk.Template.Child()
    _new_playlist_button = Gtk.Template.Child()
    _new_playlist_entry = Gtk.Template.Child()
    _first_playlist_button = Gtk.Template.Child()
    _first_playlist_entry = Gtk.Template.Child()

    def __repr__(self):
        return '<PlaylistDialog>'

    @log
    def __init__(self, parent):
        super().__init__()

        self._add_playlist_button = None
        self._add_playlist_entry = None

        self.props.transient_for = parent
        self.set_titlebar(self._title_bar)
        self._user_playlists_available = False
        self._app = parent._app
        self._coremodel = parent._app.props.coremodel
        self._listbox.bind_model(
            self._coremodel.props.user_playlists_sort,
            self._create_playlist_row)

        self._set_view()

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
    def _create_playlist_row(self, playlist):
        """Adds (non-smart only) playlists to the model"""
        self._user_playlists_available = True
        self._set_view()

        row = PlaylistDialogRow(playlist)

        return row

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
    def _on_selected_rows_changed(self, klass):
        self._add_playlist_entry.props.text = ""
        self._add_playlist_button.props.sensitive = False
        selected_row = self._listbox.get_selected_row()
        if selected_row is not None:
            self.props.selected_playlist = selected_row.props.playlist
        self._select_button.props.sensitive = selected_row is not None

        for row in self._listbox:
            row.props.selected = (row == selected_row)

    @Gtk.Template.Callback()
    @log
    def _on_editing_done(self, sender, data=None):
        def select_and_close_dialog(playlist):
            for row in self._listbox:
                if row.props.playlist == playlist:
                    self._listbox.select_row(row)
                    break
            self.response(Gtk.ResponseType.ACCEPT)

        _all_playlist_name = []
        for pl in self._coremodel.props.playlists :
            _all_playlist_name.append(pl.props.title)

        text = self._add_playlist_entry.props.text
        if(text not in _all_playlist_name):
            self._coremodel.create_playlist(text, select_and_close_dialog)
        else:
            ErrorNotification(self._app.props.window.notifications_popup, "Playlist already exists")

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
        self._listbox.unselect_all()
