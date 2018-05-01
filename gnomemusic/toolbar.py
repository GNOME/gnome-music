# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Eslam Mostafa <cseslam@gmail.com>
# Copyright (c) 2013 Sai Suman Prayaga <suman.sai14@gmail.com>
# Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
# Copyright (c) 2013 Guillaume Quintard <guillaume.quintard@gmail.com>
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
from gnomemusic.searchbar import Searchbar, DropDown
from gnomemusic.utils import View


class Toolbar(GObject.GObject):

    class State(IntEnum):
        MAIN = 0
        CHILD_VIEW = 1
        SEARCH_VIEW = 2
        EMPTY_VIEW = 3

    def __repr__(self):
        return '<Toolbar>'

    @log
    def __init__(self):
        super().__init__()

        self._selection_mode = False

        self._stack_switcher = Gtk.StackSwitcher(can_focus=False,
                                                 halign="center")
        self._stack_switcher.show()
        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Music/headerbar.ui')
        self.header_bar = self._ui.get_object('header-bar')
        self._search_button = self._ui.get_object('search-button')
        self.dropdown = DropDown()
        self.searchbar = Searchbar(
            self._stack_switcher, self._search_button, self.dropdown)
        self.dropdown.initialize_filters(self.searchbar)
        self._select_button = self._ui.get_object('select-button')
        self._cancel_button = self._ui.get_object('done-button')
        self._back_button = self._ui.get_object('back-button')
        self._selection_menu = self._ui.get_object('selection-menu')
        self._selection_menu_button = self._ui.get_object(
            'selection-menu-button')
        self._selection_menu_label = self._ui.get_object(
            'selection-menu-button-label')

        self._back_button.connect('clicked', self.on_back_button_clicked)
        self._window = self.header_bar.get_parent()

        self.bind_property(
            'selection-mode', self.header_bar, 'show-close-button',
            GObject.BindingFlags.INVERT_BOOLEAN |
            GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            'selection_mode', self._cancel_button, 'visible')
        self.bind_property(
            'selection_mode', self._select_button, 'visible',
            GObject.BindingFlags.INVERT_BOOLEAN)

    @GObject.Property(type=bool, default=False)
    def selection_mode(self):
        return self._selection_mode

    @selection_mode.setter
    def selection_mode(self, mode):
        self._selection_mode = mode

        if mode:
            self.header_bar.get_style_context().add_class('selection-mode')
        else:
            self.header_bar.get_style_context().remove_class('selection-mode')
            self._select_button.set_active(False)

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

        if value == Toolbar.State.EMPTY_VIEW:
            self._search_button.props.sensitive = False
            self._select_button.props.sensitive = False
            self._stack_switcher.hide()
        else:
            self._search_button.props.sensitive = True
            self._select_button.props.sensitive = True
            self._stack_switcher.show()

    @log
    def reset_header_title(self):
        self.header_bar.set_title(_("Music"))
        self.header_bar.set_custom_title(self._stack_switcher)

    @log
    def set_stack(self, stack):
        self._stack_switcher.set_stack(stack)

    @log
    def get_stack(self):
        return self._stack_switcher.get_stack()

    @log
    def set_selection_mode(self, mode):
        self.props.selection_mode = mode

    @log
    def on_back_button_clicked(self, widget=None):
        self._window = self.header_bar.get_parent()
        visible_child = self._window.curr_view.get_visible_child()

        view = self._stack_switcher.get_stack().get_visible_child()
        view._back_button_clicked(view)

        current_view = self._window.curr_view
        if not ((current_view == self._window.views[View.SEARCH]
                 or current_view == self._window.views[View.EMPTY])
                and visible_child != current_view._grid):
            self.props.state = Toolbar.State.MAIN
        else:
            self._search_button.set_visible(True)

        self.searchbar.reveal(False)

    @log
    def _update(self):
        if self.props.selection_mode:
            self.header_bar.set_custom_title(self._selection_menu_button)
        elif self.props.state != Toolbar.State.MAIN:
            self.header_bar.set_custom_title(None)
        else:
            self.reset_header_title()

        self._search_button.set_visible(
            self.props.state != Toolbar.State.SEARCH_VIEW)

        self._back_button.set_visible(
            not self._selection_mode
            and self.props.state != Toolbar.State.MAIN
            and self.props.state != Toolbar.State.EMPTY_VIEW)
