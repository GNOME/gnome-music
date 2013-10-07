from gi.repository import Gtk, Gd, GObject, Pango
from gnomemusic import log
import logging
logger = logging.getLogger(__name__)


class BaseModelColumns():
    ID = 0
    NAME = 1
    HEADING_TEXT = 2


class FilterView():
    def __init__(self, manager):
        self.manager = manager
        self.model = Gtk.ListStore.new([
            GObject.TYPE_STRING,  #ID
            GObject.TYPE_STRING,  #NAME
            GObject.TYPE_STRING,  #TEXT
        ])
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
        col.add_attribute(self._rendererHeading, 'text', BaseModelColumns.HEADING_TEXT);
        col.set_cell_data_func(self._rendererHeading, self._visibilityForHeading, True)

        self._rendererRadio = Gtk.CellRendererToggle(radio=True, mode=Gtk.CellRendererMode.INERT)
        col.pack_start(self._rendererRadio, False)
        col.set_cell_data_func(self._rendererRadio, self._visibilityForHeading, [True, self._render_radio])

        self._rendererText = Gtk.CellRendererText()
        col.pack_start(self._rendererText, True)
        col.add_attribute(self._rendererText, 'text', BaseModelColumns.NAME);
        col.set_cell_data_func(self._rendererText, self._visibilityForHeading, True);

        self.view.show()

    def _row_activated(self, view, path, col):
        id = self.model.get_value(self.model.get_iter(path), BaseModelColumns.ID)
        self.manager.set_active(id)

    def _render_radio(self, col, cell, model, _iter):
        id = model.get_value(_iter, BaseModelColumns.ID)
        cell.set_active(self.manager.get_active() == id)

    def _visibilityForHeading(self, col, cell, model, _iter, additional_arguments):
        heading = model.get_value(_iter, BaseModelColumns.HEADING_TEXT)
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

        sourcesManager = BaseManager("sources_soundcloud")
        sourcesFilter = FilterView(sourcesManager)
        _iter = sourcesFilter.model.append()
        sourcesFilter.model.set(_iter, [0, 1, 2], ["sources_local", "Local", "Sources"])
        _iter = sourcesFilter.model.append()
        sourcesFilter.model.set(_iter, [0, 1, 2], ["sources_grooveshark", "GrooveShark", ""])
        _iter = sourcesFilter.model.append()
        sourcesFilter.model.set(_iter, [0, 1, 2], ["sources_soundcloud", "SoundCloud", ""])
        self._grid.add(sourcesFilter.view)

        searchFieldsManager = BaseManager("search_artist")
        searchFieldsFilter = FilterView(searchFieldsManager)
        _iter = searchFieldsFilter.model.append()
        searchFieldsFilter.model.set(_iter, [0, 1, 2], ["search_all", "All fields", "Search By"])
        _iter = searchFieldsFilter.model.append()
        searchFieldsFilter.model.set(_iter, [0, 1, 2], ["search_artist", "Artist", ""])
        _iter = searchFieldsFilter.model.append()
        searchFieldsFilter.model.set(_iter, [0, 1, 2], ["search_album", "Album", ""])
        self._grid.add(searchFieldsFilter.view)
        searchFieldsFilter.model.set(_iter, [0, 1, 2], ["search_track", "Album", ""])
        self._grid.add(searchFieldsFilter.view)

        typesManager = BaseManager("type_playable")
        typesFilter = FilterView(typesManager)
        _iter = typesFilter.model.append()
        typesFilter.model.set(_iter, [0, 1, 2], ["type_any", "Any", "Type"])
        _iter = typesFilter.model.append()
        typesFilter.model.set(_iter, [0, 1, 2], ["type_playable", "Playable", ""])
        self._grid.add(typesFilter.view)

        self._grid.show_all()

        frame = Gtk.Frame(shadow_type=Gtk.ShadowType.IN, opacity=0.9)
        frame.get_style_context().add_class('documents-dropdown')
        frame.add(self._grid)
        frame.show_all()

        self.add(frame)


class BaseManager:

    def __init__(self, id):
        self.id = id

    def get_active(self):
        return self.id

    def set_active(self, id):
        self.id = id



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
        self._search_entry.connect("changed", self.search_entry_changed)
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

        self._sourceTag = Gd.TaggedEntryTag()
        self._typeTag = Gd.TaggedEntryTag()
        self._matchTag = Gd.TaggedEntryTag()

        self._search_entry.connect("tag-clicked", self._search_entry_tag_clicked)
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

    def _search_entry_tag_clicked(self, *args):
        print("search_entry_tag_clicked")

    def _search_entry_tag_button_clicked(self, *args):
        print("search_entry_tag_button_clicked")

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
            GObject.source_remove(self.timeout)
        self.timeout = GObject.timeout_add(500, self.search_entry_changed, widget)

    @log
    def search_entry_changed(self, widget):
        self.search_term = self._search_entry.get_text()
        if self.view:
            self.view.filter.refilter()

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
