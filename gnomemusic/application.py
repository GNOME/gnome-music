from gi.repository import Gtk, Gio, GLib
from gnomemusic.window import Window


class Application(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self,
                                 flags=Gio.ApplicationFlags.FLAGS_NONE,
                                 inactivity_timeout=12000)
        GLib.set_application_name("Music")

    def do_startup(self):
        Gtk.Application.do_startup(self)

    def do_activate(self):
        self._window = Window(self)
        self._window.show_all()

    def quit(self):
        self.quit()
