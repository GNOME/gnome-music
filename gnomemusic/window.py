# Copyright 2025 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from gi.repository import Adw, GLib, GObject, Gdk, Gio, Gtk
from gettext import gettext as _

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
    _shortcut_controller = Gtk.Template.Child()
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
        self._search_view: SearchView | None = None
        self._status_navpage = StatusNavigationPage(app)
        self._playlist_dialog: PlaylistDialog | None = None

        self._player = app.props.player
        self._search = app.props.search

        self._startup_timeout_id = 0
        self._setup_view()
        self._set_actions()

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
        shift_mask = Gdk.ModifierType.SHIFT_MASK

        search_active = self._search.props.search_mode_active
        rename_active = getattr(
            self.views[View.PLAYLIST], "rename_active", False)
        unicode_char = chr(Gdk.keyval_to_unicode(keyval))

        # Open the search bar when typing printable chars.
        if ((not search_active
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

    def _set_actions(self) -> None:
        action_entries = [
            ("navigate_back", self._navigate_back, ["<Alt>Left"]),
            ("search_bar_close", self._search_bar_close, ["Escape"]),
            ("search_bar_open", self._search_bar_open, ["<Ctrl>F"]),
            ("view_albums", self._view_albums, ["<Alt>1", "<Alt>KP_1"]),
            ("view_artists", self._view_artists, ["<Alt>2", "<Alt>KP_2"]),
            ("view_playlists", self._view_playlists, ["<Alt>3", "<Alt>KP_3"])
        ]

        for action, callback, accel in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect("activate", callback)
            self.add_action(simple_action)
            if accel:
                shortcut = Gtk.Shortcut.new(
                    Gtk.ShortcutTrigger.parse_string("|".join(accel)),
                    Gtk.ShortcutAction.parse_string(f"action(win.{action})"))
                self._shortcut_controller.add_shortcut(shortcut)

    def _navigate_back(
            self, action: Gio.SimpleAction,
            param: GLib.Variant | None) -> None:
        if not self._is_main_view_active():
            self._navigation_view.pop()

    def _search_bar_close(
            self, action: Gio.SimpleAction,
            param: GLib.Variant | None) -> None:
        if self._search.props.search_mode_active:
            self._search.props.search_mode_active = False

    def _search_bar_open(
            self, action: Gio.SimpleAction,
            param: GLib.Variant | None) -> None:
        rename_active = getattr(
            self.views[View.PLAYLIST], "rename_active", False)

        if not (rename_active
                or self._search.props.search_mode_active):
            self._search.props.search_mode_active = True

    def _view_albums(
            self, action: Gio.SimpleAction,
            param: GLib.Variant | None) -> None:
        self._switch_to_view("albums")

    def _view_artists(
            self, action: Gio.SimpleAction,
            param: GLib.Variant | None) -> None:
        self._switch_to_view("artists")

    def _view_playlists(
            self, action: Gio.SimpleAction,
            param: GLib.Variant | None) -> None:
        self._switch_to_view("playlists")

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
