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

from gi.repository import GObject, Grl, Gtk

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists
import gnomemusic.utils as utils


class PlaylistDialogRow(Gtk.ListBoxRow):

    playlist = GObject.Property(type=Grl.Media, default=None)

    def __repr__(self):
        return "PlaylistDialogRow"

    def __init__(self, playlist):
        """Create a row of the PlaylistDialog

        :param Grl.Media playlist: the associated playlist
        """
        super().__init__()

        self.props.playlist = playlist

        hbox = Gtk.Box()
        self.add(hbox)

        title = utils.get_media_title(playlist)
        label = Gtk.Label(label=title, margin=10, xalign=0.0)
        hbox.pack_start(label, False, False, 0)

        self._selection_icon = Gtk.Image.new_from_icon_name(
            "object-select-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        hbox.pack_start(self._selection_icon, False, False, 0)

        self.get_style_context().add_class("playlistdialog-row")
        self.show_all()
        self._selection_icon.props.visible = False

    def display_selection_icon(self, selected):
        """Displays the selection icon if the row is selected

        :param bool selected: Indicate if the row is selected
        """
        self._selection_icon.props.visible = selected


@Gtk.Template(resource_path="/org/gnome/Music/ui/PlaylistDialog.ui")
class PlaylistDialog(Gtk.Dialog):
    """Dialog for adding items to a playlist"""

    __gtype_name__ = 'PlaylistDialog'

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
    def __init__(self, parent, playlists_todelete):
        super().__init__()

        self._add_playlist_button = None
        self._add_playlist_entry = None

        self.props.transient_for = parent
        self.set_titlebar(self._title_bar)
        self._populate()

        self._playlists_todelete_ids = playlists_todelete.keys()

        self._user_playlists_available = False
        self._playlist = Playlists.get_default()
        self._playlist.connect('playlist-created', self._on_playlist_created)

    @log
    def get_selected(self):
        """Get the selected playlist"""
        selected_row = self._listbox.get_selected_row()

        if not selected_row:
            return None

        return selected_row.props.playlist

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
            self._add_playlist_to_listbox(item)
        if remaining == 0:
            self._set_view()

    @log
    def _add_playlist_to_listbox(self, item):
        """Adds (non-smart only) playlists to the model"""

        # Hide playlists that are going to be deleted
        if item.get_id() in self._playlists_todelete_ids:
            return None

        self._user_playlists_available = True
        row = PlaylistDialogRow(item)
        self._listbox.insert(row, -1)

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
        self._select_button.props.sensitive = (selected_row is not None)

        for row in self._listbox:
            row.display_selection_icon(row == selected_row)

    @Gtk.Template.Callback()
    @log
    def _on_editing_done(self, sender, data=None):
        text = self._add_playlist_entry.props.text
        if text:
            self._playlist.create_playlist(text)

    @log
    def _on_playlist_created(self, playlists, item):
        row = self._add_playlist_to_listbox(item)
        if not row:
            return
        self._listbox.select_row(row)
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
        self._listbox.unselect_all()
