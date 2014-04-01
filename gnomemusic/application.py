# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Lubosz Sarnecki <lubosz@gmail.com>
# Copyright (c) 2013 Guillaume Quintard <guillaume.quintard@gmail.com>
# Copyright (c) 2013 Felipe Borges <felipe10borges@gmail.com>
# Copyright (c) 2013 Eslam Mostafa <cseslam@gmail.com>
# Copyright (c) 2013 Shivani Poddar <shivani.poddar92@gmail.com>
# Copyright (c) 2013 Sai Suman Prayaga <suman.sai14@gmail.com>
# Copyright (c) 2013 Seif Lotfy <seif@lotfy.com>
#
# GNOME Music is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# GNOME Music is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with GNOME Music; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# The GNOME Music authors hereby grant permission for non-GPL compatible
# GStreamer plugins to be used and distributed together with GStreamer
# and GNOME Music.  This permission is above and beyond the permissions
# granted by the GPL license by which GNOME Music is covered.  If you
# modify this code, you may extend this exception to your version of the
# code, but you are not obligated to do so.  If you do not wish to do so,
# delete this exception statement from your version.


from gi.repository import Gtk, Gio, GLib, Gdk, Notify
from gettext import gettext as _
from gnomemusic.window import Window
from gnomemusic.mpris import MediaPlayer2Service
from gnomemusic.notification import NotificationManager
import logging
log = logging.getLogger(__name__)


class Application(Gtk.Application):
    def __init__(self):
        log.debug("Creating app")
        Gtk.Application.__init__(self,
                                 application_id='org.gnome.Music',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        GLib.set_application_name(_("Music"))
        GLib.set_prgname('gnome-music')
        cssProviderFile = Gio.File.new_for_uri('resource:///org/gnome/Music/application.css')
        cssProvider = Gtk.CssProvider()
        cssProvider.load_from_file(cssProviderFile)
        screen = Gdk.Screen.get_default()
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(screen, cssProvider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_USER)

        self._window = None

    def build_app_menu(self):
        log.debug("building app menu")
        builder = Gtk.Builder()

        builder.add_from_resource('/org/gnome/Music/app-menu.ui')

        menu = builder.get_object('app-menu')
        self.set_app_menu(menu)

        aboutAction = Gio.SimpleAction.new('about', None)
        aboutAction.connect('activate', self.about)
        self.add_action(aboutAction)

        helpAction = Gio.SimpleAction.new('help', None)
        helpAction.connect('activate', self.help)
        self.add_action(helpAction)

        newPlaylistAction = Gio.SimpleAction.new('newPlaylist', None)
        newPlaylistAction.connect('activate', self.new_playlist)
        self.add_action(newPlaylistAction)

        quitAction = Gio.SimpleAction.new('quit', None)
        quitAction.connect('activate', self.quit)
        self.add_action(quitAction)

    def new_playlist(self, action, param):
        log.debug("TODO: New playlist action")
        pass

    def help(self, action, param):
        log.debug("Open Help action")
        Gtk.show_uri(None, "help:gnome-music", Gdk.CURRENT_TIME)

    def about(self, action, param):
        log.debug("About action")
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Music/AboutDialog.ui')
        about = builder.get_object('about_dialog')
        about.set_transient_for(self._window)
        about.connect("response", self.about_response)
        about.show()

    def about_response(self, dialog, response):
        log.debug("Close about")
        dialog.destroy()

    def do_startup(self):
        log.debug("app is starting up")
        Gtk.Application.do_startup(self)

        Notify.init(_("Music"))

        self.build_app_menu()

    def quit(self, action=None, param=None):
        logging.debug("Help action")
        self._window.destroy()

    def do_activate(self):
        log.debug("App is activated")
        if not self._window:
            self._window = Window(self)
            self.service = MediaPlayer2Service(self)
            self._notifications = NotificationManager(self._window.player)

        self._window.present()
