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

from gnomemusic.widgets.appmenu import AppMenu


@Gtk.Template(resource_path="/org/gnome/Music/ui/SelectionBarMenuButton.ui")
class SelectionBarMenuButton(Gtk.MenuButton):
    """Button for popup to select all or no items

    The button label indicates the number of items selected.
    """

    __gtype_name__ = "SelectionBarMenuButton"

    _menu_label = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        self._selected_items_count = 0

    @GObject.Property(type=int, default=0, minimum=0)
    def selected_items_count(self):
        """The number of items selected

        :returns: Number of items selected
        :rtype: int
        """
        return self._selected_items_count

    @selected_items_count.setter
    def selected_items_count(self, value):
        """Set the number of items selected

        :param int value: The number of items selected
        """
        self._selected_items_count = value

        if value > 0:
            text = ngettext(
                "Selected {} item", "Selected {} items", value).format(value)
            self._menu_label.props.label = text
        else:
            self._menu_label.props.label = _("Click on items to select them")


@Gtk.Template(resource_path="/org/gnome/Music/ui/HeaderBar.ui")
class HeaderBar(Gtk.HeaderBar):
    """Headerbar of the application"""

    class State(IntEnum):
        """States the Headerbar can have"""
        MAIN = 0
        CHILD = 1
        SEARCH = 2
        EMPTY = 3

    __gtype_name__ = "HeaderBar"

    __gsignals__ = {
        'back-button-clicked': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    _search_button = Gtk.Template.Child()
    _select_button = Gtk.Template.Child()
    _cancel_button = Gtk.Template.Child()
    _back_button = Gtk.Template.Child()
    _menu_button = Gtk.Template.Child()

    search_mode_active = GObject.Property(type=bool, default=False)
    selected_items_count = GObject.Property(type=int, default=0, minimum=0)
    selection_mode_allowed = GObject.Property(type=bool, default=True)
    stack = GObject.Property(type=Gtk.Stack)

    def __init__(self, application):
        """Initialize Headerbar

        :param Application application: Application object
        """
        super().__init__()

        self._selection_mode = False

        self._stack_switcher = Gtk.StackSwitcher(
            can_focus=False, halign="center")
        self._stack_switcher.show()

        self._selection_menu = SelectionBarMenuButton()

        self._menu_button.set_popover(AppMenu(application))

        self.bind_property(
            "selection-mode", self, "show-title-buttons",
            GObject.BindingFlags.INVERT_BOOLEAN
            | GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "selection-mode", self._cancel_button, "visible")
        self.bind_property(
            "selection-mode", self._select_button, "visible",
            GObject.BindingFlags.INVERT_BOOLEAN)
        self.bind_property(
            "selection-mode", self._select_button, "active",
            GObject.BindingFlags.BIDIRECTIONAL)
        self.bind_property(
            "stack", self._stack_switcher, "stack",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "selected-items-count", self._selection_menu,
            "selected-items-count")
        self.bind_property(
            "search-mode-active", self._search_button, "active",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        self.connect(
            "notify::selection-mode-allowed",
            self._on_selection_mode_allowed_changed)

    @GObject.Property(type=bool, default=False)
    def selection_mode(self):
        """Selection mode

        :returns: Selection mode
        :rtype: bool
        """
        return self._selection_mode

    @selection_mode.setter
    def selection_mode(self, mode):
        """Set the selection mode

        :param bool value: Selection mode
        """
        self._selection_mode = mode

        if mode:
            self.get_style_context().add_class("selection-mode")
        else:
            self.get_style_context().remove_class("selection-mode")
            self._select_button.props.active = False

        self._update()

    @GObject.Property
    def state(self):
        """State of the widget

        :returns: Widget state
        :rtype: HeaderBar.State
        """
        return self._state

    @state.setter
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
            self._select_button.props.sensitive = False
            self._stack_switcher.hide()
        else:
            self._search_button.props.sensitive = True
            self._select_button.props.sensitive = True
            self._stack_switcher.show()

    @Gtk.Template.Callback()
    def _on_back_button_clicked(self, widget=None):
        self.emit('back-button-clicked')

    @Gtk.Template.Callback()
    def _on_cancel_button_clicked(self, button):
        self.props.selection_mode = False

    def _update(self):
        if self.props.selection_mode:
            self.props.title_widget = self._selection_menu
        elif self.props.state != HeaderBar.State.MAIN:
            self.props.title_widget= None
        else:
            self.props.title_widget = self._stack_switcher

        self._back_button.props.visible = (
            not self.props.selection_mode
            and self.props.state != HeaderBar.State.MAIN
            and self.props.state != HeaderBar.State.EMPTY
        )

        self._menu_button.props.visible = (
            not self.props.selection_mode
            and self.props.state == HeaderBar.State.MAIN
        )

    def _on_selection_mode_allowed_changed(self, widget, data):
        if self.props.selection_mode_allowed:
            self._select_button.props.sensitive = True
        else:
            self._select_button.props.sensitive = False
