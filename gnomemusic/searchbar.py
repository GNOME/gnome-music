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

from enum import IntEnum

from gettext import gettext as _

import gi
gi.require_version('Gd', '1.0')
from gi.repository import Gd, GLib, GObject, Gtk, Pango

from gnomemusic import log
from gnomemusic.grilo import grilo


class BaseModelColumns(IntEnum):
    ID = 0
    NAME = 1
    HEADING_TEXT = 2


class BaseManager(object):

    def __repr__(self):
        return '<BaseManager>'

    @log
    def __init__(self, id_, label, entry):
        self._id = id_
        self._label = label
        self.entry = entry
        self._tag = Gd.TaggedEntryTag()
        self._tag.manager = self
        self.values = []

    @log
    def fill_in_values(self, model):
        if self._id == "search":
            self.values = [
                ['', '', self._label],
                ['search_all', _("All"), ''],
                ['search_artist', _("Artist"), ''],
                ['search_album', _("Album"), ''],
                ['search_composer', _("Composer"), ''],
                ['search_track', _("Track Title"), ''],
            ]
        for value in self.values:
            iter_ = model.append()
            model[iter_][0, 1, 2] = value
        self.selected_id = self.values[1][BaseModelColumns.ID]

    @property
    @log
    def active(self):
        return self.selected_id

    @active.setter
    @log
    def active(self, selected_id):
        if selected_id == "":
            return

        selected_value = [
            x for x in self.values if x[BaseModelColumns.ID] == selected_id]

        if selected_value != []:
            selected_value = selected_value[0]
            self.selected_id = selected_value[BaseModelColumns.ID]

            # If selected values has first entry then it is a default
            # value. No need to set the tag there.
            value_id = selected_value[BaseModelColumns.ID]
            if (value_id != 'search_all'
                    and value_id != 'grl-tracker-source'):
                self._tag.set_label(selected_value[BaseModelColumns.NAME])
                self.entry.add_tag(self._tag)
            else:
                self.entry.remove_tag(self._tag)

    @log
    def reset_to_default(self):
        self.active(self.values[0][BaseModelColumns.ID])


class SourceManager(BaseManager):

    def __repr__(self):
        return '<SourceManager>'

    @log
    def __init__(self, id_, label, entry):
        super().__init__(id_, label, entry)

        self.values.append(['', '', self._label])
        self.values.append(['all', _("All"), ""])
        self.values.append(['grl-tracker-source', _("Local"), ''])

    @log
    def fill_in_values(self, model):
        self._model = model

        super().fill_in_values(model)

        # FIXME: This call should be to this class and not the super
        # class.
        super(SourceManager, self.__class__).active.fset(
            self, 'grl-tracker-source')

    @log
    def add_new_source(self, klass, source):
        value = [source.get_id(), source.get_name(), '']
        iter_ = self._model.append()
        self._model[iter_][0, 1, 2] = value
        self.values.append(value)

    @property
    @log
    def active(self):
        return super().active

    @active.setter
    @log
    def active(self, selected_id):
        if selected_id == "":
            return

        # https://gitlab.gnome.org/GNOME/gnome-music/snippets/31
        super(SourceManager, self.__class__).active.fset(self, selected_id)

        src = grilo.sources[selected_id] if selected_id != 'all' else None
        grilo.search_source = src


class FilterView(object):

    def __repr__(self):
        return '<FilterView>'

    @log
    def __init__(self, manager, dropdown):
        self._manager = manager
        self._dropdown = dropdown

        self._model = Gtk.ListStore.new([
            GObject.TYPE_STRING,  # ID
            GObject.TYPE_STRING,  # NAME
            GObject.TYPE_STRING,  # TEXT
        ])

        self._manager.fill_in_values(self._model)

        self.view = Gtk.TreeView()
        self.view.set_activate_on_single_click(True)
        self.view.set_headers_visible(False)
        self.view.set_enable_search(False)
        self.view.set_model(self._model)
        self.view.get_selection().set_mode(Gtk.SelectionMode.NONE)
        self.view.connect("row-activated", self._row_activated)

        col = Gtk.TreeViewColumn()
        self.view.append_column(col)

        self._head_renderer = Gtk.CellRendererText(
            weight=Pango.Weight.BOLD, weight_set=True)
        col.pack_start(self._head_renderer, False)
        col.add_attribute(
            self._head_renderer, 'text', BaseModelColumns.HEADING_TEXT)
        col.set_cell_data_func(
            self._head_renderer, self._head_visible, True)

        self._radio_renderer = Gtk.CellRendererToggle(
            radio=True, mode=Gtk.CellRendererMode.INERT)
        col.pack_start(self._radio_renderer, False)
        col.set_cell_data_func(
            self._radio_renderer, self._head_visible,
            [False, self._render_radio])

        self._text_renderer = Gtk.CellRendererText()
        col.pack_start(self._text_renderer, True)
        col.add_attribute(self._text_renderer, 'text', BaseModelColumns.NAME)
        col.set_cell_data_func(
            self._text_renderer, self._head_visible, False)

        self.view.show()

    @log
    def _row_activated(self, view, path, col):
        id_ = self._model[self._model.get_iter(path)][BaseModelColumns.ID]
        self._dropdown.do_select(self._manager, id_)
        self._manager.entry.emit('changed')

    @log
    def _render_radio(self, col, cell, model, iter_):
        id_ = model[iter_][BaseModelColumns.ID]
        cell.set_active(self._manager.active == id_)

    @classmethod
    @log
    def _head_visible(cls, col, cell, model, _iter, additional_arguments):
        additional_func = None
        visible = additional_arguments

        if isinstance(additional_arguments, list):
            visible = additional_arguments[0]
            additional_func = additional_arguments[1]

        cell.set_visible(
            visible == (model[_iter][BaseModelColumns.HEADING_TEXT] != ""))

        if additional_func:
            additional_func(col, cell, model, _iter)


class DropDown(Gtk.Revealer):

    def __repr__(self):
        return '<DropDown>'

    @log
    def __init__(self):
        super().__init__(halign=Gtk.Align.CENTER, valign=Gtk.Align.START)

        self._source_manager = None
        self.search_manager = None
        self._search_filter = None

        self._grid = Gtk.Grid(orientation=Gtk.Orientation.HORIZONTAL)

        frame = Gtk.Frame(shadow_type=Gtk.ShadowType.IN, opacity=0.9)
        frame.get_style_context().add_class('documents-dropdown')
        frame.add(self._grid)
        frame.show_all()

        self.add(frame)

    @log
    def initialize_filters(self, searchbar):
        self._source_manager = SourceManager(
            'source', _("Sources"), searchbar._search_entry)
        _source_filter = FilterView(self._source_manager, self)
        self._grid.add(_source_filter.view)

        grilo.connect('new-source-added', self._source_manager.add_new_source)
        grilo._find_sources()

        self.search_manager = BaseManager(
            'search', _("Match"), searchbar._search_entry)
        self._search_filter = FilterView(self.search_manager, self)
        self._grid.add(self._search_filter.view)

        self._grid.show_all()

        self._search_filter.view.set_sensitive(
            self._source_manager.active == 'grl-tracker-source'
        )

    @log
    def do_select(self, manager, id_):
        manager.active = id_
        if manager == self._source_manager:
            self._search_filter.view.set_sensitive(id == 'grl-tracker-source')


class Searchbar(Gtk.SearchBar):

    def __repr__(self):
        return '<Searchbar>'

    @log
    def __init__(self, stack_switcher, search_button, dropdown):
        super().__init__()

        self._timeout = None
        self._stack_switcher = stack_switcher
        self._search_button = search_button
        self._dropdown = dropdown
        self._search_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.CENTER)
        self._search_box.get_style_context().add_class('linked')

        self._search_entry = Gd.TaggedEntry(
            width_request=500, halign=Gtk.Align.CENTER)
        self._search_entry.connect("changed", self._search_entry_timeout)
        self._search_entry.show()
        self._search_box.add(self._search_entry)

        arrow = Gtk.Image.new_from_icon_name(
            'pan-down-symbolic', Gtk.IconSize.BUTTON)
        self._drop_down_button = Gtk.ToggleButton()
        self._drop_down_button.add(arrow)
        self._drop_down_button.get_style_context().add_class('image-button')
        self._drop_down_button.connect(
            "toggled", self._drop_down_button_toggled)
        self._drop_down_button.show_all()
        self._search_box.add(self._drop_down_button)

        self._search_entry.connect(
            "tag-button-clicked", self._tag_button_clicked)

        self._search_box.show_all()
        self.add(self._search_box)

    @log
    def _drop_down_button_toggled(self, *args):
        self._dropdown.set_reveal_child(self._drop_down_button.get_active())

    @log
    def _tag_button_clicked(self, entry, tag_):
        tag_.manager.active = tag_.manager.values[1][BaseModelColumns.ID]
        self._search_entry_changed(None)

    @log
    def _search_entry_timeout(self, widget):
        if self._timeout:
            GLib.source_remove(self._timeout)
        self._timeout = GLib.timeout_add(
            500, self._search_entry_changed, widget)

    @log
    def _search_entry_changed(self, widget):
        self._timeout = None

        search_term = self._search_entry.get_text()
        if grilo.search_source:
            fields_filter = self._dropdown.search_manager.active
        else:
            fields_filter = 'search_all'

        stack = self._stack_switcher.get_stack()
        if search_term != "":
            stack.set_visible_child_name('search')
            view = stack.get_visible_child()
            view.set_search_text(search_term, fields_filter)

        self._drop_down_button.set_active(False)
        self._dropdown.set_reveal_child(False)

        return False

    @log
    def reveal(self, show, clear=True):
        self.set_search_mode(show)
        self._search_button.set_active(show)

        if show:
            self._search_entry.realize()
            if clear:
                self._search_entry.set_text('')
            self._search_entry.grab_focus()
        else:
            self._drop_down_button.set_active(False)

    @log
    def toggle(self):
        self.reveal(not self.get_search_mode())
