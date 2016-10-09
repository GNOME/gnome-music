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

from gettext import gettext as _
from gi.repository import Gtk

from gnomemusic import log
from gnomemusic.query import Query


class EmptyView(Gtk.Stack):

    def __repr__(self):
        return '<EmptyView>'

    @log
    def __init__(self, window, player):
        Gtk.Stack.__init__(self,
                           transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/gnome/Music/NoMusic.ui')
        widget = self.builder.get_object('container')
        self.update_empty_state_link()
        self.add(widget)
        self.show_all()

    def update_empty_state_link(self):
        label = self.builder.get_object('empty-state-label')
        href_text = '<a href="%s">%s</a>' % (Query.MUSIC_URI,
                                             _("Music folder"))
        label.set_label(label.get_label() % href_text)
