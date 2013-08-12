from gi.repository import Gtk, Gdk, GObject

if Gtk.get_minor_version() > 8:
    from gi.repository.Gtk import StackSwitcher
else:
    from gi.repository.Gd import StackSwitcher


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
    _maximized = False

    def __init__(self):
        GObject.GObject.__init__(self)
        self._stack_switcher = StackSwitcher(margin_top=2, margin_bottom=2)
        self._ui = Gtk.Builder()
        self._ui.add_from_resource('/org/gnome/Music/headerbar.ui')
        self.header_bar = self._ui.get_object('header-bar')
        self._select_button = self._ui.get_object('select-button')
        self._cancel_button = self._ui.get_object('done-button')
        self._back_button = self._ui.get_object('back-button')
        self._close_separator = self._ui.get_object('close-button-separator')
        self._close_button = self._ui.get_object('close-button')
        self._selection_menu = self._ui.get_object('selection-menu')
        self._selection_menu_button = self._ui.get_object('selection-menu-button')
        self._selection_menu_button.set_relief(Gtk.ReliefStyle.NONE)
        self._search_button = self._ui.get_object('search-button')
        if Gtk.Widget.get_default_direction() is Gtk.TextDirection.RTL:
            _back_button_image = self._ui.get_object('back-button-image')
            _back_button_image.set_property('icon-name', 'go-previous-rtl-symbolic')
        self._back_button.connect('clicked', self.on_back_button_clicked)
        self._close_button.connect('clicked', self._close_button_clicked)
        if Gtk.get_minor_version() <= 8:
            self._close_button.connect('hierarchy-changed', self._on_hierarchy_changed)

    def _close_button_clicked(self, btn):
        if Gtk.get_minor_version() > 8:
            self._close_button.get_toplevel().close()
        else:
            self._close_button.get_toplevel().destroy()

    def reset_header_title(self):
        self.header_bar.set_custom_title(self._stack_switcher)

    def _on_hierarchy_changed(self, widget, previous_toplevel):
        if previous_toplevel:
            previous_toplevel.disconnect(self._window_state_handler)
        self._close_button.get_toplevel().add_events(Gdk.EventMask.STRUCTURE_MASK)
        self._window_state_handler = \
            self._close_button.get_toplevel().connect('window-state-event', self._on_window_state_event)

    def _on_window_state_event(self, widget, event):
        if event.changed_mask & Gdk.WindowState.MAXIMIZED:
            self._maximized = bool(event.new_window_state & Gdk.WindowState.MAXIMIZED)
            self._update()

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

        if Gtk.get_minor_version() > 8:
            self._close_separator.set_visible(not self._selectionMode)
            self._close_button.set_visible(not self._selectionMode)
        else:
            self._close_separator.set_visible(not self._selectionMode and self._maximized)
            self._close_button.set_visible(not self._selectionMode and self._maximized)
