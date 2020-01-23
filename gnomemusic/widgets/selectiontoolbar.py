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


@Gtk.Template(resource_path='/org/gnome/Music/ui/SelectionToolbar.ui')
class SelectionToolbar(Gtk.ActionBar):

    __gtype_name__ = 'SelectionToolbar'

    _add_to_playlist_button = Gtk.Template.Child()
    _edit_details_button = Gtk.Template.Child()

    __gsignals__ = {
        'add-to-playlist': (GObject.SignalFlags.RUN_FIRST, None, ()),
        "edit-details": (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    selected_items_count = GObject.Property(type=int, default=0, minimum=0)

    def __init__(self):
        super().__init__()

        self._stack = None

        self.connect(
            'notify::selected-items-count', self._on_item_selection_changed)

        self.notify("selected-items-count")

    @Gtk.Template.Callback()
    def _on_add_to_playlist_button_clicked(self, widget):
        self.emit('add-to-playlist')

    @Gtk.Template.Callback()
    def _on_edit_tags_button_clicked(self, widget):
        self.emit("edit-details")

    def _on_item_selection_changed(self, widget, data):
        selection_size = self.props.selected_items_count

        self._add_to_playlist_button.props.sensitive = (selection_size > 0)
        self._edit_details_button.props.sensitive = (selection_size == 1)

    # FIXME: This is a workaround for not being able to pass the stack
    # object via init when using Gtk.Builder.
    @GObject.Property(type=Gtk.Stack, default=None)
    def stack(self):
        """The main GtkStack of the app

        :return: main stack object
        :rtype: GtkStack
        """
        return self._stack

    @stack.setter
    def stack(self, stack):
        """Set the GtkStack object used

        :param GtkStack stack: The GtkStack to use
        """
        if (stack is None
                or (self._stack is not None
                    and self._stack != stack)):
            return
        self._stack = stack
