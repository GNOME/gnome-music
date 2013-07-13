import os
import sys
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
        if(self._window == null):
            self._window = Window(self)
        self._window.present()

    def Quit(self):
        this.quit();

if __name__ == '__main__':
    app = Application()
    sys.exit(app.run(sys.argv))
