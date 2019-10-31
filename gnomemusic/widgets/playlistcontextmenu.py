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

from gi.repository import Gio, Gtk


@Gtk.Template(resource_path='/org/gnome/Music/ui/PlaylistContextMenu.ui')
class PlaylistContextMenu(Gtk.Popover):

    __gtype_name__ = 'PlaylistContextMenu'

    _song_menu = Gtk.Template.Child()

    def __init__(self, application, view):
        """Initialize

        :param GtkApplication application: The Application object
        :param GtkListBox view: The view the popup is relative to
        """
        super().__init__()

        window = application.props.window

        self.props.relative_to = view

        # self.bind_model(self._song_menu, None)

        add_song = Gio.SimpleAction.new("add_song_to_playlist", None)
        window.add_action(add_song)

        play_song = Gio.SimpleAction.new("play_song", None)
        window.add_action(play_song)

        remove_song = Gio.SimpleAction.new("remove_song", None)
        window.add_action(remove_song)
