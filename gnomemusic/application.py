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

import asyncio
from typing import Optional
from gettext import gettext as _

from gi.events import GLibEventLoopPolicy
from gi.repository import Adw, Gtk, Gio, GLib, Gdk, GObject

from gnomemusic.about import show_about
from gnomemusic.coregrilo import CoreGrilo
from gnomemusic.coremodel import CoreModel
from gnomemusic.inhibitsuspend import InhibitSuspend
from gnomemusic.mpris import MPRIS
from gnomemusic.musiclogger import MusicLogger
from gnomemusic.notificationmanager import NotificationManager
from gnomemusic.pauseonsuspend import PauseOnSuspend
from gnomemusic.player import Player
from gnomemusic.search import Search
from gnomemusic.widgets.preferencesdialog import PreferencesDialog
from gnomemusic.window import Window


class Application(Adw.Application):

    def __init__(self, application_id, version):
        super().__init__(
            application_id=application_id,
            flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.props.resource_base_path = "/org/gnome/Music"
        GLib.set_application_name(_("Music"))
        GLib.set_prgname(application_id)
        GLib.setenv("PULSE_PROP_media.role", "music", True)

        asyncio.set_event_loop_policy(GLibEventLoopPolicy())

        self._version = version
        self._window = None

        self._log = MusicLogger()
        self._search = Search()

        self._notificationmanager = NotificationManager(self)
        self._coremodel = CoreModel(self)
        # Order is important: CoreGrilo initializes the Grilo sources,
        # which in turn uses CoreModel extensively.
        self._coregrilo = CoreGrilo(self)

        self._settings = Gio.Settings.new('org.gnome.Music')
        self._player = Player(self)

        InhibitSuspend(self)

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

    @GObject.Property(
        type=NotificationManager, flags=GObject.ParamFlags.READABLE)
    def notificationmanager(self):
        """Get notification manager

        :returns: notification manager
        :rtype: NotificationManager
        """
        return self._notificationmanager

    def _set_actions(self):
        action_entries = [
            ("about", self._about, None),
            ("preferences", self._preferences_dialog,
                ("app.preferences", ["<Ctrl>comma"])),
            ("help", self._help, ("app.help", ["F1"])),
            ("quit", self._quit, ("app.quit", ["<Ctrl>Q"]))
        ]

        for action, callback, accel in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect('activate', callback)
            self.add_action(simple_action)
            if accel is not None:
                self.set_accels_for_action(*accel)

    def _help(self, action: Gio.Action, param: Optional[GLib.Variant]) -> None:

        def show_uri_cb(parent: Gtk.Window, result: Gio.AsyncResult) -> None:
            try:
                Gtk.show_uri_full_finish(parent, result)
            except GLib.Error:
                self._log.message("Help handler not available.")

        Gtk.show_uri_full(
            self._window, "help:gnome-music", Gdk.CURRENT_TIME, None,
            show_uri_cb)

    def _preferences_dialog(
            self, action: Gio.SimpleAction,
            param_type: GLib.VariantType) -> None:
        if self._window.props.visible_dialog:
            return

        pref_dialog = PreferencesDialog(self)
        pref_dialog.present(self._window)

    def _about(self, action, param):
        show_about(self.props.application_id, self._version, self._window)

    def do_startup(self):
        Adw.Application.do_startup(self)
        Adw.StyleManager.get_default().set_color_scheme(
            Adw.ColorScheme.PREFER_LIGHT)
        self._set_actions()

    def _quit(self, action=None, param=None):
        self._window.destroy()

    def do_activate(self):
        if not self._window:
            self._window = Window(self)
            self.notify("window")
            self._window.set_default_icon_name(self.props.application_id)
            if self.props.application_id == "org.gnome.Music.Devel":
                self._window.get_style_context().add_class('devel')
            MPRIS(self)

        PauseOnSuspend(self._player)

        self._window.present()
