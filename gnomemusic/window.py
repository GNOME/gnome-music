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

from gi.repository import Gtk, Gdk, Gio, GLib, GObject
from gettext import gettext as _

from gnomemusic import log
from gnomemusic.gstplayer import Playback
from gnomemusic.mediakeys import MediaKeys
from gnomemusic.player import RepeatMode
from gnomemusic.search import Search
from gnomemusic.trackerwrapper import TrackerState
from gnomemusic.utils import View, AdaptiveViewMode
from gnomemusic.views.albumsview import AlbumsView
from gnomemusic.views.artistsview import ArtistsView
from gnomemusic.views.emptyview import EmptyView
from gnomemusic.views.searchview import SearchView
from gnomemusic.views.songsview import SongsView
from gnomemusic.views.playlistsview import PlaylistsView
from gnomemusic.widgets.headerbar import HeaderBar
from gnomemusic.widgets.notificationspopup import NotificationsPopup  # noqa
from gnomemusic.widgets.playertoolbar import PlayerToolbar
from gnomemusic.widgets.playlistdialog import PlaylistDialog
from gnomemusic.widgets.searchheaderbar import SearchHeaderBar
from gnomemusic.widgets.selectiontoolbar import SelectionToolbar  # noqa: F401
from gnomemusic.windowplacement import WindowPlacement

import logging
logger = logging.getLogger(__name__)


@Gtk.Template(resource_path="/org/gnome/Music/ui/Window.ui")
class Window(Gtk.ApplicationWindow):

    __gtype_name__ = "Window"

    adaptive_view = GObject.Property(type=GObject.TYPE_INT, default=AdaptiveViewMode.MOBILE)
    selected_items_count = GObject.Property(type=int, default=0, minimum=0)
    selection_mode = GObject.Property(type=bool, default=False)

    notifications_popup = Gtk.Template.Child()
    _box = Gtk.Template.Child()
    _overlay = Gtk.Template.Child()
    _selection_toolbar = Gtk.Template.Child()
    _stack = Gtk.Template.Child()

    _switcher_bar = Gtk.Template.Child()

    def __repr__(self):
        return '<Window>'

    @log
    def __init__(self, app):
        """Initialize the main window.

        :param Gtk.Application app: Application object
        """
        super().__init__(application=app, title=_("Music"))

        # Hack
        self._app = app

        self._app._coreselection.bind_property(
            "selected-items-count", self, "selected-items-count")

        self._settings = app.props.settings
        self.add_action(self._settings.create_action('repeat'))
        select_all = Gio.SimpleAction.new('select_all', None)
        select_all.connect('activate', self._select_all)
        self.add_action(select_all)
        select_none = Gio.SimpleAction.new('select_none', None)
        select_none.connect('activate', self._select_none)
        self.add_action(select_none)

        self.set_size_request(200, 100)
        WindowPlacement(self)

        self.prev_view = None
        self.curr_view = None
        self._view_before_search = None

        self._player = app.props.player

        self._setup_view()

        MediaKeys(self._player, self)

    @log
    def _setup_view(self):
        self._search = Search()
        self._headerbar_stack = Gtk.Stack()
        transition_type = Gtk.StackTransitionType.CROSSFADE
        self._headerbar_stack.props.transition_type = transition_type
        self._headerbar = HeaderBar()
        self._search_headerbar = SearchHeaderBar(self._app)
        self._search_headerbar.props.stack = self._stack
        self._headerbar_stack.add_named(self._headerbar, "main")
        self._headerbar_stack.add_named(self._search_headerbar, "search")
        self._headerbar_stack.props.name = "search"

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

        self._player_toolbar = PlayerToolbar()
        self._player_toolbar.bind_property("adaptive-view", self, "adaptive-view",
                                            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        self._player_toolbar.props.player = self._player

        self._headerbar.connect(
            'back-button-clicked', self._switch_back_from_childview)

        self.bind_property(
            'selected-items-count', self._headerbar, 'selected-items-count')
        self.bind_property(
            "selected-items-count", self._selection_toolbar,
            "selected-items-count")
        self.bind_property(
            'selection-mode', self._headerbar, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "selected-items-count", self._search_headerbar,
            "selected-items-count")
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

        self.views = [Gtk.Box()] * len(View)
        # Create only the empty view at startup
        # if no music, switch to empty view and hide stack
        # if some music is available, populate stack with mainviews,
        # show stack and set empty_view to empty_search_view
        self.views[View.EMPTY] = EmptyView()
        self._stack.add_named(self.views[View.EMPTY], "emptyview")

        # Add the 'background' styleclass so it properly hides the
        # bottom line of the searchbar
        self._stack.get_style_context().add_class('background')

        self._box.pack_start(self._player_toolbar, False, False, 0)
        self._box.reorder_child(self._player_toolbar, 1)

        self.set_titlebar(self._headerbar_stack)

        self._selection_toolbar.connect(
            'add-to-playlist', self._on_add_to_playlist)
        self._search.connect("notify::state", self._on_search_state_changed)

        self._headerbar.props.state = HeaderBar.State.MAIN
        self._headerbar_stack.show_all()

        self._app.props.coremodel.connect(
            "notify::songs-available", self._on_songs_available)

        self._app.props.coremodel.props.grilo.connect(
            "notify::tracker-available", self._on_tracker_available)

        if self._app.props.coremodel.props.songs_available:
            self._switch_to_player_view()
        else:
            self._switch_to_empty_view()

    @log
    def _switch_to_empty_view(self):
        did_initial_state = self._settings.get_boolean('did-initial-state')

        state = self._app.props.coremodel.props.grilo.props.tracker_available
        empty_view = self.views[View.EMPTY]
        if state == TrackerState.UNAVAILABLE:
            empty_view.props.state = EmptyView.State.NO_TRACKER
        elif state == TrackerState.OUTDATED:
            empty_view.props.state = EmptyView.State.TRACKER_OUTDATED
        elif did_initial_state:
            empty_view.props.state = EmptyView.State.EMPTY
        else:
            # FIXME: On switch back this view does not show properly.
            empty_view.props.state = EmptyView.State.INITIAL

        self._headerbar.props.state = HeaderBar.State.EMPTY

    def _on_search_mode_changed(self, search, value):
        if self._search.props.search_mode_active:
            self._headerbar_stack.set_visible_child_name("search")
        else:
            self._headerbar_stack.set_visible_child_name("main")

    def _on_songs_available(self, klass, value):
        if self._app.props.coremodel.props.songs_available:
            self._switch_to_player_view()
        else:
            self._switch_to_empty_view()

    def _on_tracker_available(self, klass, value):
        grilo = self._app.props.coremodel.props.grilo
        new_state = grilo.props.tracker_available

        if new_state != TrackerState.AVAILABLE:
            self._switch_to_empty_view()

        self._on_songs_available(None, None)

    @log
    def _switch_to_player_view(self):
        self._settings.set_boolean('did-initial-state', True)
        self._on_notify_model_id = self._stack.connect(
            'notify::visible-child', self._on_notify_mode)
        self.connect('destroy', self._notify_mode_disconnect)
        self._key_press_event_id = self.connect(
            'key_press_event', self._on_key_press)

        self._btn_ctrl = Gtk.GestureMultiPress().new(self)
        self._btn_ctrl.props.propagation_phase = Gtk.PropagationPhase.CAPTURE
        # Mouse button 8 is the back button.
        self._btn_ctrl.props.button = 8
        self._btn_ctrl.connect("pressed", self._on_back_button_pressed)

        self.views[View.EMPTY].props.state = EmptyView.State.SEARCH

        # FIXME: In case Grilo is already initialized before the views
        # get created, they never receive a 'ready' signal to trigger
        # population. To fix this another check was added to baseview
        # to populate if grilo is ready at the end of init. For this to
        # work however, the headerbar stack needs to be created and
        # populated. This is done below, by binding headerbar.stack to
        # to window._stack. For this to succeed, the stack needs to be
        # filled with something: Gtk.Box.
        # This is a bit of circular logic that needs to be fixed.
        self._headerbar.props.state = HeaderBar.State.MAIN
        self._headerbar.props.stack = self._stack

        self.views[View.ALBUM] = AlbumsView(self._app, self._player)
        self.views[View.ARTIST] = ArtistsView(self._app, self._player)
        self.views[View.SONG] = SongsView(self._app, self._player)
        self.views[View.PLAYLIST] = PlaylistsView(self._app, self._player)
        self.views[View.SEARCH] = SearchView(self._app, self._player)

        selectable_views = [View.ALBUM, View.ARTIST, View.SONG, View.SEARCH]
        for view in selectable_views:
            self.views[view].bind_property(
                'selected-items-count', self, 'selected-items-count')

        # empty view has already been created in self._setup_view starting at
        # View.ALBUM
        # empty view state is changed once album view is visible to prevent it
        # from being displayed during startup
        for i in self.views[View.ALBUM:]:
            if i.title:
                self._stack.add_titled(i, i.name, i.title)
                self._stack.child_set_property(i, "icon-name", i.icon)
                i.bind_property("adaptive-view", self, "adaptive-view",
                                    GObject.BindingFlags.BIDIRECTIONAL
                                    | GObject.BindingFlags.SYNC_CREATE)
            else:
                self._stack.add_named(i, i.name)

        self._stack.set_visible_child(self.views[View.ALBUM])

        self.views[View.SEARCH].bind_property(
            "search-state", self._search, "state",
            GObject.BindingFlags.SYNC_CREATE)
        self._search.bind_property(
            "search-mode-active", self.views[View.SEARCH],
            "search-mode-active", GObject.BindingFlags.BIDIRECTIONAL)
        self._search.bind_property(
            "search-mode-active", self.views[View.ALBUM],
            "search-mode-active", GObject.BindingFlags.SYNC_CREATE)

        # Adaptive View
        self._switcher_bar.set_stack(self._stack)
        self.connect("size-allocate", self._on_size_allocate)

    @log
    def _select_all(self, action=None, param=None):
        if not self.props.selection_mode:
            return
        if self._headerbar.props.state == HeaderBar.State.MAIN:
            view = self._stack.get_visible_child()
        else:
            view = self._stack.get_visible_child().get_visible_child()

        view.select_all()

    @log
    def _select_none(self, action=None, param=None):
        if not self.props.selection_mode:
            return
        if self._headerbar.props.state == HeaderBar.State.MAIN:
            view = self._stack.get_visible_child()
            view.unselect_all()
        else:
            view = self._stack.get_visible_child().get_visible_child()
            view.select_none()

    @log
    def _on_key_press(self, widget, event):
        modifiers = event.get_state() & Gtk.accelerator_get_default_mod_mask()
        (_, keyval) = event.get_keyval()

        control_mask = Gdk.ModifierType.CONTROL_MASK
        shift_mask = Gdk.ModifierType.SHIFT_MASK
        mod1_mask = Gdk.ModifierType.MOD1_MASK
        shift_ctrl_mask = control_mask | shift_mask

        # Ctrl+<KEY>
        if control_mask == modifiers:
            if keyval == Gdk.KEY_a:
                self._select_all()
            # Open search bar on Ctrl + F
            if (keyval == Gdk.KEY_f
                    and not self.views[View.PLAYLIST].rename_active
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
            if keyval == Gdk.KEY_q:
                self.props.application.quit()
            # Toggle repeat on Ctrl + R
            if keyval == Gdk.KEY_r:
                if self._player.props.repeat_mode == RepeatMode.SONG:
                    self._player.props.repeat_mode = RepeatMode.NONE
                    repeat_state = GLib.Variant("s", ("none"))
                else:
                    self._player.props.repeat_mode = RepeatMode.SONG
                    repeat_state = GLib.Variant("s", ("song"))
                self.lookup_action('repeat').change_state(repeat_state)
            # Toggle shuffle on Ctrl + S
            if keyval == Gdk.KEY_s:
                if self._player.props.repeat_mode == RepeatMode.SHUFFLE:
                    self._player.props.repeat_mode = RepeatMode.NONE
                    repeat_state = GLib.Variant("s", ("none"))
                else:
                    self._player.props.repeat_mode = RepeatMode.SHUFFLE
                    repeat_state = GLib.Variant("s", ("shuffle"))
                self.lookup_action('repeat').change_state(repeat_state)
        # Ctrl+Shift+<KEY>
        elif modifiers == shift_ctrl_mask:
            if keyval == Gdk.KEY_A:
                self._select_none()
        # Alt+<KEY>
        elif modifiers == mod1_mask:
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

            child = self._stack.get_visible_child()
            if (keyval == Gdk.KEY_Delete
                    and child == self.views[View.PLAYLIST]):
                self.views[View.PLAYLIST].remove_playlist()
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
                and not self.views[View.PLAYLIST].rename_active
                and self._headerbar.props.state != HeaderBar.State.SEARCH):
            self._search.props.search_mode_active = True

    @log
    def _on_back_button_pressed(self, gesture, n_press, x, y):
        self._headerbar.emit('back-button-clicked')

    @log
    def _notify_mode_disconnect(self, data=None):
        self._player.stop()
        self.notifications_popup.terminate_pending()
        self._stack.disconnect(self._on_notify_model_id)

    @log
    def _on_notify_mode(self, stack, param):
        self.prev_view = self.curr_view
        self.curr_view = stack.get_visible_child()

        # Disable search mode when switching view
        search_views = [self.views[View.EMPTY], self.views[View.SEARCH]]
        if (self.curr_view in search_views
                and self.prev_view not in search_views):
            self._view_before_search = self.prev_view
        elif (self.curr_view not in search_views
                and self._search.props.search_mode_active is True):
            self._search.props.search_mode_active = False

        # Disable the selection button for the EmptySearch and Playlist
        # view
        no_selection_mode = [
            self.views[View.EMPTY],
            self.views[View.PLAYLIST]
        ]
        allowed = self.curr_view not in no_selection_mode
        self._headerbar.props.selection_mode_allowed = allowed

        # Disable renaming playlist if it was active when leaving
        # Playlist view
        if (self.prev_view == self.views[View.PLAYLIST]
                and self.views[View.PLAYLIST].rename_active):
            self.views[View.PLAYLIST].disable_rename_playlist()

    @log
    def _toggle_view(self, view_enum):
        # TODO: The SEARCH state actually refers to the child state of
        # the search mode. This fixes the behaviour as needed, but is
        # incorrect: searchview currently does not switch states
        # correctly.
        if (not self.props.selection_mode
                and not self._headerbar.props.state == HeaderBar.State.CHILD
                and not self._headerbar.props.state == HeaderBar.State.SEARCH):
            self._stack.set_visible_child(self.views[view_enum])

    @log
    def _on_search_state_changed(self, klass, param):
        if (self._search.props.state != Search.State.NONE
                or not self._view_before_search):
            return

        # Get back to the view before the search
        self._stack.set_visible_child(self._view_before_search)

    @log
    def _switch_back_from_childview(self, klass=None):
        if self.props.selection_mode:
            return

        views_with_child = [
            self.views[View.ALBUM],
            self.views[View.SEARCH],
        ]

        is_folded_childs = [
            self.views[View.ARTIST],
            self.views[View.PLAYLIST],
        ]
        for child in is_folded_childs:
            if child.is_folded:
                views_with_child.append(child)

        if self.curr_view in views_with_child:
            self.curr_view._back_button_clicked(self.curr_view)

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        if (not self.props.selection_mode
                and self._player.state == Playback.STOPPED):
            self._player_toolbar.set_visible_child(False)

    @log
    def _on_size_allocate(self, widget, allocation):
        album_view = self.views[View.ALBUM]
        artists_view = self.views[View.ARTIST]

        if allocation.width < 650:
            self.props.adaptive_view = AdaptiveViewMode.MOBILE
            self._headerbar.view = HeaderBar.View.TITLE
            self._switcher_bar.set_reveal(True)
        elif allocation.width <= 900:
            self.props.adaptive_view = AdaptiveViewMode.TABLET
            self._headerbar.view = HeaderBar.View.NARROW
            self._switcher_bar.set_reveal(False)
        else:
            self._headerbar.view = HeaderBar.View.WIDE
            self.props.adaptive_view = AdaptiveViewMode.DESKTOP
            self._switcher_bar.set_reveal(False)

    @log
    def _on_add_to_playlist(self, widget):
        if self._stack.get_visible_child() == self.views[View.PLAYLIST]:
            return

        selected_songs = self._app._coreselection.props.selected_items

        if len(selected_songs) < 1:
            return

        playlist_dialog = PlaylistDialog(self)
        if playlist_dialog.run() == Gtk.ResponseType.ACCEPT:
            playlist = playlist_dialog.props.selected_playlist
            playlist.add_songs(selected_songs)

        self.props.selection_mode = False
        playlist_dialog.destroy()

