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
        self._stack_switcher = Gtk.StackSwitcher(margin_top=2, margin_bottom=2)
        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Music/Headerbar.ui')
        self.header_bar = self._ui.get_object('header-bar')
        self._select_button = self._ui.get_object('select-button')
        self._cancel_button = self._ui.get_object('done-button')
        self._back_button = self._ui.get_object('back-button')
        self._close_separator = self._ui.get_object("close-button-separator")
        self._close_button = self._ui.get_object("close-button")
        self._selection_menu = self._ui.get_object("selection-menu")
        self._selection_menu_button = self._ui.get_object("selection-menu-button")
        self._selection_menu_button.set_relief(Gtk.ReliefStyle.NONE)
        self.header_bar.set_custom_title(self._stack_switcher)
        self._search_button = self._ui.get_object("search-button")
        self._back_button.connect('clicked', self.on_back_button_clicked)
        self._close_button.connect('clicked', self._close_button_clicked)

    def _close_button_clicked(self, btn):
        self._close_button.get_toplevel().close()

    def reset_header_title(self):
        self.header_bar.set_custom_title(self._stack_switcher)

    def set_stack(self, stack):
        self._stack_switcher.set_stack(stack)

    def get_stack(self):
        return self._stack_switcher.get_stack()

    def set_selection_mode(self, selectionMode):
        self._selectionMode = selectionMode
        if selectionMode:
            self._select_button.hide()
            self._cancel_button.show()
            self.header_bar.get_style_context().add_class('selection-mode')
            self._cancel_button.get_style_context().remove_class('selection-mode')
        else:
            self.header_bar.get_style_context().remove_class('selection-mode')
            self._select_button.set_active(False)
            self._select_button.show()
            self._cancel_button.hide()
        self._update()

    def on_back_button_clicked(self, widget):
        view = self._stack_switcher.get_stack().get_visible_child()
        view._back_button_clicked(view)
        self.set_state(ToolbarState.ALBUMS)

    def set_state(self, state, btn=None):
        self._state = state
        self._update()
        self.emit('state-changed')

    def _update(self):
        if self._state == ToolbarState.SINGLE:
            self.header_bar.set_custom_title(None)
        elif self._selectionMode:
            self.header_bar.set_custom_title(self._selection_menu_button)
        else:
            self.reset_header_title()

        self._back_button.set_visible(not self._selectionMode and self._state == ToolbarState.SINGLE)
        self._close_separator.set_visible(not self._selectionMode)
        self._close_button.set_visible(not self._selectionMode)
