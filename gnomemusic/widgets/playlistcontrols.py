# Copyright 2018 The GNOME Music Developers
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

import gettext

from gi.repository import Gdk, GObject, Gtk

from gnomemusic import log
import gnomemusic.utils as utils


@Gtk.Template(resource_path='/org/gnome/Music/PlaylistControls.ui')
class PlaylistControls(Gtk.Grid):
    """Widget holding the playlist controls"""

    __gsignals__ = {
        'playlist-renamed': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    __gtype_name__ = "PlaylistControls"

    _name_stack = Gtk.Template.Child()
    _name_label = Gtk.Template.Child()
    _rename_entry = Gtk.Template.Child()
    _rename_done_button = Gtk.Template.Child()
    _songs_count_label = Gtk.Template.Child()
    _menubutton = Gtk.Template.Child()

    songs_count = GObject.Property(
        type=int, default=0, minimum=0, flags=GObject.ParamFlags.READWRITE)
    playlist_name = GObject.Property(
        type=str, default="", flags=GObject.ParamFlags.READWRITE)

    def __repr__(self):
        return '<PlaylistControls>'

    def __init__(self):
        super().__init__()
        self.bind_property("playlist-name", self._name_label, "label")

        self.connect("notify::songs-count", self._on_songs_count_changed)

    @Gtk.Template.Callback()
    @log
    def _on_rename_entry_changed(self, selection):
        selection_length = selection.props.text_length
        self._rename_done_button.props.sensitive = selection_length > 0

    @Gtk.Template.Callback()
    @log
    def _on_rename_entry_key_pressed(self, widget, event):
        (_, keyval) = event.get_keyval()
        if keyval == Gdk.KEY_Escape:
            self.disable_rename_playlist()

    @Gtk.Template.Callback()
    @log
    def _on_playlist_renamed(self, widget):
        new_name = self._rename_entry.props.text

        if not new_name:
            return

        self.props.playlist_name = new_name
        self.disable_rename_playlist()
        self.emit('playlist-renamed', new_name)

    @log
    def _on_songs_count_changed(self, klass, data=None):
        self._songs_count_label.props.label = gettext.ngettext(
            "{} Song", "{} Songs", self.props.songs_count).format(
                self.props.songs_count)

    @log
    def enable_rename_playlist(self, pl_torename):
        """Enables rename button and entry

        :param Grl.Media pl_torename : The playlist to rename
        """
        self._name_stack.props.visible_child_name = "renaming_dialog"
        self._set_rename_entry_text_and_focus(
            utils.get_media_title(pl_torename))

    @log
    def disable_rename_playlist(self):
        """Disables rename button and entry"""
        self._name_stack.props.visible_child = self._name_label

    @GObject.Property(type=bool, default=False)
    def rename_active(self):
        """Indicate if renaming dialog is active

        :return: Renaming dialog active
        :rtype: bool
        """

        return self._name_stack.props.visible_child_name == "renaming_dialog"

    @GObject.Property
    def rename_entry_text(self):
        """Gets the value of the rename entry input

        :return: Contents of rename entry field
        :rtype: string
        """
        return self._rename_entry.props.text

    @log
    def _set_rename_entry_text_and_focus(self, text):
        self._rename_entry.props.text = text
        self._rename_entry.grab_focus()
