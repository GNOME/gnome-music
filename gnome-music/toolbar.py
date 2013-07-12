from gi.repository import Gtk, Gd

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
        self.headerBar.custom_title = self._stackSwitcher;
        self._searchButton = self._ui.get_object("search-button")
        self._backButton.connect('clicked',self.setState)
        self._closeButton.connect('clicked', self._closeButtonClicked)

    def _closeButtonClicked(self, btn):
        self._closeButton.get_toplevel().close()

    def set_stack(self, stack)
        self._stackSwitcher.set_stack(stack)

    def get_stack(self):
        return self._stackSwitcher.get_stack()

    def setSelectionMode(self, selectionMode):
        self._selectionMode = selectionMode
        if (selectionMode):
            self._selectButton.hide()
            self._cancelButton.show()
            self.headerBar.get_style_context().add_class('selection-mode')
            self._cancelButton.get_style_context().remove_class('selection-mode')
        else:
            self.headerBar.get_style_context().remove_class('selection-mode')
            self._selectButton.set_active(false)
            self._selectButton.show()
            self._cancelButton.hide()
        self._update()

    def setState(self, state, *btn=None):
        self._state = state
        self._update()
        self.emit('state-changed')

    def _update(self):
        if (self._state == ToolbarState.SINGLE or self._selectionMode):
            self.headerBar.custom_title = None
        else:
            self.title = ""
            self.headerBar.custom_title = self._stackSwitcher

        if (self._state == ToolbarState.SINGLE and !self._selectionMode):
            self._backButton.show()
        else:
            self._backButton.hide()

        if (self._selectionMode):
            self.headerBar.custom_title = self._selectionMenuButton
            self._closeSeparator.hide()
            self._closeButton.hide();
        else:
            self._closeSeparator.show()
            self._closeButton.show()

    def _addBackButton(self):
        iconName = (self.get_direction() == Gtk.TextDirection.RTL) ?
            'go-previous-rtl-symbolic' : 'go-previous-symbolic'
        self._backButton = Gd.HeaderSimpleButton(symbolic_icon_name=iconName,
                                                     label=_("Back"))
        self._backButton.connect('clicked', self.setState);
        self.pack_start(self._backButton, False, False, 0);

    def _addSearchButton(self):
        self._searchButton = Gd.HeaderSimpleButton(symbolic_icon_name='folder-saved-search-symbolic',
                                                        label=_("Search"))
        self.pack_end(self._searchButton)
        self._searchButton.show()

    def _addSelectButton(self):
        self._selectButton = Gd.HeaderToggleButton(symbolic_icon_name='object-select-symbolic',
                                                        label= _("Select"))
        self.pack_end(self._selectButton)
        self._selectButton.show()

    def _addCloseButton(self):
        self._closeSeparator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.pack_end(self._closeSeparator)

        self._closeButton = Gd.HeaderSimpleButton(symbolic_icon_name='window-close-symbolic')
        self._closeButton.set_relief(Gtk.ReliefStyle.NONE)
        self._closeButton.connect('clicked', self._closeButtonClicked)
        self.pack_end(self._closeButton);

