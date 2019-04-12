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
import logging

from gi.repository import Gtk, Gio, GLib, Gdk, GObject

from gnomemusic import log
from gnomemusic.mpris import MediaPlayer2Service
from gnomemusic.player import Player
from gnomemusic.widgets.aboutdialog import AboutDialog
from gnomemusic.window import Window


class Application(Gtk.Application):
    def __repr__(self):
        return '<Application>'

    @log
    def __init__(self, application_id):
        super().__init__(
            application_id=application_id,
            flags=Gio.ApplicationFlags.FLAGS_NONE)

        self.props.resource_base_path = "/org/gnome/Music"
        GLib.set_application_name(_("Music"))
        GLib.set_prgname(application_id)
        GLib.setenv("PULSE_PROP_media.role", "music", True)

        self._init_style()
        self._window = None

        self._settings = Gio.Settings.new('org.gnome.Music')
        self._player = Player(self)

    def _init_style(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource('/org/gnome/Music/org.gnome.Music.css')
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    @GObject.Property(
        type=Player, default=None, flags=GObject.ParamFlags.READABLE)
    def player(self):
        """Get application-wide music player.

        :returns: the player
        :rtype: Player
        """
        return self._player

    @GObject.Property(
        type=Gio.Settings, flags=GObject.ParamFlags.READABLE)
    def settings(self):
        """Get application-wide settings.

        :returns: settings
        :rtype: Gio.settings
        """
        return self._settings

    @log
    def _build_app_menu(self):
        action_entries = [
            ('about', self._about),
            ('help', self._help)
        ]

        for action, callback in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect('activate', callback)
            self.add_action(simple_action)

    @log
    def _help(self, action, param):
        try:
            Gtk.show_uri(None, "help:gnome-music", Gdk.CURRENT_TIME)
        except GLib.Error:
            logging.warning("Help handler not available.")

    @log
    def _about(self, action, param):
        about = AboutDialog()
        about.props.transient_for = self._window

    @log
    def do_startup(self):
        Gtk.Application.do_startup(self)

        self._build_app_menu()

    @log
    def quit(self, action=None, param=None):
        self._window.destroy()

    def do_activate(self):
        if not self._window:
            self._window = Window(self)
            self._window.set_default_icon_name(self.props.application_id)
            if self.props.application_id == 'org.gnome.MusicDevel':
                self._window.get_style_context().add_class('devel')
            MediaPlayer2Service(self)

        # gtk_window_present does not work on Wayland.
        # Use gtk_present_with_time as a workaround instead.
        # See https://gitlab.gnome.org/GNOME/gtk/issues/624#note_10996
        self._window.present_with_time(GLib.get_monotonic_time() / 1000)
