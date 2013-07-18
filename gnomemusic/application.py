from gi.repository import Gtk, Gio, GLib, Gdk
from gnomemusic.window import Window


class Application(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self,
                                 application_id='org.gnome.Music',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        GLib.set_application_name("Music")

        cssProviderFile = Gio.File.new_for_uri('resource:///org/gnome/Music/application.css')
        cssProvider = Gtk.CssProvider()
        cssProvider.load_from_file(cssProviderFile)
        screen = Gdk.Screen.get_default()
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(screen, cssProvider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def do_startup(self):
        Gtk.Application.do_startup(self)

    def do_activate(self):
        self._window = Window(self)
        self._window.show()

    def quit(self):
        self.quit()
