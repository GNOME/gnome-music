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
from gi.repository import Gd, Gtk

from gnomemusic import log
from gnomemusic.toolbar import Toolbar
from gnomemusic.utils import View
from gnomemusic.views.baseview import BaseView


class EmptySearchView(BaseView):

    def __repr__(self):
        return '<EmptySearchView>'

    @log
    def __init__(self, window, player):
        super().__init__('emptysearch', None, window, Gd.MainViewType.LIST)

        self._artist_albums_widget = None

        self.player = player

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Music/NoMusic.ui')
        widget = builder.get_object('container')
        widget.set_vexpand(True)
        widget.set_hexpand(True)
        widget.get_children()[1].get_children()[1].set_text(
            _("Try a different search"))
        widget.show_all()
        self._box.add(widget)

    @log
    def _back_button_clicked(self, widget, data=None):
        self._header_bar.searchbar.reveal(True, False)
        if self.get_visible_child() == self._artist_albums_widget:
            self._artist_albums_widget.destroy()
            self._artist_albums_widget = None
        elif self.get_visible_child() == self._grid:
            self._window.views[View.ALBUM].set_visible_child(
                self._window.views[View.ALBUM]._grid)
            self._window.toolbar.props.state = Toolbar.State.CHILD_VIEW
        self.set_visible_child(self._grid)
