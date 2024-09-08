# Copyright 2019 The GNOME Music developers
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

from typing import Optional

from gi.repository import Adw, Gtk, Gdk, GLib, GObject
from gettext import gettext as _

from gnomemusic.player import RepeatMode
from gnomemusic.trackerwrapper import TrackerState
from gnomemusic.utils import View
from gnomemusic.views.albumsview import AlbumsView
from gnomemusic.views.artistsview import ArtistsView
from gnomemusic.views.searchview import SearchView
from gnomemusic.views.playlistsview import PlaylistsView
from gnomemusic.widgets.statusnavigationpage import StatusNavigationPage
from gnomemusic.widgets.headerbar import HeaderBar
from gnomemusic.widgets.playertoolbar import PlayerToolbar  # noqa: F401
from gnomemusic.widgets.playlistdialog import PlaylistDialog
from gnomemusic.windowplacement import WindowPlacement


@Gtk.Template(resource_path="/org/gnome/Music/ui/Window.ui")
class Window(Adw.ApplicationWindow):

    __gtype_name__ = "Window"

    active_view = GObject.Property(type=GObject.GObject, default=None)

    _loading_progress = Gtk.Template.Child()
    _main_navigation_page = Gtk.Template.Child()
    _main_toolbar_view = Gtk.Template.Child()
    _navigation_view = Gtk.Template.Child()
    _overlay = Gtk.Template.Child()
    _player_toolbar = Gtk.Template.Child()
    _stack = Gtk.Template.Child()
    _toast_overlay = Gtk.Template.Child()

    def __init__(self, app):
        """Initialize the main window.

        :param Gtk.Application app: Application object
        """
        super().__init__(application=app, title=_("Music"))

        self._app = app

        self.set_size_request(360, 294)
        WindowPlacement(self)

        self._headerbar = HeaderBar(self._app)
        self._search_view: Optional[SearchView] = None
        self._status_navpage = StatusNavigationPage(app)
        self._playlist_dialog: Optional[PlaylistDialog] = None

        self._player = app.props.player
        self._search = app.props.search

        self._startup_timeout_id = 0
        self._setup_view()

    def _setup_view(self):
        self._headerbar.props.stack = self._stack
        self._main_toolbar_view.add_top_bar(self._headerbar)

        self._search.bind_property(
            "search-mode-active", self._headerbar, "search-mode-active",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        self._search.connect(
            "notify::search-mode-active", self._on_search_mode_changed)

        self._player_toolbar.props.player = self._player

        self.views = [None] * len(View)

        self._navigation_view.add(self._status_navpage)

        self._stack.connect(
            "notify::visible-child", self._on_stack_visible_child_changed)

        self._headerbar.props.state = HeaderBar.State.MAIN

        self._app.props.coremodel.connect(
            "notify::songs-available", self._on_songs_available)

        self._app.props.coregrilo.connect(
            "notify::tracker-available", self._on_tracker_available)

        def notify() -> bool:
            self._startup_timeout_id = 0
            self._app.props.coremodel.notify("songs-available")

            return GLib.SOURCE_REMOVE

        self._startup_timeout_id = GLib.timeout_add(1000, notify)

    def _switch_to_empty_view(self) -> None:
        tracker_state = self._app.props.coregrilo.props.tracker_available
        statusnp = self._status_navpage
        if tracker_state == TrackerState.UNAVAILABLE:
            statusnp.props.state = StatusNavigationPage.State.NO_TRACKER
        elif tracker_state == TrackerState.OUTDATED:
            statusnp.props.state = StatusNavigationPage.State.TRACKER_OUTDATED
        else:
            statusnp.props.state = StatusNavigationPage.State.EMPTY

    def _on_search_mode_changed(self, search, value):
        if self._search.props.search_mode_active:
            self._navigation_view.replace_with_tags(["searchview"])
        else:
            self._navigation_view.replace_with_tags(["mainview"])

    def _on_songs_available(self, klass, value):
        if self._startup_timeout_id > 0:
            GLib.source_remove(self._startup_timeout_id)
            self._startup_timeout_id = 0

        if self._app.props.coremodel.props.songs_available:
            self._navigation_view.replace_with_tags(["mainview"])
            self._switch_to_player_view()
        else:
            self._navigation_view.replace_with_tags(["status"])
            self._switch_to_empty_view()

    def _on_stack_visible_child_changed(self, klass, value):
        self.props.active_view = self._stack.props.visible_child

    def _on_tracker_available(self, klass, value):
        new_state = self._app.props.coregrilo.props.tracker_available

        if new_state != TrackerState.AVAILABLE:
            self._switch_to_empty_view()

        self._app.props.coremodel.notify("songs-available")

    def _switch_to_player_view(self):
        # All views are created together, so if the album view is
        # already initialized, assume the rest are as well.
        if self.views[View.ALBUM] is not None:
            return

        self._headerbar.props.state = HeaderBar.State.MAIN
        self.views[View.ALBUM] = AlbumsView(self._app)
        self.views[View.ARTIST] = ArtistsView(self._app)
        self.views[View.PLAYLIST] = PlaylistsView(self._app)

        self._search_view = SearchView(self._app)
        self._search.bind_property(
            "state", self._search_view, "search-state",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self._navigation_view.add(self._search_view)
        self._search.bind_property(
            "search-mode-active", self._search_view, "search-mode-active",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        for i in self.views[View.ALBUM:]:
            if i.props.title:
                stackpage = self._stack.add_titled(
                    i, i.props.name, i.props.title)
                stackpage.props.icon_name = i.props.icon_name
            else:
                self._stack.add_named(i, i.props.name)

    @GObject.Property(
        type=HeaderBar, default=None, flags=GObject.ParamFlags.READABLE)
    def headerbar(self) -> HeaderBar:
        """Get headerbar instance.

        :returns: The headerbar
        :rtype: HeaderBar
        """
        return self._headerbar

    @GObject.Property(
        type=Adw.NavigationView, default=None,
        flags=GObject.ParamFlags.READABLE)
    def navigation_view(self) -> Adw.NavigationView:
        """Get NavigationView instance.

        :returns: The navigation view
        :rtype: Adw.NavigationView
        """
        return self._navigation_view

    @Gtk.Template.Callback()
    def _on_key_press(
            self, controller: Gtk.EventControllerKey, keyval: int,
            keycode: int, state: Gdk.ModifierType) -> bool:
        modifiers = state & Gtk.accelerator_get_default_mod_mask()
        control_mask = Gdk.ModifierType.CONTROL_MASK
        shift_mask = Gdk.ModifierType.SHIFT_MASK
        alt_mask = Gdk.ModifierType.ALT_MASK

        search_active = self._search.props.search_mode_active
        rename_active = (self.views[View.PLAYLIST] is not None
                         and self.views[View.PLAYLIST].rename_active)
        unicode_char = chr(Gdk.keyval_to_unicode(keyval))
        active_view_stack_name = self._stack.props.visible_child_name

        # Ctrl + F: Open search bar
        if (modifiers == control_mask
                and keyval == Gdk.KEY_f
                and not rename_active
                and not search_active):
            self._search.props.search_mode_active = True
        # Ctrl + Space: Play / Pause
        elif (modifiers == control_mask
                and keyval == Gdk.KEY_space):
            self._player.play_pause()
        # Ctrl + B: Previous
        elif (modifiers == control_mask
                and keyval == Gdk.KEY_b):
            self._player.previous()
        # Ctrl + N: Next
        elif (modifiers == control_mask
                and keyval == Gdk.KEY_n):
            self._player.next()
        # Ctrl + R: Toggle repeat
        elif (modifiers == control_mask
                and keyval == Gdk.KEY_r):
            if self._player.props.repeat_mode == RepeatMode.SONG:
                self._player.props.repeat_mode = RepeatMode.NONE
            else:
                self._player.props.repeat_mode = RepeatMode.SONG
        # Ctrl + S: Toggle shuffle
        elif (modifiers == control_mask
                and keyval == Gdk.KEY_s):
            if self._player.props.repeat_mode == RepeatMode.SHUFFLE:
                self._player.props.repeat_mode = RepeatMode.NONE
            else:
                self._player.props.repeat_mode = RepeatMode.SHUFFLE
        # Alt + 1 : Switch to albums view
        elif (modifiers == alt_mask
                and keyval in [Gdk.KEY_1, Gdk.KEY_KP_1]):
            self._switch_to_view("albums")
        # Alt + 2 : Switch to artists view
        elif (modifiers == alt_mask
                and keyval in [Gdk.KEY_2, Gdk.KEY_KP_2]):
            self._switch_to_view("artists")
        # Alt + 3 : Switch to playlists view
        elif (modifiers == alt_mask
                and keyval in [Gdk.KEY_3, Gdk.KEY_KP_3]):
            self._switch_to_view("playlists")
        elif (keyval == Gdk.KEY_AudioPlay
                or keyval == Gdk.KEY_AudioPause):
            self._player.play_pause()
        elif keyval == Gdk.KEY_AudioStop:
            self._player.stop()
        elif keyval == Gdk.KEY_AudioPrev:
            self._player.previous()
        elif keyval == Gdk.KEY_AudioNext:
            self._player.next()
        elif (keyval == Gdk.KEY_Delete
                and self._is_main_view_active()
                and active_view_stack_name == "playlists"
                and not rename_active):
            self.activate_action("playlist_delete", None)
        # Close the search bar after Esc is pressed
        elif (keyval == Gdk.KEY_Escape
                and search_active):
            self._search.props.search_mode_active = False
        # Open the search bar when typing printable chars.
        elif ((not search_active
                and self._search_view is not None
                and self._is_main_view_active()
                and not keyval == Gdk.KEY_space)
                and GLib.unichar_isprint(unicode_char)
                and (modifiers == shift_mask
                     or modifiers == 0)
                and not rename_active):
            self._search.props.search_mode_active = True
            self._search_view.props.search_text = unicode_char
        else:
            return Gdk.EVENT_PROPAGATE

        return Gdk.EVENT_STOP

    def _switch_to_view(self, view_name: str) -> None:
        """Switch the view switcher to another page"""
        if self._is_main_view_active():
            self._stack.props.visible_child_name = view_name

    def _is_main_view_active(self) -> bool:
        """Returns True if the main (view switcher) navigation page
        is active
        """
        visible_page = self._navigation_view.props.visible_page
        return visible_page == self._main_navigation_page

    def set_player_visible(self, visible):
        """Set PlayWidget action visibility

        :param bool visible: actionbar visibility
        """
        self._player_toolbar.props.revealed = visible

    def loading_pulse(self) -> bool:
        """Pulse the loading progress bar

        :returns: GLib.SOURCE_CONTINUE
        :rtype: bool
        """
        self._loading_progress.pulse()

        return GLib.SOURCE_CONTINUE

    def loading_visible(self, show: bool) -> None:
        """Sets visibility of the loading progressbar

        :param bool show: Wheter to show the loading bar
        """
        self._loading_progress.props.visible = show
