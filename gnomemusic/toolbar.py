from gi.repository import Gtk, GObject


class ToolbarState:
    SINGLE = 0
    ALBUMS = 1
    ARTISTS = 2
    PLAYLISTS = 3
    SONGS = 4


class Toolbar(GObject.GObject):

    __gsignals__ = {
        'state-changed': (GObject.SIGNAL_RUN_FIRST, None, ())
    }
    _selectionMode = False

    def __init__(self):
        GObject.GObject.__init__(self)
        self._stackSwitcher = Gtk.StackSwitcher()
        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/music/Headerbar.ui')
        self.header_bar = self._ui.get_object('header-bar')
        self._selectButton = self._ui.get_object('select-button')
        self._cancelButton = self._ui.get_object('done-button')
        self._backButton = self._ui.get_object('back-button')
        self._closeSeparator = self._ui.get_object("close-button-separator")
        self._closeButton = self._ui.get_object("close-button")
        self._selectionMenu = self._ui.get_object("selection-menu")
        self._selectionMenuButton = self._ui.get_object("selection-menu-button")
        self._selectionMenuButton.set_relief(Gtk.ReliefStyle.NONE)
        self.header_bar.set_custom_title(self._stackSwitcher)
        self._searchButton = self._ui.get_object("search-button")
        self._backButton.connect('clicked', self.on_back_button_clicked)
        self._closeButton.connect('clicked', self._close_button_clicked)

    def _close_button_clicked(self, btn):
        self._closeButton.get_toplevel().close()

    def set_stack(self, stack):
        self._stackSwitcher.set_stack(stack)

    def get_stack(self):
        return self._stackSwitcher.get_stack()

    def set_selection_mode(self, selectionMode):
        self._selectionMode = selectionMode
        if selectionMode:
            self._selectButton.hide()
            self._cancelButton.show()
            self.header_bar.get_style_context().add_class('selection-mode')
            self._cancelButton.get_style_context().remove_class('selection-mode')
        else:
            self.header_bar.get_style_context().remove_class('selection-mode')
            self._selectButton.set_active(False)
            self._selectButton.show()
            self._cancelButton.hide()
        self._update()

    def on_back_button_clicked(self, widget):
        view = self._stackSwitcher.get_stack().get_visible_child()
        view._back_button_clicked(view)
        self.set_state(ToolbarState.ALBUMS)

    def set_state(self, state, btn=None):
        self._state = state
        self._update()
        self.emit('state-changed')

    def _update(self):
        if self._state == ToolbarState.SINGLE:
            self.header_bar.set_custom_title(None)
            self._backButton.show()
        else:
            self.title = ""
            self.header_bar.set_custom_title(self._stackSwitcher)
            self._backButton.hide()

        if self._selectionMode:
            self.header_bar.set_custom_title(self._selectionMenuButton)
            self._closeSeparator.hide()
            self._closeButton.hide()
        else:
            self._closeSeparator.show()
            self._closeButton.show()
