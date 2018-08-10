# Copyright 2018 The GNOME Music developers
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


@Gtk.Template(resource_path='/org/gnome/Music/SidebarRow.ui')
class SidebarRow(Gtk.ListBoxRow):
    """"""

    __gtype_name__ = 'SidebarRow'

    _check = Gtk.Template.Child()
    _label = Gtk.Template.Child()

    text = GObject.Property(type=str, default='')
    selection_mode = GObject.Property(type=bool, default=False)
    selected = GObject.Property(type=bool, default=False)

    def __repr__(self):
        return '<SidebarRow>'

    @log
    def __init__(self):
        super().__init__()

        self.bind_property('text', self._label, 'label')
        self.bind_property(
            'selected', self._check, 'active',
            GObject.BindingFlags.BIDIRECTIONAL)
        self.bind_property('selection-mode', self._check, 'visible')

        self.show()
