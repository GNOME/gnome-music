# Copyright © 2018 The GNOME Music developers
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


@Gtk.Template(resource_path='/org/gnome/Music/ui/SelectionToolbar.ui')
class SelectionToolbar(Gtk.ActionBar):

    __gtype_name__ = 'SelectionToolbar'

    _add_to_playlist_button = Gtk.Template.Child()

    __gsignals__ = {
        'add-to-playlist': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    selected_items_count = GObject.Property(type=int, default=0, minimum=0)

    def __repr__(self):
        return '<SelectionToolbar>'

    @log
    def __init__(self):
        super().__init__()

        self.connect(
            'notify::selected-items-count', self._on_item_selection_changed)

        self.notify("selected-items-count")

    @Gtk.Template.Callback()
    @log
    def _on_add_to_playlist_button_clicked(self, widget):
        self.emit('add-to-playlist')

    @log
    def _on_item_selection_changed(self, widget, data):
        if self.props.selected_items_count > 0:
            self._add_to_playlist_button.props.sensitive = True
        else:
            self._add_to_playlist_button.props.sensitive = False
