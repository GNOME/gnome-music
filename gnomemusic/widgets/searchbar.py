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

from gettext import gettext as _

import gi
gi.require_version('Gd', '1.0')
from gi.repository import Gd, GLib, GObject, Gtk, Pango
from gi.repository.Gd import TaggedEntry  # noqa: F401

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.search import Search


class BaseModelColumns(IntEnum):
    ID = 0
    NAME = 1
    HEADING_TEXT = 2


class BaseManager(GObject.GObject):

    default_value = GObject.Property(type=int, default=1)

    def __repr__(self):
        return '<BaseManager>'

    @log
    def __init__(self, id_, label, entry):
        super().__init__()

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

        value = self.values[self.props.default_value]
        self.selected_id = value[BaseModelColumns.ID]

    @GObject.Property
    def active(self):
        return self.selected_id

    @active.setter
    def active(self, selected_id):
        if selected_id == "":
            return

        selected_value = [
            x for x in self.values if x[BaseModelColumns.ID] == selected_id]

        if selected_value != []:
            selected_value = selected_value[0]
            selected_index = self.values.index(selected_value)
            self.selected_id = selected_value[BaseModelColumns.ID]

            # If selected value is the default one, hide the tag.
            if selected_index == self.props.default_value:
                self.entry.remove_tag(self._tag)
            else:
                self._tag.set_label(selected_value[BaseModelColumns.NAME])
                self.entry.add_tag(self._tag)


class SourceManager(BaseManager):

    def __repr__(self):
        return '<SourceManager>'

    @log
    def __init__(self, id_, label, entry):
        super().__init__(id_, label, entry)

        self.values.append(['', '', self._label])
        self.values.append(['all', _("All"), ""])
        self.values.append(['grl-tracker-source', _("Local"), ''])
        self.props.default_value = 2

        grilo.connect('new-source-added', self._add_new_source)

    @log
    def fill_in_values(self, model):
        self._model = model

        super().fill_in_values(model)

        # FIXME: This call should be to this class and not the super
        # class.
        super(SourceManager, self.__class__).active.fset(
            self, 'grl-tracker-source')

    @log
    def _add_new_source(self, klass, source):
        value = [source.get_id(), source.get_name(), '']
        iter_ = self._model.append()
        self._model[iter_][0, 1, 2] = value
        self.values.append(value)

    @log
    def add_sources(self):
        """Add available Grilo sources

        Adds available Grilo sources to the internal model.
        """
        for id_ in grilo.props.sources:
            self._add_new_source(None, grilo.props.sources[id_])

    @GObject.Property
    def active(self):
        return super().active

    @active.setter
    def active(self, selected_id):
        if selected_id == "":
            return

        # https://gitlab.gnome.org/GNOME/gnome-music/snippets/31
        super(SourceManager, self.__class__).active.fset(self, selected_id)

        src = grilo.sources[selected_id] if selected_id != 'all' else None
        grilo.search_source = src


@Gtk.Template(resource_path="/org/gnome/Music/ui/FilterView.ui")
class FilterView(Gtk.TreeView):
    """TreeView for search entry items

    Shows a radio button with a title.
    """

    __gtype_name__ = 'FilterView'

    __gsignals__ = {
        'selection-changed': (
            GObject.SignalFlags.RUN_FIRST, None, (GObject.GObject, str,)
        ),
    }

    manager = GObject.Property(type=GObject.GObject)

    def __repr__(self):
        return '<FilterView>'

    @log
    def __init__(self):
        super().__init__()

        self._model = Gtk.ListStore.new([
            GObject.TYPE_STRING,  # ID
            GObject.TYPE_STRING,  # NAME
            GObject.TYPE_STRING,  # TEXT
        ])

        self.set_model(self._model)

        col = Gtk.TreeViewColumn()
        self.append_column(col)

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

        self.connect('notify::manager', self._on_manager_changed)

    @log
    def _on_manager_changed(self, klass, value, data=None):
        if value is not None:
            self.props.manager.fill_in_values(self._model)

    @log
    def _render_radio(self, col, cell, model, iter_):
        id_ = model[iter_][BaseModelColumns.ID]
        cell.set_active(self.props.manager.active == id_)

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

    @Gtk.Template.Callback()
    @log
    def _on_row_activated(self, filterview, path, col):
        model = filterview.get_model()
        id_ = model[model.get_iter(path)][BaseModelColumns.ID]

        self.emit('selection-changed', self.props.manager, id_)
        self.props.manager.entry.emit('changed')


@Gtk.Template(resource_path="/org/gnome/Music/ui/DropDown.ui")
class DropDown(Gtk.Revealer):
    """Dropdown source/option selection widget for search

    Shows available search sources and their respective options and
    allows selection.
    """

    __gtype_name__ = 'DropDown'

    _grid = Gtk.Template.Child()
    _search_filter = Gtk.Template.Child()
    _source_filter = Gtk.Template.Child()

    def __repr__(self):
        return '<DropDown>'

    @log
    def __init__(self):
        super().__init__()

        self._source_manager = None
        self.search_manager = None

    @log
    def initialize_filters(self, searchbar):
        self._source_manager = SourceManager(
            'source', _("Sources"), searchbar._search_entry)
        self._source_manager.connect(
            "notify::active", self._on_source_manager_value_changed)

        self._source_filter.props.manager = self._source_manager
        self._source_filter.connect(
            'selection-changed', self._on_selection_changed)

        self._source_manager.add_sources()

        self.search_manager = BaseManager(
            'search', _("Match"), searchbar._search_entry)

        self._search_filter.props.manager = self.search_manager
        self._search_filter.connect(
            'selection-changed', self._on_selection_changed)

        self._search_filter.props.sensitive = (
            self._is_tracker(self._source_manager.props.active))

    @log
    def _on_selection_changed(self, klass, manager, id_):
        manager.active = id_

    @log
    def _on_source_manager_value_changed(self, klass, value):
        is_tracker = self._is_tracker(klass.props.active)
        self._search_filter.props.sensitive = is_tracker
        self.search_manager.props.active = (
            'search_all' if not is_tracker else '')

    @log
    def _is_tracker(self, grilo_id):
        return grilo_id == "grl-tracker-source"


@Gtk.Template(resource_path="/org/gnome/Music/ui/Searchbar.ui")
class Searchbar(Gtk.SearchBar):
    """Widget containing the search entry
    """

    __gtype_name__ = 'Searchbar'

    _search_entry = Gtk.Template.Child()
    _drop_down_button = Gtk.Template.Child()

    search_state = GObject.Property(type=int, default=Search.State.NONE)
    stack = GObject.Property(type=Gtk.Stack)

    def __repr__(self):
        return '<Searchbar>'

    @log
    def __init__(self):
        """Initialize the Searchbar"""
        super().__init__()

        self._timeout = None

        self._dropdown = DropDown()
        self._dropdown.initialize_filters(self)

        self.connect(
            "notify::search-mode-enabled", self._search_mode_changed)
        self.connect('notify::search-state', self._search_state_changed)

    @Gtk.Template.Callback()
    @log
    def _drop_down_button_toggled(self, *args):
        self._dropdown.set_reveal_child(self._drop_down_button.get_active())

    @Gtk.Template.Callback()
    @log
    def _tag_button_clicked(self, entry, tag_):
        default_value = tag_.manager.values[tag_.manager.props.default_value]
        tag_.manager.props.active = default_value[BaseModelColumns.ID]
        self._search_entry_changed(None)

    @Gtk.Template.Callback()
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

        if search_term != "":
            self.props.stack.set_visible_child_name('search')
            view = self.props.stack.get_visible_child()
            view.set_search_text(search_term, fields_filter)
        else:
            self._set_error_style(False)

        self._drop_down_button.set_active(False)
        self._dropdown.set_reveal_child(False)

        return False

    @log
    def _search_mode_changed(self, klass, data):
        if self.props.search_mode_enabled:
            self._search_entry.realize()
            self._search_entry.grab_focus()
        else:
            self._drop_down_button.set_active(False)

    @log
    def _search_state_changed(self, klass, data):
        search_state = self.props.search_state

        if search_state == Search.State.NONE:
            self.props.search_mode_enabled = False
        elif search_state == Search.State.NO_RESULT:
            self._set_error_style(True)
            self.props.stack.props.visible_child_name = 'emptyview'
        else:
            self._set_error_style(False)
            self.props.stack.props.visible_child_name = 'search'

    @log
    def _set_error_style(self, error):
        """Adds error state to searchbar.

        :param bool error: Whether to add error state
        """
        style_context = self._search_entry.get_style_context()
        if error:
            style_context.add_class('error')
        else:
            style_context.remove_class('error')

    @log
    def clear(self):
        """Clear the searchbar."""
        self._search_entry.props.text = ""
