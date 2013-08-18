# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Lubosz Sarnecki <lubosz@gmail.com>
# Copyright (c) 2013 Guillaume Quintard <guillaume.quintard@gmail.com>
# Copyright (c) 2013 Felipe Borges <felipe10borges@gmail.com>
# Copyright (c) 2013 Eslam Mostafa <cseslam@gmail.com>
# Copyright (c) 2013 Shivani Poddar <shivani.poddar92@gmail.com>
# Copyright (c) 2013 Sai Suman Prayaga <suman.sai14@gmail.com>
# Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>.
#
# Gnome Music is free software; you can Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# Gnome Music is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along
# with Gnome Music; if not, write to the Free Software Foundation,
# Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


from gi.repository import Gtk, Gio, GLib, Gdk
from gettext import gettext as _
from gnomemusic.window import Window
from gnomemusic.mpris import MediaPlayer2Service


class Application(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self,
                                 application_id='org.gnome.Music',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        GLib.set_application_name(_('Music'))

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
        about.set_transient_for(self._window)
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
