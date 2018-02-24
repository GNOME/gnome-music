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

from gettext import gettext as _
from gi.repository import GObject, Gtk

from gnomemusic import log
from gnomemusic.searchbar import Searchbar, DropDown
from gnomemusic.utils import View


class ToolbarState:
    MAIN = 0
    CHILD_VIEW = 1
    SEARCH_VIEW = 2


class Toolbar(GObject.GObject):

    __gsignals__ = {
        'selection-mode-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }
    _selectionMode = False

    def __repr__(self):
        return '<Toolbar>'

    @log
    def __init__(self):
        super().__init__()

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
    def hide_stack(self):
        self._stack_switcher.hide()

    @log
    def show_stack(self):
        self._stack_switcher.show()

    @log
    def set_selection_mode(self, selectionMode):
        self._selectionMode = selectionMode
        if selectionMode:
            self._select_button.hide()
            self._cancel_button.show()
            self.header_bar.get_style_context().add_class('selection-mode')
            self._cancel_button.get_style_context().remove_class(
                'selection-mode')
        else:
            self.header_bar.get_style_context().remove_class('selection-mode')
            self._select_button.set_active(False)
            self._select_button.show()
            self._cancel_button.hide()
        self.emit('selection-mode-changed')
        self._update()

    @log
    def on_back_button_clicked(self, widget=None):
        self._window = self.header_bar.get_parent()
        visible_child = self._window.curr_view.get_visible_child()

        view = self._stack_switcher.get_stack().get_visible_child()
        view._back_button_clicked(view)

        current_view = self._window.curr_view
        if not ((current_view == self._window.views[View.SEARCH]
                 or current_view == self._window.views[View.EMPTY_SEARCH])
                and visible_child != current_view._grid):
            self.set_state(ToolbarState.MAIN)
        else:
            self._search_button.set_visible(True)

        self.searchbar.reveal(False)

    @log
    def set_state(self, state, btn=None):
        self._state = state
        self._update()

    @log
    def _update(self):
        if self._selectionMode:
            self.header_bar.set_custom_title(self._selection_menu_button)
        elif self._state != ToolbarState.MAIN:
            self.header_bar.set_custom_title(None)
        else:
            self.reset_header_title()

        self._search_button.set_visible(
            self._state != ToolbarState.SEARCH_VIEW)
        self._back_button.set_visible(
            not self._selectionMode and self._state != ToolbarState.MAIN)
        self.header_bar.set_show_close_button(not self._selectionMode)
