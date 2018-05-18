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

from gettext import gettext as _, ngettext
from gi.repository import GObject, Gtk

from gnomemusic import log
from gnomemusic.searchbar import Searchbar, DropDown
from gnomemusic.utils import View


@Gtk.Template(resource_path="/org/gnome/Music/SelectionBarMenuButton.ui")
class SelectionBarMenuButton(Gtk.MenuButton):

    __gtype_name__ = "SelectionBarMenuButton"

    _menu_label = Gtk.Template.Child()

    def __repr__(self):
        return "<SelectionBarMenuButton>"

        self._items_selected = 0

    @log
    def __init__(self):
        super().__init__()

    @GObject.Property(type=int, default=0, minimum=0)
    @log
    def items_selected(self):
        return self._items_selected

    @items_selected.setter
    @log
    def items_selected(self, value):
        self._items_selected = value

        if value > 0:
            text = ngettext(
                "Selected {} item", "Selected {} items", value).format(value)
            self._menu_label.props.label = text
        else:
            self._menu_label.props.label = _("Click on items to select them")


@Gtk.Template(resource_path="/org/gnome/Music/HeaderBar.ui")
class HeaderBar(Gtk.HeaderBar):

    class State(IntEnum):
        MAIN = 0
        CHILD = 1
        SEARCH = 2
        EMPTY = 3

    __gtype_name__ = "HeaderBar"

    _search_button = Gtk.Template.Child()
    _select_button = Gtk.Template.Child()
    _cancel_button = Gtk.Template.Child()
    _back_button = Gtk.Template.Child()

    items_selected = GObject.Property(type=int, default=0, minimum=0)
    stack = GObject.Property(type=Gtk.Stack)

    def __repr__(self):
        return "<HeaderBar>"

    @log
    def __init__(self):
        super().__init__()

        self._selection_mode = False

        self._stack_switcher = Gtk.StackSwitcher(
            can_focus=False, halign="center")
        self._stack_switcher.show()

        self.dropdown = DropDown()
        self.searchbar = Searchbar(
            self._stack_switcher, self._search_button, self.dropdown)
        self.dropdown.initialize_filters(self.searchbar)

        self._selection_menu = SelectionBarMenuButton()

        self.bind_property(
            "selection-mode", self, "show-close-button",
            GObject.BindingFlags.INVERT_BOOLEAN |
            GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "selection-mode", self._cancel_button, "visible")
        self.bind_property(
            "selection-mode", self._select_button, "visible",
            GObject.BindingFlags.INVERT_BOOLEAN)
        self.bind_property(
            "stack", self._stack_switcher, "stack",
            GObject.BindingFlags.BIDIRECTIONAL |
            GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "items-selected", self._selection_menu, "items-selected")

    @GObject.Property(type=bool, default=False)
    @log
    def selection_mode(self):
        return self._selection_mode

    @selection_mode.setter
    @log
    def selection_mode(self, mode):
        self._selection_mode = mode

        if mode:
            self.get_style_context().add_class("selection-mode")
        else:
            self.get_style_context().remove_class("selection-mode")
            self._select_button.props.active = False

        self._update()

    @GObject.Property
    @log
    def state(self):
        return self._state

    @state.setter
    @log
    def state(self, value):
        self._state = value
        self._update()

        search_visible = self.props.state != HeaderBar.State.SEARCH
        self._search_button.props.visible = search_visible

        if value == HeaderBar.State.EMPTY:
            self._search_button.props.sensitive = False
            self._select_button.props.sensitive = False
            self._stack_switcher.hide()
        else:
            self._search_button.props.sensitive = True
            self._select_button.props.sensitive = True
            self._stack_switcher.show()

    @Gtk.Template.Callback()
    @log
    def _on_back_button_clicked(self, widget=None):
        window = self.get_toplevel()

        visible_child = window.curr_view.get_visible_child()

        # FIXME: Stack switch logic should not be here.
        view = self._stack_switcher.props.stack.get_visible_child()
        view._back_button_clicked(view)

        current_view = window.curr_view
        if not ((current_view == window.views[View.SEARCH]
                 or current_view == window.views[View.EMPTY])
                and visible_child != current_view._grid):
            self.props.state = HeaderBar.State.MAIN
        else:
            self._search_button.props.visible = True

        self.searchbar.reveal(False)

    @log
    def _update(self):
        if self.props.selection_mode:
            self.props.custom_title = self._selection_menu
        elif self.props.state != HeaderBar.State.MAIN:
            self.props.custom_title = None
        else:
            self.props.custom_title = self._stack_switcher

        self._back_button.props.visible = (
            not self.props.selection_mode
            and self.props.state != HeaderBar.State.MAIN
            and self.props.state != HeaderBar.State.EMPTY
        )
