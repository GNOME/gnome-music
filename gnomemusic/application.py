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

from gi.repository import Gtk, Gio, GLib, Gdk, GObject

from gnomemusic.coregrilo import CoreGrilo
from gnomemusic.coremodel import CoreModel
from gnomemusic.coreselection import CoreSelection
from gnomemusic.inhibitsuspend import InhibitSuspend
from gnomemusic.mpris import MPRIS
from gnomemusic.musiclogger import MusicLogger
from gnomemusic.pauseonsuspend import PauseOnSuspend
from gnomemusic.player import Player
from gnomemusic.scrobbler import LastFmScrobbler
from gnomemusic.search import Search
from gnomemusic.widgets.aboutdialog import AboutDialog
from gnomemusic.widgets.lastfmdialog import LastfmDialog
from gnomemusic.window import Window


class Application(Gtk.Application):

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

        self._log = MusicLogger()
        self._search = Search()

        self._coreselection = CoreSelection()
        self._coremodel = CoreModel(self)
        # Order is important: CoreGrilo initializes the Grilo sources,
        # which in turn use CoreModel & CoreSelection extensively.
        self._coregrilo = CoreGrilo(self)

        self._settings = Gio.Settings.new('org.gnome.Music')
        self._lastfm_scrobbler = LastFmScrobbler(self)
        self._player = Player(self)

        InhibitSuspend(self)
        PauseOnSuspend(self._player)

    def _init_style(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource('/org/gnome/Music/org.gnome.Music.css')
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    @GObject.Property(
        type=CoreGrilo, default=None, flags=GObject.ParamFlags.READABLE)
    def coregrilo(self):
        """Get application-wide CoreGrilo instance.

        :returns: The grilo wrapper
        :rtype: CoreGrilo
        """
        return self._coregrilo

    @GObject.Property(
        type=MusicLogger, default=None, flags=GObject.ParamFlags.READABLE)
    def log(self):
        """Get application-wide logging facility.

        :returns: the logger
        :rtype: MusicLogger
        """
        return self._log

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

    @GObject.Property(
        type=CoreModel, flags=GObject.ParamFlags.READABLE)
    def coremodel(self):
        """Get class providing all listmodels.

        :returns: List model provider class
        :rtype: CoreModel
        """
        return self._coremodel

    @GObject.Property(
        type=CoreSelection, flags=GObject.ParamFlags.READABLE)
    def coreselection(self):
        """Get selection object.

        :returns: Object containing all selection info
        :rtype: CoreSelection
        """
        return self._coreselection

    @GObject.Property(type=LastFmScrobbler, flags=GObject.ParamFlags.READABLE)
    def lastfm_scrobbler(self):
        """Get Last.fm scrobbler.

        :returns: Last.fm scrobbler
        :rtype: LastFmScrobbler
        """
        return self._lastfm_scrobbler

    @GObject.Property(type=Window, flags=GObject.ParamFlags.READABLE)
    def window(self):
        """Get main window.

        :returns: Main window.
        :rtype: Window
        """
        return self._window

    @GObject.Property(
        type=Search, flags=GObject.ParamFlags.READABLE)
    def search(self):
        """Get class providing search logic.

        :returns: List model provider class
        :rtype: Search
        """
        return self._search

    def _set_actions(self):
        action_entries = [
            ('about', self._about, None),
            ("help", self._help, ("app.help", ["F1"])),
            ("lastfm-configure", self._lastfm_account, None),
            ("quit", self._quit, ("app.quit", ["<Ctrl>Q"]))
        ]

        for action, callback, accel in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect('activate', callback)
            self.add_action(simple_action)
            if accel is not None:
                self.set_accels_for_action(*accel)

    def _help(self, action, param):
        try:
            Gtk.show_uri(None, "help:gnome-music", Gdk.CURRENT_TIME)
        except GLib.Error:
            self._log.message("Help handler not available.")

    def _lastfm_account(self, action, param):
        lastfm_dialog = LastfmDialog(self._window, self._lastfm_scrobbler)
        lastfm_dialog.run()
        lastfm_dialog.destroy()

    def _about(self, action, param):
        about = AboutDialog()
        about.props.transient_for = self._window
        about.present()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self._set_actions()

    def _quit(self, action=None, param=None):
        self._window.destroy()

    def do_activate(self):
        if not self._window:
            self._window = Window(self)
            self._window.set_default_icon_name(self.props.application_id)
            if self.props.application_id == "org.gnome.Music.Devel":
                self._window.get_style_context().add_class('devel')
            MPRIS(self)

        self._window.present()
