from gi.repository import Gtk, Gio, GLib, Gdk
from gettext import gettext as _
from gnomemusic.window import Window
from gnomemusic.mpris import MediaPlayer2Service


class Application(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self,
                                 application_id='org.gnome.Music',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        GLib.set_application_name(_("Music"))

        cssProviderFile = Gio.File.new_for_uri('resource:///org/gnome/Music/application.css')
        cssProvider = Gtk.CssProvider()
        cssProvider.load_from_file(cssProviderFile)
        screen = Gdk.Screen.get_default()
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(screen, cssProvider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_USER)

        self._window = None

    def build_app_menu(self):
        builder = Gtk.Builder()

        builder.add_from_resource('/org/gnome/Music/app-menu.ui')

        menu = builder.get_object('app-menu')
        self.set_app_menu(menu)

        aboutAction = Gio.SimpleAction.new('about', None)
        aboutAction.connect('activate', self.about)
        self.add_action(aboutAction)

        newPlaylistAction = Gio.SimpleAction.new('newPlaylist', None)
        newPlaylistAction.connect('activate', self.new_playlist)
        self.add_action(newPlaylistAction)

        nowPlayingAction = Gio.SimpleAction.new('nowPlaying', None)
        nowPlayingAction.connect('activate', self.now_playing)
        self.add_action(nowPlayingAction)

        quitAction = Gio.SimpleAction.new('quit', None)
        quitAction.connect('activate', self.quit)
        self.add_action(quitAction)

    def new_playlist(self, action, param):
        pass

    def now_playing(self, action, param):
        pass

    def about(self, action, param):
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Music/AboutDialog.ui')
        about = builder.get_object('about_dialog')
        about.connect("response", self.about_response)
        about.show()

    def about_response(self, dialog, response):
        dialog.destroy()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        self.build_app_menu()

    def quit(self, action, param):
        self._window.destroy()

    def do_activate(self):
        if not self._window:
            self._window = Window(self)
            self.service = MediaPlayer2Service(self)
        self._window.present()
