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


import gettext

from gi.repository import Gdk, GObject, Gtk
from gnomemusic import log
import gnomemusic.utils as utils


@Gtk.Template(resource_path='/org/gnome/Music/PlaylistControls.ui')
class PlaylistControls(Gtk.Grid):

    __gtype_name__ = "PlaylistControls"

    _name_stack = Gtk.Template.Child()
    _name_label = Gtk.Template.Child()
    _rename_entry = Gtk.Template.Child()
    _rename_done_button = Gtk.Template.Child()
    _songs_count_label = Gtk.Template.Child()
    _menubutton = Gtk.Template.Child()

    def __repr__(self):
        return '<PlaylistControls>'

    @Gtk.Template.Callback()
    @log
    def _on_rename_entry_changed(self, selection):
        self._rename_done_button.set_sensitive(selection.get_text_length() > 0)

    @Gtk.Template.Callback()
    @log
    def _on_rename_entry_key_pressed(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.disable_rename_playlist()

    @log
    def disable_rename_playlist(self):
        """disables rename button and entry"""
        self._name_stack.set_visible_child(self._name_label)
        self._rename_done_button.disconnect(self._handler_rename_done_button)
        self._rename_entry.disconnect(self._handler_rename_entry)

    @log
    def update_songs_count(self, songs_count):
        self._songs_count_label.props.label = gettext.ngettext(
            "{} Song", "{} Songs", songs_count).format(songs_count)

    @log
    def rename_active(self):
        """Indic_songs_count_labelate if renaming dialog is active"""
        return self._name_stack.get_visible_child_name() == 'renaming_dialog'

    @log
    def set_name(self, name):
        self._name_stack.set_visible_child_name(name)

    @GObject.Property
    @log
    def playlist_name(self, playlist_name):
        self._name_label.props.label = playlist_name

    @log
    def get_rename_entry_text(self):
        return self._rename_entry.props.text

    @log
    def set_rename_entry_text_and_focus(self, text):
        self._rename_entry.props.text = text
        self._rename_entry.grab_focus()

    @log
    def connect_rename_entry(self, callback_name, callback_func):
        self._handler_rename_entry = self._rename_entry.connect(
            callback_name, callback_func)

    @log
    def connect_rename_done_btn(self, callback_name, callback_func):
        self._handler_rename_done_button = self._rename_done_button.connect(
            callback_name, callback_func)

    @log
    def enable_rename_playlist(self, pl_torename):
        self.set_name('renaming_dialog')
        self.set_rename_entry_text_and_focus(
            utils.get_media_title(pl_torename))
