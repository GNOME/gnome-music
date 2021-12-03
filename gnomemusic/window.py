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

from gi.repository import Adw, Gtk, Gdk, Gio, GLib, GObject
from gettext import gettext as _

from gnomemusic.gstplayer import Playback
from gnomemusic.player import RepeatMode
from gnomemusic.search import Search
from gnomemusic.trackerwrapper import TrackerState
from gnomemusic.utils import View
from gnomemusic.views.albumsview import AlbumsView
from gnomemusic.views.artistsview import ArtistsView
from gnomemusic.views.emptyview import EmptyView
from gnomemusic.views.filesview import FilesView
from gnomemusic.views.searchview import SearchView
from gnomemusic.views.songsview import SongsView
from gnomemusic.views.playlistsview import PlaylistsView
from gnomemusic.widgets.headerbar import HeaderBar
from gnomemusic.widgets.playertoolbar import PlayerToolbar  # noqa: F401
from gnomemusic.widgets.playlistdialog import PlaylistDialog
from gnomemusic.widgets.searchheaderbar import SearchHeaderBar
from gnomemusic.widgets.selectiontoolbar import SelectionToolbar  # noqa: F401
from gnomemusic.windowplacement import WindowPlacement


@Gtk.Template(resource_path="/org/gnome/Music/ui/Window.ui")
class Window(Adw.ApplicationWindow):

    __gtype_name__ = "Window"

    active_view = GObject.Property(type=GObject.GObject, default=None)
    selected_songs_count = GObject.Property(type=int, default=0, minimum=0)
    selection_mode = GObject.Property(type=bool, default=False)

    _headerbar_stack = Gtk.Template.Child()
    _loading_progress = Gtk.Template.Child()
    _overlay = Gtk.Template.Child()
    _player_toolbar = Gtk.Template.Child()
    _selection_toolbar = Gtk.Template.Child()
    _stack = Gtk.Template.Child()
    _toast_overlay = Gtk.Template.Child()

    def __init__(self, app):
        """Initialize the main window.

        :param Gtk.Application app: Application object
        """
        super().__init__(application=app, title=_("Music"))

        self._app = app
        self._coreselection = app.props.coreselection

        self._coreselection.bind_property(
            "selected-songs-count", self, "selected-songs-count")

        self._settings = app.props.settings
        select_all = Gio.SimpleAction.new('select_all', None)
        select_all.connect('activate', self._select_all)
        self.add_action(select_all)
        deselect_all = Gio.SimpleAction.new('deselect_all', None)
        deselect_all.connect('activate', self._deselect_all)
        self.add_action(deselect_all)

        self.set_size_request(200, 100)
        WindowPlacement(self)

        self._current_view = None
        self._view_before_search = None

        self._playlist_dialog: Optional[PlaylistDialog] = None

        self._player = app.props.player
        self._search = app.props.search

        self._startup_timeout_id = 0
        self._setup_view()

    def _setup_view(self):
        self._headerbar = HeaderBar(self._app)
        self._headerbar.props.stack = self._stack
        self._search_headerbar = SearchHeaderBar(self._app)
        self._search_headerbar.props.stack = self._stack
        self._headerbar_stack.add_named(self._headerbar, "main")
        self._headerbar_stack.add_named(self._search_headerbar, "search")

        self._search.bind_property(
            "search-mode-active", self._headerbar, "search-mode-active",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self._search.bind_property(
            "search-mode-active", self._search_headerbar, "search-mode-active",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self._search.bind_property(
            "state", self._search_headerbar, "search-state",
            GObject.BindingFlags.SYNC_CREATE)

        self._search.connect(
            "notify::search-mode-active", self._on_search_mode_changed)

        self._player_toolbar.props.player = self._player

        self._headerbar.connect(
            'back-button-clicked', self._switch_back_from_childview)

        self.bind_property(
            'selected-songs-count', self._headerbar, 'selected-songs-count')
        self.bind_property(
            "selected-songs-count", self._selection_toolbar,
            "selected-songs-count")
        self.bind_property(
            'selection-mode', self._headerbar, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "selected-songs-count", self._search_headerbar,
            "selected-songs-count")
        self.bind_property(
            "selection-mode", self._search_headerbar, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "selection-mode", self._player_toolbar, "visible",
            GObject.BindingFlags.INVERT_BOOLEAN)
        self.bind_property(
            "selection-mode", self._selection_toolbar, "visible")
        self.connect("notify::selection-mode", self._on_selection_mode_changed)

        self.views = [None] * len(View)
        # Create only the empty view at startup
        # if no music, switch to empty view and hide stack
        # if some music is available, populate stack with mainviews,
        # show stack and set empty_view to empty_search_view
        self.views[View.EMPTY] = EmptyView()
        self._stack.connect(
            "notify::visible-child", self._on_stack_visible_child_changed)
        self._stack.add_named(self.views[View.EMPTY], "emptyview")

        # Add the 'background' styleclass so it properly hides the
        # bottom line of the searchbar
        self._stack.get_style_context().add_class('background')

        self._selection_toolbar.connect(
            'add-to-playlist', self._on_add_to_playlist)
        self._search.connect("notify::state", self._on_search_state_changed)

        self._headerbar.props.state = HeaderBar.State.MAIN

        self._app.props.coremodel.connect(
            "notify::songs-available", self._on_songs_available)

        self._app.props.coregrilo.connect(
            "notify::tracker-available", self._on_tracker_available)

        self._startup_timeout_id = GLib.timeout_add(
            2000, self._on_songs_available, None, None)

    def _switch_to_empty_view(self):
        state = self._app.props.coregrilo.props.tracker_available
        empty_view = self.views[View.EMPTY]
        empty_view.props.visible = True
        if state == TrackerState.UNAVAILABLE:
            empty_view.props.state = EmptyView.State.NO_TRACKER
        elif state == TrackerState.OUTDATED:
            empty_view.props.state = EmptyView.State.TRACKER_OUTDATED
        else:
            empty_view.props.state = EmptyView.State.EMPTY

        self._headerbar.props.state = HeaderBar.State.EMPTY

    def _on_search_mode_changed(self, search, value):
        if self._search.props.search_mode_active:
            self._headerbar_stack.props.visible_child_name = "search"
        else:
            self._headerbar_stack.props.visible_child_name = "main"

    def _on_songs_available(self, klass, value):
        if self._startup_timeout_id > 0:
            GLib.source_remove(self._startup_timeout_id)
            self._startup_timeout_id = 0

        if self._app.props.coremodel.props.songs_available:
            self._switch_to_player_view()
        else:
            self._switch_to_empty_view()

    def _on_stack_visible_child_changed(self, klass, value):
        self.props.active_view = self._stack.props.visible_child

    def _on_tracker_available(self, klass, value):
        new_state = self._app.props.coregrilo.props.tracker_available

        if new_state != TrackerState.AVAILABLE:
            self._switch_to_empty_view()

        self._on_songs_available(None, None)

    def _switch_to_player_view(self):
        self._on_notify_model_id = self._stack.connect(
            'notify::visible-child', self._on_notify_mode)
        self.connect('destroy', self._notify_mode_disconnect)

        # All views are created together, so if the album view is
        # already initialized, assume the rest are as well.
        if self.views[View.ALBUM] is not None:
            return

        ctrl = Gtk.GestureClick().new()
        # Mouse button 8 is the back button.
        ctrl.props.button = 8
        ctrl.connect("pressed", self._on_back_button_pressed)
        self.add_controller(ctrl)

        self.views[View.EMPTY].props.state = EmptyView.State.SEARCH

        self._headerbar.props.state = HeaderBar.State.MAIN
        self.views[View.ALBUM] = AlbumsView(self._app)
        self.views[View.ARTIST] = ArtistsView(self._app)
        self.views[View.SONG] = SongsView(self._app)
        self.views[View.PLAYLIST] = PlaylistsView(self._app)
        self.views[View.SEARCH] = SearchView(self._app)
        self.views[View.FILES] = FilesView(self._app)

        # empty view has already been created in self._setup_view starting at
        # View.ALBUM
        # empty view state is changed once album view is visible to prevent it
        # from being displayed during startup
        for i in self.views[View.ALBUM:]:
            if i.props.title:
                stackpage = self._stack.add_titled(
                    i, i.props.name, i.props.title)
                stackpage.props.icon_name = i.props.icon_name
            else:
                self._stack.add_named(i, i.props.name)

        # The "visible-child" notification ensures that the AlbumView
        # appears as selected by the stack switcher on launch.
        self._stack.props.visible_child = self.views[View.ALBUM]
        self._stack.notify("visible-child")

        self.views[View.SEARCH].bind_property(
            "search-state", self._search, "state",
            GObject.BindingFlags.SYNC_CREATE)
        self._search.bind_property(
            "search-mode-active", self.views[View.SEARCH],
            "search-mode-active", GObject.BindingFlags.BIDIRECTIONAL)
        self._search.bind_property(
            "search-mode-active", self.views[View.ALBUM],
            "search-mode-active", GObject.BindingFlags.SYNC_CREATE)

    def _select_all(self, action=None, param=None):
        if not self.props.selection_mode:
            return

        self.props.active_view.select_all()

    def _deselect_all(self, action=None, param=None):
        if not self.props.selection_mode:
            return

        self.props.active_view.deselect_all()

    @Gtk.Template.Callback()
    def _on_key_press(self, controller, keyval, keycode, state):
        modifiers = state & Gtk.accelerator_get_default_mod_mask()
        control_mask = Gdk.ModifierType.CONTROL_MASK
        shift_mask = Gdk.ModifierType.SHIFT_MASK
        alt_mask = Gdk.ModifierType.ALT_MASK
        shift_ctrl_mask = control_mask | shift_mask

        # Ctrl+<KEY>
        if control_mask == modifiers:
            if keyval == Gdk.KEY_a:
                self._select_all()
            # Open search bar on Ctrl + F
            if (keyval == Gdk.KEY_f
                    and not self.views[View.PLAYLIST].rename_active
                    and not self.props.selection_mode
                    and self._headerbar.props.state != HeaderBar.State.SEARCH):
                search_mode = self._search.props.search_mode_active
                self._search.props.search_mode_active = not search_mode
            # Play / Pause on Ctrl + SPACE
            if keyval == Gdk.KEY_space:
                self._player.play_pause()
            # Play previous on Ctrl + B
            if keyval == Gdk.KEY_b:
                self._player.previous()
            # Play next on Ctrl + N
            if keyval == Gdk.KEY_n:
                self._player.next()
            # Toggle repeat on Ctrl + R
            if keyval == Gdk.KEY_r:
                if self._player.props.repeat_mode == RepeatMode.SONG:
                    self._player.props.repeat_mode = RepeatMode.NONE
                else:
                    self._player.props.repeat_mode = RepeatMode.SONG
            # Toggle shuffle on Ctrl + S
            if keyval == Gdk.KEY_s:
                if self._player.props.repeat_mode == RepeatMode.SHUFFLE:
                    self._player.props.repeat_mode = RepeatMode.NONE
                else:
                    self._player.props.repeat_mode = RepeatMode.SHUFFLE
        # Ctrl+Shift+<KEY>
        elif modifiers == shift_ctrl_mask:
            if keyval == Gdk.KEY_A:
                self._deselect_all()
        # Alt+<KEY>
        elif modifiers == alt_mask:
            # Go back from child view on Alt + Left
            if keyval == Gdk.KEY_Left:
                self._switch_back_from_childview()
            # Headerbar switching
            if keyval in [Gdk.KEY_1, Gdk.KEY_KP_1]:
                self._toggle_view(View.ALBUM)
            if keyval in [Gdk.KEY_2, Gdk.KEY_KP_2]:
                self._toggle_view(View.ARTIST)
            if keyval in [Gdk.KEY_3, Gdk.KEY_KP_3]:
                self._toggle_view(View.SONG)
            if keyval in [Gdk.KEY_4, Gdk.KEY_KP_4]:
                self._toggle_view(View.PLAYLIST)
        # No modifier
        else:
            if (keyval == Gdk.KEY_AudioPlay
                    or keyval == Gdk.KEY_AudioPause):
                self._player.play_pause()

            if keyval == Gdk.KEY_AudioStop:
                self._player.stop()

            if keyval == Gdk.KEY_AudioPrev:
                self._player.previous()

            if keyval == Gdk.KEY_AudioNext:
                self._player.next()

            if (keyval == Gdk.KEY_Delete
                    and self.props.active_view == self.views[View.PLAYLIST]
                    and not self.views[View.PLAYLIST].rename_active):
                self.activate_action("playlist_delete", None)

            # Close selection mode or search bar after Esc is pressed
            if keyval == Gdk.KEY_Escape:
                if self.props.selection_mode:
                    self.props.selection_mode = False
                elif self._search.props.search_mode_active:
                    self._search.props.search_mode_active = False

        # Open the search bar when typing printable chars.
        key_unic = Gdk.keyval_to_unicode(keyval)
        if ((not self._search.props.search_mode_active
                and not keyval == Gdk.KEY_space)
                and GLib.unichar_isprint(chr(key_unic))
                and (modifiers == shift_mask
                     or modifiers == 0)
                and self.views[View.PLAYLIST] is not None
                and not self.views[View.PLAYLIST].rename_active
                and not self.props.selection_mode
                and self._headerbar.props.state != HeaderBar.State.SEARCH):
            self._search.props.search_mode_active = True

    def _on_back_button_pressed(self, gesture, n_press, x, y):
        self._headerbar.emit('back-button-clicked')

    def _notify_mode_disconnect(self, data=None):
        self._player.stop()
        self.notifications_popup.terminate_pending()
        self._stack.disconnect(self._on_notify_model_id)

    def _on_notify_mode(self, stack, param):
        previous_view = self._current_view
        self._current_view = self.props.active_view

        # Disable search mode when switching view
        search_views = [self.views[View.EMPTY], self.views[View.SEARCH]]
        if (self._current_view in search_views
                and previous_view not in search_views):
            self._view_before_search = previous_view
        elif (self._current_view not in search_views
                and self._search.props.search_mode_active is True):
            self._search.props.search_mode_active = False

        # Disable the selection button for the EmptySearch and Playlist
        # view
        no_selection_mode = [
            self.views[View.EMPTY],
            self.views[View.PLAYLIST]
        ]
        allowed = self._current_view not in no_selection_mode
        self._headerbar.props.selection_mode_allowed = allowed
        self._search_headerbar.props.selection_mode_allowed = allowed

    def _toggle_view(self, view_enum):
        # TODO: The SEARCH state actually refers to the child state of
        # the search mode. This fixes the behaviour as needed, but is
        # incorrect: searchview currently does not switch states
        # correctly.
        if (not self.props.selection_mode
                and not self._headerbar.props.state == HeaderBar.State.CHILD
                and not self._headerbar.props.state == HeaderBar.State.SEARCH):
            self._stack.set_visible_child(self.views[view_enum])

    def _on_search_state_changed(self, klass, param):
        if (self._search.props.state != Search.State.NONE
                or not self._view_before_search):
            return

        # Get back to the view before the search
        self._stack.props.visible_child = self._view_before_search

    def _switch_back_from_childview(self, klass=None):
        if self.props.selection_mode:
            return

        views_with_child = [
            self.views[View.ALBUM],
            self.views[View.SEARCH]
        ]
        if self._current_view in views_with_child:
            self._current_view._back_button_clicked(self._current_view)

    def _on_selection_mode_changed(self, widget, data=None):
        if (not self.props.selection_mode
                and self._player.state == Playback.STOPPED):
            self._player_toolbar.props.revealed = False

    def _on_add_to_playlist(self, widget: SelectionToolbar) -> None:

        def on_response(dialog: PlaylistDialog, response_id: int) -> None:
            if not self._playlist_dialog:
                return

            if response_id == Gtk.ResponseType.ACCEPT:
                playlist = self._playlist_dialog.props.selected_playlist
                playlist.add_songs(selected_songs)

            self.props.selection_mode = False
            self._playlist_dialog.destroy()
            self._playlist_dialog = None

        if self.props.active_view == self.views[View.PLAYLIST]:
            return

        selected_songs = self._coreselection.props.selected_songs

        if len(selected_songs) < 1:
            return

        self._playlist_dialog = PlaylistDialog(self._app)
        self._playlist_dialog.props.transient_for = self
        self._playlist_dialog.connect("response", on_response)
        self._playlist_dialog.present()

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
