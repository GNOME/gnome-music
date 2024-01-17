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

from enum import IntEnum

from gi.repository import Adw, GObject, Gtk


@Gtk.Template(resource_path="/org/gnome/Music/ui/HeaderBar.ui")
class HeaderBar(Adw.Bin):
    """Headerbar of the application"""

    class State(IntEnum):
        """States the Headerbar can have"""
        MAIN = 0
        CHILD = 1
        SEARCH = 2
        EMPTY = 3

    __gtype_name__ = "HeaderBar"

    _search_button = Gtk.Template.Child()
    _headerbar = Gtk.Template.Child()
    _menu_button = Gtk.Template.Child()

    search_mode_active = GObject.Property(type=bool, default=False)
    stack = GObject.Property(type=Adw.ViewStack)

    def __init__(self, application):
        """Initialize Headerbar

        :param Application application: Application object
        """
        super().__init__()

        self._stack_switcher = Adw.ViewSwitcher(
            focusable=False, halign="center",
            policy=Adw.ViewSwitcherPolicy.WIDE)

        self.bind_property(
            "stack", self._stack_switcher, "stack",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "search-mode-active", self._search_button, "active",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

    @GObject.Property
    def state(self):
        """State of the widget

        :returns: Widget state
        :rtype: HeaderBar.State
        """
        return self._state

    @state.setter  # type: ignore
    def state(self, value):
        """Set state of the of widget

        This influences the look and functionality of the headerbar.

        :param HeaderBar.State value: Widget state
        """
        self._state = value
        self._update()

        search_visible = self.props.state != HeaderBar.State.SEARCH
        self._search_button.props.visible = search_visible

        if value == HeaderBar.State.EMPTY:
            self._search_button.props.sensitive = False
            self._stack_switcher.hide()
        else:
            self._search_button.props.sensitive = True
            self._stack_switcher.show()

    def _update(self):
        if self.props.state != HeaderBar.State.MAIN:
            self._headerbar.props.title_widget = None
        else:
            self._headerbar.props.title_widget = self._stack_switcher

        self._menu_button.props.visible = (
            self.props.state in [HeaderBar.State.MAIN, HeaderBar.State.EMPTY]
        )
