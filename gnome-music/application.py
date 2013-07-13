from gi.repository import Gtk, Gio, GLib

from window import Window


class Application(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self,
                                 application_id='org.gnome.Music',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE,
                                 inactivity_timeout=12000)
        GLib.set_application_name("Music")

    def do_startup(self):
        Gtk.Application.startup(self)

    def do_activate(self):
        if self._window is not None:
            self._window = Window(self)
        self._window.present()

    def quit(self):
        self.quit()
