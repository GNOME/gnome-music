from gi.repository import Gtk, Gd
from gnomemusic import log
import logging
logger = logging.getLogger(__name__)


class Searchbar(Gd.Revealer):

    @log
    def __init__(self, stack_switcher, search_button):
        Gd.Revealer.__init__(self)
        self.stack_switcher = stack_switcher
        self._search_button = search_button
        toolbar = Gtk.Toolbar()
        toolbar.get_style_context().add_class("search-bar")
        toolbar.show()
        self.add(toolbar)
        item = Gtk.ToolItem()
        item.set_expand(True)
        item.show()
        toolbar.insert(item, 0)
        self._search_entry = Gtk.SearchEntry(width_request=500, halign=Gtk.Align.CENTER)
        self._search_entry.connect("changed", self.search_entry_changed)
        self._search_entry.show()
        item.add(self._search_entry)
        self.connect("notify::child-revealed", self.prepare_search_filter)
        self.view = None

    @log
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
