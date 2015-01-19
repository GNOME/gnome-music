# Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2014 Arnel A. Borja <kyoushuu@yahoo.com>
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


from gi.repository import Gtk, Gd, GObject, Pango, GLib
from gettext import gettext as _
from gnomemusic.grilo import grilo
from gnomemusic import log
import logging
logger = logging.getLogger(__name__)


class BaseModelColumns():
    ID = 0
    NAME = 1
    HEADING_TEXT = 2


class BaseManager:
    @log
    def __init__(self, id, label, entry):
        self.id = id
        self.label = label
        self.entry = entry
        self.tag = Gd.TaggedEntryTag()
        self.tag.set_style('button')
        self.tag.manager = self
        self.values = []

    @log
    def fill_in_values(self, model):
        if self.id == "search":
            self.values = [
                ['', '', self.label],
                ['search_all', _("All"), ''],
                ['search_artist', _("Artist"), ''],
                ['search_album', _("Album"), ''],
                ['search_track', _("Track Title"), ''],
            ]
        for value in self.values:
            _iter = model.append()
            model.set(_iter, [0, 1, 2], value)
        self.selected_id = self.values[1][BaseModelColumns.ID]

    @log
    def get_active(self):
        return self.selected_id

    @log
    def set_active(self, selected_id):
        if selected_id == "":
            return

        selected_value = [x for x in self.values if x[BaseModelColumns.ID] == selected_id]
        if selected_value != []:
            selected_value = selected_value[0]
            self.selected_id = selected_value[BaseModelColumns.ID]

            # If selected values has first entry then it is a default value
            # No need to set the tag there
            if selected_value[BaseModelColumns.ID] != self.values[1][BaseModelColumns.ID]:
                self.entry.add_tag(self.tag)
                self.tag.set_label(selected_value[BaseModelColumns.NAME])
            else:
                self.entry.remove_tag(self.tag)

    @log
    def reset_to_default(self):
        self.set_active(self.values[0][BaseModelColumns.ID])


class SourceManager(BaseManager):

    @log
    def __init__(self, id, label, entry):
        super(SourceManager, self).__init__(id, label, entry)
        self.values.append(['', '', self.label])
        self.values.append(['all', _("All"), ""])
        self.values.append(['grl-tracker-source', _("Local"), ''])

    @log
    def fill_in_values(self, model):
        self.model = model
        super(SourceManager, self).fill_in_values(model)

    @log
    def add_new_source(self, klass, source):
        value = [source.get_id(), source.get_name(), '']
        _iter = self.model.append()
        self.model.set(_iter, [0, 1, 2], value)
        self.values.append(value)

    @log
    def set_active(self, selected_id):
        if selected_id == "":
            return

        super(SourceManager, self).set_active(selected_id)
        src = grilo.sources[selected_id] if selected_id != 'all' else None
        grilo.search_source = src


class FilterView():
    @log
    def __init__(self, manager, dropdown):
        self.manager = manager
        self.dropdown = dropdown
        self.model = Gtk.ListStore.new([
            GObject.TYPE_STRING,  # ID
            GObject.TYPE_STRING,  # NAME
            GObject.TYPE_STRING,  # TEXT
        ])
        self.manager.fill_in_values(self.model)

        self.view = Gtk.TreeView()
        self.view.set_activate_on_single_click(True)
        self.view.set_headers_visible(False)
        self.view.set_enable_search(False)
        self.view.set_model(self.model)
        self.view.get_selection().set_mode(Gtk.SelectionMode.NONE)
        self.view.connect("row-activated", self._row_activated)

        col = Gtk.TreeViewColumn()
        self.view.append_column(col)

        self._rendererHeading = Gtk.CellRendererText(weight=Pango.Weight.BOLD, weight_set=True)
        col.pack_start(self._rendererHeading, False)
        col.add_attribute(self._rendererHeading, 'text', BaseModelColumns.HEADING_TEXT)
        col.set_cell_data_func(self._rendererHeading, self._visibilityForHeading, True)

        self._rendererRadio = Gtk.CellRendererToggle(radio=True, mode=Gtk.CellRendererMode.INERT)
        col.pack_start(self._rendererRadio, False)
        col.set_cell_data_func(self._rendererRadio, self._visibilityForHeading, [False, self._render_radio])

        self._rendererText = Gtk.CellRendererText()
        col.pack_start(self._rendererText, True)
        col.add_attribute(self._rendererText, 'text', BaseModelColumns.NAME)
        col.set_cell_data_func(self._rendererText, self._visibilityForHeading, False)

        self.view.show()

    @log
    def _row_activated(self, view, path, col):
        id = self.model.get_value(self.model.get_iter(path), BaseModelColumns.ID)
        self.dropdown.do_select(self.manager, id)
        self.manager.entry.emit('changed')

    @log
    def _render_radio(self, col, cell, model, _iter):
        id = model.get_value(_iter, BaseModelColumns.ID)
        cell.set_active(self.manager.get_active() == id)

    @log
    def _visibilityForHeading(self, col, cell, model, _iter, additional_arguments):
        additionalFunc = None
        visible = additional_arguments
        if isinstance(additional_arguments, list):
            visible = additional_arguments[0]
            additionalFunc = additional_arguments[1]
        cell.set_visible(visible == (model[_iter][BaseModelColumns.HEADING_TEXT] != ""))
        if additionalFunc:
            additionalFunc(col, cell, model, _iter)


class DropDown(Gtk.Revealer):
    @log
    def __init__(self):
        Gtk.Revealer.__init__(self, halign=Gtk.Align.CENTER, valign=Gtk.Align.START)

        self._grid = Gtk.Grid(orientation=Gtk.Orientation.HORIZONTAL)

        frame = Gtk.Frame(shadow_type=Gtk.ShadowType.IN, opacity=0.9)
        frame.get_style_context().add_class('documents-dropdown')
        frame.add(self._grid)
        frame.show_all()

        self.add(frame)

    @log
    def initialize_filters(self, searchbar):
        self.sourcesManager = SourceManager('source', _("Sources"), searchbar._search_entry)
        self.sourcesFilter = FilterView(self.sourcesManager, self)
        self._grid.add(self.sourcesFilter.view)

        grilo.connect('new-source-added', self.sourcesManager.add_new_source)
        grilo._find_sources()

        self.searchFieldsManager = BaseManager('search', _("Match"), searchbar._search_entry)
        self.searchFieldsFilter = FilterView(self.searchFieldsManager, self)
        self._grid.add(self.searchFieldsFilter.view)

        self._grid.show_all()

        self.searchFieldsFilter.view.set_sensitive(
            self.sourcesManager.get_active() == 'grl-tracker-source'
        )

    @log
    def do_select(self, manager, id):
        manager.set_active(id)
        if manager == self.sourcesManager:
            self.searchFieldsFilter.view.set_sensitive(id == 'grl-tracker-source')


class Searchbar(Gtk.Revealer):

    @log
    def __init__(self, stack_switcher, search_button, dropdown):
        Gtk.Revealer.__init__(self)
        self.timeout = None
        self.stack_switcher = stack_switcher
        self._search_button = search_button
        self.dropdown = dropdown
        self._searchContainer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.CENTER)
        self._searchContainer.get_style_context().add_class('linked')

        self._search_entry = Gd.TaggedEntry(width_request=500, halign=Gtk.Align.CENTER)
        self._search_entry.connect("changed", self.search_entry_timeout)
        self._search_entry.show()
        self._searchContainer.add(self._search_entry)

        self._dropDownButtonArrow = Gtk.Arrow(arrow_type=Gtk.ArrowType.DOWN, shadow_type=Gtk.ShadowType.NONE)
        self._dropDownButton = Gtk.ToggleButton()
        self._dropDownButton.add(self._dropDownButtonArrow)
        self._dropDownButton.get_style_context().add_class('raised')
        self._dropDownButton.get_style_context().add_class('image-button')
        self._dropDownButton.connect("toggled", self._drop_down_button_toggled)
        self._dropDownButton.show_all()
        self._searchContainer.add(self._dropDownButton)

        self._search_entry.connect("tag-button-clicked", self._search_entry_tag_button_clicked)

        self._searchContainer.show_all()
        toolbar = Gtk.Toolbar()
        toolbar.get_style_context().add_class("search-bar")
        toolbar.show()
        self.add(toolbar)

        item = Gtk.ToolItem()
        item.set_expand(True)
        item.show()
        toolbar.insert(item, 0)
        item.add(self._searchContainer)

    @log
    def _drop_down_button_toggled(self, *args):
        self.dropdown.set_reveal_child(self._dropDownButton.get_active())

    @log
    def _search_entry_tag_button_clicked(self, entry, tag):
        tag.manager.set_active(tag.manager.values[1][BaseModelColumns.ID])

    @log
    def search_entry_timeout(self, widget):
        if self.timeout:
            GLib.source_remove(self.timeout)
        self.timeout = GLib.timeout_add(500, self.search_entry_changed, widget)

    @log
    def search_entry_changed(self, widget):
        self.timeout = None

        search_term = self._search_entry.get_text()
        if grilo.search_source:
            fields_filter = self.dropdown.searchFieldsManager.get_active()
        else:
            fields_filter = 'search_all'

        stack = self.stack_switcher.get_stack()
        if search_term != "":
            stack.set_visible_child_name('search')
            view = stack.get_visible_child()
            view.set_search_text(search_term, fields_filter)

        self._dropDownButton.set_active(False)
        self.dropdown.set_reveal_child(False)

        return False

    @log
    def show_bar(self, show, clear=True):
        self.set_reveal_child(show)
        self._search_button.set_active(show)

        if show:
            if clear:
                self._search_entry.set_text('')
            self._search_entry.grab_focus()
        else:
            self._dropDownButton.set_active(False)

    @log
    def toggle_bar(self):
        self.show_bar(not self.get_child_revealed())
