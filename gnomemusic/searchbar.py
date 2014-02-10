from gi.repository import Gtk, Gd


class Searchbar(Gd.Revealer):

    def __init__(self, stack_switcher):
        Gd.Revealer.__init__(self)
        self.stack_switcher = stack_switcher
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

    def set_view_filter(self, model, itr, user_data):
        if self._search_entry.get_property("visible"):
            search_string = self._search_entry.get_text().lower()
            media = model.get_value(itr, 5)
            searchable_fields = []
            artist = None
            if media and media.get_url():
                artist = media.get_artist()
            if media and artist:
                searchable_fields = [media.get_artist(),
                                     media.get_album(),
                                     media.get_title()]
            else:
                searchable_fields = [model.get_value(itr, 2),
                                     model.get_value(itr, 3)]
            for field in searchable_fields:
                if field and search_string in field.lower():
                    return True
            return False
        return True

    def prepare_search_filter(self, widget, data):
        self.view = self.stack_switcher.get_stack().get_visible_child()
        if self.view.header_bar._state == 0:
            # album was selected on album view, view needs to be redefined
            self.view = self.view._albumWidget
        if not hasattr(self.view.filter, "visible_function_set"):
            self.view.filter.set_visible_func(self.set_view_filter)
            self.view.filter.visible_function_set = True

    def search_entry_changed(self, widget):
        self.search_term = self._search_entry.get_text()
        if self.view:
            self.view.filter.refilter()
