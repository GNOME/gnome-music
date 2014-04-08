from gi.repository import Gtk, Gd, GObject, Pango, GLib
from gnomemusic.grilo import grilo
from gnomemusic import log
import logging
logger = logging.getLogger(__name__)


class BaseModelColumns():
    ID = 0
    NAME = 1
    HEADING_TEXT = 2


class BaseManager:

    def __init__(self, id, label, entry):
        self.id = id
        self.label = label
        self.entry = entry
        self.tag = Gd.TaggedEntryTag()
        self.tag.manager = self
        self.values = []

    def fill_in_values(self, model):
        if self.id == "search":
            self.values = [
                ["search_all", "All fields", self.label],
                ["search_artist", "Artist", ""],
                ["search_album", "Album", ""],
                ["search_track", "Track", ""],
            ]
        for value in self.values:
            _iter = model.append()
            model.set(_iter, [0, 1, 2], value)
        self.selected_id = self.values[0][BaseModelColumns.ID]

    def get_active(self):
        return self.selected_id

    def set_active(self, selected_id):
        selected_value = [x for x in self.values if x[BaseModelColumns.ID] == selected_id]
        if selected_value != []:
            selected_value = selected_value[0]
            self.selected_id = selected_value[BaseModelColumns.ID]

            # If selected values has non-empty HEADING_TEXT then it is a default value
            # No need to set the tag there
            if selected_value[BaseModelColumns.HEADING_TEXT] == "":
                self.entry.add_tag(self.tag)
                self.tag.set_label(selected_value[BaseModelColumns.NAME])
            else:
                self.entry.remove_tag(self.tag)

    def reset_to_default(self):
        self.set_active(self.values[0][BaseModelColumns.ID])


class SourceManager(BaseManager):
    def fill_in_values(self, model):
        if self.id == "source":
            # First one should always be 'Filesystem'
            src = grilo.sources['grl-filesystem']
            self.values.append([src.get_id(), src.get_name(), self.label])
            for key in grilo.sources:
                source = grilo.sources[key]
                if source.get_id() == 'grl-filesystem':
                    continue
                self.values.append([source.get_id(), source.get_name(), ""])
        super(SourceManager, self).fill_in_values(model)

    def set_active(self, selected_id):
        super(SourceManager, self).set_active(selected_id)
        src = grilo.sources[selected_id]
        grilo.search_source = src

class FilterView():
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
        self.view.connect("row-activated", self._row_activated)

        col = Gtk.TreeViewColumn()
        self.view.append_column(col)

        self._rendererHeading = Gtk.CellRendererText(weight=Pango.Weight.BOLD, weight_set=True)
        col.pack_start(self._rendererHeading, False)
        col.add_attribute(self._rendererHeading, 'text', BaseModelColumns.HEADING_TEXT)
        col.set_cell_data_func(self._rendererHeading, self._visibilityForHeading, True)

        self._rendererRadio = Gtk.CellRendererToggle(radio=True, mode=Gtk.CellRendererMode.INERT)
        col.pack_start(self._rendererRadio, False)
        col.set_cell_data_func(self._rendererRadio, self._visibilityForHeading, [True, self._render_radio])

        self._rendererText = Gtk.CellRendererText()
        col.pack_start(self._rendererText, True)
        col.add_attribute(self._rendererText, 'text', BaseModelColumns.NAME)
        col.set_cell_data_func(self._rendererText, self._visibilityForHeading, True)

        self.view.show()

    def _row_activated(self, view, path, col):
        id = self.model.get_value(self.model.get_iter(path), BaseModelColumns.ID)
        self.dropdown.do_select(self.manager, id)

    def _render_radio(self, col, cell, model, _iter):
        id = model.get_value(_iter, BaseModelColumns.ID)
        cell.set_active(self.manager.get_active() == id)

    def _visibilityForHeading(self, col, cell, model, _iter, additional_arguments):
        additionalFunc = None
        visible = additional_arguments
        if isinstance(additional_arguments, list):
            visible = additional_arguments[0]
            additionalFunc = additional_arguments[1]
        cell.set_visible(visible)
        if additionalFunc:
            additionalFunc(col, cell, model, _iter)


class DropDown(Gd.Revealer):
    def __init__(self):
        Gd.Revealer.__init__(self, halign=Gtk.Align.CENTER, valign=Gtk.Align.START)

        self._grid = Gtk.Grid(orientation=Gtk.Orientation.HORIZONTAL)

        frame = Gtk.Frame(shadow_type=Gtk.ShadowType.IN, opacity=0.9)
        frame.get_style_context().add_class('documents-dropdown')
        frame.add(self._grid)
        frame.show_all()

        self.add(frame)

    def initialize_filters(self, searchbar):
        sourcesManager = SourceManager('source', "Sources", searchbar._search_entry)
        sourcesFilter = FilterView(sourcesManager, self)
        self._grid.add(sourcesFilter.view)

        searchFieldsManager = BaseManager('search', "Search By", searchbar._search_entry)
        searchFieldsFilter = FilterView(searchFieldsManager, self)
        self._grid.add(searchFieldsFilter.view)

        self._grid.show_all()

    def do_select(self, manager, id):
        manager.set_active(id)


class Searchbar(Gd.Revealer):

    @log
    def __init__(self, stack_switcher, search_button, dropdown):
        Gd.Revealer.__init__(self)
        self.timeout = None
        self.stack_switcher = stack_switcher
        self._search_button = search_button
        self.dropdown = dropdown
        self._searchContainer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.CENTER)
        self._searchContainer.get_style_context().add_class('linked')

        self._search_entry = Gd.TaggedEntry(width_request=500, halign=Gtk.Align.CENTER)
        self._search_entry.connect("changed", self.search_entry_timeout)
        self._search_entry.show()
        self.connect("notify::child-revealed", self.prepare_search_filter)
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
        self.view = None
        item.add(self._searchContainer)


    @log
    def _drop_down_button_toggled(self, *args):
        self.dropdown.set_reveal_child(self._dropDownButton.get_active())

    def _search_entry_tag_button_clicked(self, entry, tag):
        tag.manager.reset_to_default()

    def set_view_filter(self, model, itr, user_data):
        if self._search_entry.get_property("visible"):
            search_string = self._search_entry.get_text().lower()
            media = model.get_value(itr, 5)
            searchable_fields = [model.get_value(itr, 2),
                                 model.get_value(itr, 3)]
            if media and media.get_url():
                searchable_fields.append(media.get_title())
            for field in searchable_fields:
                if field and search_string in field.lower():
                    return True
            return False
        return True

    @log
    def prepare_search_filter(self, widget, data):
        self.view = self.stack_switcher.get_stack().get_visible_child()
        if self.view.header_bar._state == 0:
            # album was selected on album view, view needs to be redefined
            self.view = self.view._albumWidget
        if not hasattr(self.view.filter, "visible_function_set"):
            self.view.filter.set_visible_func(self.set_view_filter)
            self.view.filter.visible_function_set = True

    def search_entry_timeout(self, widget):
        if self.timeout:
            GLib.source_remove(self.timeout)
        self.timeout = GLib.timeout_add(500, self.search_entry_changed, widget)

    @log
    def search_entry_changed(self, widget):
        self.search_term = self._search_entry.get_text()
        if self.view:
            self.view._model.clear()
            grilo.search(self.search_term, self.view._add_item)
        #if self.view:
        #    self.view.filter.refilter()

    @log
    def show_bar(self, show):
        self.set_reveal_child(show)
        self._search_button.set_active(show)

        if show:
            self._search_entry.grab_focus()
        else:
            self._search_entry.set_text('')

    @log
    def toggle_bar(self):
        self.show_bar(not self.get_child_revealed())
