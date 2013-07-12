from gi.repository import Gtk, Gio, GLib
from gettext import gettext as _

class Window(Gtk.ApplicationWindow):
    def __init__(self, app):
        Gtk.ApplicationWindow.init(self, 
                                    application=app,
                                    title=_('Music'))
        settings = Gio.Settings.new('org.gnome.Music')
        this.set_size_request(887, 640);
        this._setupView();

    def _setupView(self):
        self._box = Gtk.VBox()
        self.views = []
        self._stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE,
            transition_duration=100,
            visible=true)
        
