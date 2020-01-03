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
from gnomemusic.grilowrappers.grltrackerplaylists import Playlist
from gnomemusic.widgets.notificationspopup import PlaylistNotification


@Gtk.Template(resource_path='/org/gnome/Music/ui/PlaylistControls.ui')
class PlaylistControls(Gtk.Grid):
    """Widget holding the playlist controls"""

    __gtype_name__ = "PlaylistControls"

    _name_stack = Gtk.Template.Child()
    _name_label = Gtk.Template.Child()
    _rename_entry = Gtk.Template.Child()
    _rename_done_button = Gtk.Template.Child()
    _songs_count_label = Gtk.Template.Child()

    def __init__(self, application):
        """Initialize

        :param GtkApplication application: The application object
        """
        super().__init__()

        self._playlist = None
        self._count_id = 0
        self._binding_count = None
        self._coremodel = application.props.coremodel
        self._window = application.props.window

        self._delete_action = self._window.lookup_action("playlist_delete")
        self._delete_action.connect("activate", self._on_delete_action)
        self._play_action = self._window.lookup_action("playlist_play")
        self._rename_action = self._window.lookup_action("playlist_rename")
        self._rename_action.connect("activate", self._on_rename_action)

    def _on_rename_action(self, menuitem, data=None):
        self._enable_rename_playlist(self.props.playlist)

    def _on_delete_action(self, menutime, data=None):
        PlaylistNotification(
            self._window.notifications_popup, self._coremodel,
            PlaylistNotification.Type.PLAYLIST, self.props.playlist)

        # FIXME: Should Check that the playlist is not playing
        # playlist_id = selection.playlist.props.pl_id
        # if self._player.playing_playlist(
        #         PlayerPlaylist.Type.PLAYLIST, playlist_id):
        #     self._player.stop()
        #     self._window.set_player_visible(False)

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
            self._disable_rename_playlist()

    @Gtk.Template.Callback()
    @log
    def _on_playlist_renamed(self, widget):
        new_name = self._rename_entry.props.text

        if not new_name:
            return

        self.props.playlist.props.title = new_name
        self._disable_rename_playlist()

    @log
    def _on_songs_count_changed(self, klass, data=None):
        self._songs_count_label.props.label = gettext.ngettext(
            "{} Song", "{} Songs", self.props.playlist.count).format(
                self.props.playlist.count)

        self._play_action.props.enabled = self.props.playlist.props.count > 0

    def _enable_rename_playlist(self, pl_torename):
        """Enables rename button and entry

        :param Playlist pl_torename : The playlist to rename
        """
        self._name_stack.props.visible_child_name = "renaming_dialog"
        self._set_rename_entry_text_and_focus(pl_torename.props.title)

    def _disable_rename_playlist(self):
        """Disables rename button and entry"""
        self._name_stack.props.visible_child = self._name_label

    @GObject.Property(type=bool, default=False)
    def rename_active(self):
        """Indicate if renaming dialog is active

        :return: Renaming dialog active
        :rtype: bool
        """

        return self._name_stack.props.visible_child_name == "renaming_dialog"

    @log
    def _set_rename_entry_text_and_focus(self, text):
        self._rename_entry.props.text = text
        self._rename_entry.grab_focus()

    @GObject.Property(
        type=Playlist, default=None, flags=GObject.ParamFlags.READWRITE)
    def playlist(self):
        """Playlist property getter.

        :returns: current playlist
        :rtype: Playlist
        """
        return self._playlist

    @playlist.setter
    def playlist(self, new_playlist):
        """Playlist property setter.

        :param Playlistnew_playlist: new playlist
        """
        if self._count_id > 0:
            self._playlist.disconnect(self._count_id)
            self._count_id = 0
            self._binding_count.unbind()

        self._playlist = new_playlist
        self._disable_rename_playlist()
        self._delete_action.props.enabled = not self._playlist.props.is_smart
        self._rename_action.props.enabled = not self._playlist.props.is_smart

        self._binding_count = self._playlist.bind_property(
            "title", self._name_label, "label",
            GObject.BindingFlags.SYNC_CREATE)
        self._count_id = self._playlist.connect(
            "notify::count", self._on_songs_count_changed)
        self._on_songs_count_changed(None)
