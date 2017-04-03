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

from gettext import gettext as _

import gi
gi.require_version('Notify', '0.7')
from gi.repository import Gtk, Gio, GLib, Gdk, Notify

from gnomemusic import log
from gnomemusic.mpris import MediaPlayer2Service
from gnomemusic.notification import NotificationManager
from gnomemusic.window import Window


class Application(Gtk.Application):
    def __repr__(self):
        return '<Application>'

    @log
    def __init__(self):
        Gtk.Application.__init__(self, application_id='org.gnome.Music',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        GLib.set_application_name(_("Music"))
        GLib.set_prgname('gnome-music')
        self._settings = Gio.Settings.new('org.gnome.Music')
        self._init_style()
        self._window = None

    def _init_style(self):
        css_provider_file = Gio.File.new_for_uri(
            'resource:///org/gnome/Music/application.css')
        css_provider = Gtk.CssProvider()
        css_provider.load_from_file(css_provider_file)
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    @log
    def _build_app_menu(self):
        action_entries = [
            ('about', self._about),
            ('help', self._help),
            ('quit', self.quit),
        ]

        for action, callback in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect('activate', callback)
            self.add_action(simple_action)

    @log
    def _help(self, action, param):
        Gtk.show_uri(None, "help:gnome-music", Gdk.CURRENT_TIME)

    @log
    def _about(self, action, param):
        def about_response(dialog, response):
            dialog.destroy()

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Music/AboutDialog.ui')
        about = builder.get_object('about_dialog')
        about.set_transient_for(self._window)
        about.connect("response", about_response)
        about.show()

    @log
    def do_startup(self):
        Gtk.Application.do_startup(self)
        Notify.init(_("Music"))
        self._build_app_menu()

    @log
    def quit(self, action=None, param=None):
        self._window.destroy()

    def do_activate(self):
        if not self._window:
            self._window = Window(self)
            MediaPlayer2Service(self)
            if self._settings.get_value('notifications'):
                self._notifications = NotificationManager(self._window.player)

        self._window.present()
