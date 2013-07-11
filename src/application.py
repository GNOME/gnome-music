from gi.repository import Gtk, Gio, GLib

class Application(gtk.Application):
    def __init__(self):
        super().__init__(
            application_id: 'org.gnome.Music',
            flags: gio.ApplicationFlags.FLAGS_NONE,
            inactivity_timeout: 12000
        )
        Glib.set_application_name("Music")


