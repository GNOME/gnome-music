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

from enum import IntEnum

from gettext import gettext as _
from gi.repository import GObject, Gtk

from gnomemusic import log
from gnomemusic.albumartcache import Art
from gnomemusic.query import Query


@Gtk.Template(resource_path="/org/gnome/Music/EmptyView.ui")
class EmptyView(Gtk.Stack):

    class State(IntEnum):
        """Enum for View State
        INITIAL means that Music app has never been initialized and no music
        has been found
        EMPTY means that no music has been found at startup
        SEARCH is the empty search view: no music found during a search
        """
        INITIAL = 0
        EMPTY = 1
        SEARCH = 2

    __gtype_name__ = 'EmptyView'

    _container = Gtk.Template.Child()
    _information_label = Gtk.Template.Child()
    _main_label = Gtk.Template.Child()
    _icon = Gtk.Template.Child()

    def __repr__(self):
        return '<EmptyView>'

    @log
    def __init__(self):
        super().__init__(transition_type=Gtk.StackTransitionType.CROSSFADE)

        self._state = 0
        self._folder_text = self._information_label.get_label()
        self.add(self._container)
        self.show_all()

    @GObject.Property(type=int, default=0, minimum=0, maximum=2)
    @log
    def state(self):
        """Get the state of the empty view

        :returns: The view state
        :rtype: int
        """
        return self._state

    @state.setter
    @log
    def state(self, value):
        """Set the state of the empty view

        :param int value: new state
        """
        self._state = value
        if self._state == EmptyView.State.INITIAL:
            self._set_inital_state()
        elif self._state == EmptyView.State.EMPTY:
            self._set_empty_state()
        elif self._state == EmptyView.State.SEARCH:
            self._set_search_state()

    @log
    def _set_initial_state(self):
        self._set_empty_state()
        self._main_label.set_label('Hey DJ')
        self._main_label.set_margin_bottom(18)

        self._icon.set_from_resource('/org/gnome/Music/initial-state.png')
        self._icon.set_margin_bottom(32)
        self._icon.set_size_request(
            Art.Size.LARGE.width, Art.Size.LARGE.height)

    @log
    def _set_empty_state(self):
        href_text = '<a href="{}">{}</a>'.format(
            Query.MUSIC_URI, _("Music folder"))
        self._information_label.set_label(
            self._folder_text.format(href_text))

    @log
    def _set_search_state(self):
        self._main_label.set_margin_bottom(12)
        self._icon.set_margin_bottom(18)
        self._information_label.set_text(_("Try a different search"))
