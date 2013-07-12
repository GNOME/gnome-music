from gi.repository import Gtk

class Toolbar():
    def __init__(self):
        self._stackSwithcer = Gtk.StackSwitcher()
        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/music/HeaderBar.ui')
        self.headerBar = self._ui.get_object('header-bar')
        self._selectButton = self._ui.get_object('select-button')
        self._cancelButton = self._ui.get_object('cancel-button')
        self._backButton = self._ui.get_object('back-button')
        self._closeSeparator = self._ui.get_object("close-button-separator")
        self._closeButton = self._ui.get_object("close-button")
        self._selectionMenu = self._ui.get_object("selection-menu")
        self._selectionMenuButton = self._ui.get_object("selection-menu-button")
        self._selectionMenuButton.set_relief(Gtk.ReliefStyle.NONE);
        self.header_bar.custom_title = this._stack_switcher;
        self._searchButton = this._ui.get_object("search-button")
        self._backButton.connect('clicked',self._setState)
        self._closeButton.connect('clicked', self._closeButtonClicked)
