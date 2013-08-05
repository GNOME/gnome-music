from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gd
from gi.repository import GObject


class Searchbar(Gtk.SearchBar):

    __gsignals__ = {
        'item-activated': (GObject.SIGNAL_RUN_FIRST, None, ())
    }

    def __init__(self):
        Gtk.SearchBar.__init__(self)
        #this.parent({show_close_button: false});
        self._search_entry = Gtk.SearchEntry()
        self.connect_entry(self._search_entry)
        self._search_entry.connect("changed", self.search_entry_changed)
        self._search_entry.show()
        self.add(self._search_entry)

    def set_view_filter(self, model, itr, user_data):
        if self._searchEntry.get_property("visible"):
            search_string = self._search_entry.get_text().lower()
            media = model.get_value(itr, 5)
            searchable_fields = []
            artist = media.get_artist()
            if (media and artist):
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

    def _on_item_activated(self):
        self.emit('item-activated')

    def search_entry_changed(self, widget):
        #print (widget)
        self.search_term = self._search_entry.get_text();
        #if self.view:
        #    self.view.filter.refilter()

