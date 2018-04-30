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


class StarImage(Gtk.Image):
    """GtkImage for starring songs"""
    __gtype_name__ = 'StarImage'

    def __repr__(self):
        return '<StarImage>'

    @log
    def __init__(self):
        super().__init__()

        self._favorite = False
        self._hover = False

        self.get_style_context().add_class("star")
        self.show_all()

    @GObject.Property(type=bool, default=False)
    @log
    def favorite(self):
        """Return the current state of the widget

        :return: The state of the widget
        :rtype: bool
        """
        return self._favorite

    @favorite.setter
    @log
    def favorite(self, value):
        """Set favorite

        Set the current widget as favorite or not.

        :param bool value: Value to switch the widget state to
        """
        self._favorite = value

        if self._favorite:
            self.set_state_flags(Gtk.StateFlags.SELECTED, False)
        else:
            self.unset_state_flags(Gtk.StateFlags.SELECTED)

    @GObject.Property(type=bool, default=False)
    @log
    def hover(self):
        return self._hover

    @hover.setter
    @log
    def hover(self, value):
        if value:
            self.set_state_flags(Gtk.StateFlags.PRELIGHT, False)
        else:
            self.unset_state_flags(Gtk.StateFlags.PRELIGHT)
