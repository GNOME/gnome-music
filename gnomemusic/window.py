# Copyright (c) 2013 Eslam Mostafa <cseslam@gmail.com>
# Copyright (c) 2013 Vadim Rutkovsky <vrutkovs@redhat.com>
# Copyright (c) 2013 Sai Suman Prayaga <suman.sai14@gmail.com>
# Copyright (c) 2013 Arnel A. Borja <kyoushuu@yahoo.com>
# Copyright (c) 2013 Shivani Poddar <shivani.poddar92@gmail.com>
# Copyright (c) 2013 Manish Sinha <manishsinha@ubuntu.com>
# Copyright (c) 2013 Seif Lotfy <seif@gmail.com>
# Copyright (c) 2013 Guillaume Quintard <guillaume.quintard@gmail.com>
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

from gi.repository import Gtk, Gdk, Gio, GLib
from gettext import gettext as _

from gnomemusic import log
from gnomemusic.mediakeys import MediaKeys
from gnomemusic.player import Player, RepeatMode
from gnomemusic.query import Query
from gnomemusic.utils import View
from gnomemusic.views.albumsview import AlbumsView
from gnomemusic.views.artistsview import ArtistsView
from gnomemusic.views.emptyview import EmptyView
from gnomemusic.views.searchview import SearchView
from gnomemusic.views.songsview import SongsView
from gnomemusic.views.playlistview import PlaylistView
from gnomemusic.widgets.headerbar import HeaderBar
from gnomemusic.widgets.notificationspopup import NotificationsPopup
from gnomemusic.widgets.playertoolbar import PlayerToolbar
from gnomemusic.widgets.playlistdialog import PlaylistDialog
from gnomemusic.widgets.selectiontoolbar import SelectionToolbar
from gnomemusic.playlists import Playlists
from gnomemusic.grilo import grilo

import logging
logger = logging.getLogger(__name__)

playlists = Playlists.get_default()


class Window(Gtk.ApplicationWindow):

    def __repr__(self):
        return '<Window>'

    @log
    def __init__(self, app):
        super().__init__(application=app, title=_("Music"))

        self.settings = Gio.Settings.new('org.gnome.Music')
        self.add_action(self.settings.create_action('repeat'))
        select_all = Gio.SimpleAction.new('select_all', None)
        select_all.connect('activate', self._select_all)
        self.add_action(select_all)
        select_none = Gio.SimpleAction.new('select_none', None)
        select_none.connect('activate', self._select_none)
        self.add_action(select_none)

        self.set_size_request(200, 100)

        self.prev_view = None
        self.curr_view = None

        size_setting = self.settings.get_value('window-size')
        if isinstance(size_setting[0], int) and isinstance(size_setting[1], int):
            self.resize(size_setting[0], size_setting[1])

        position_setting = self.settings.get_value('window-position')
        if len(position_setting) == 2 \
           and isinstance(position_setting[0], int) \
           and isinstance(position_setting[1], int):
            self.move(position_setting[0], position_setting[1])

        if self.settings.get_value('window-maximized'):
            self.maximize()

        self._setup_view()
        self.notifications_popup = NotificationsPopup()
        self._overlay.add_overlay(self.notifications_popup)

        MediaKeys(self.player, self)

        self.window_size_update_timeout = None
        self.connect("notify::is-maximized", self._on_maximized)
        self.connect("configure-event", self._on_configure_event)
        grilo.connect('changes-pending', self._on_changes_pending)

    @log
    def _on_changes_pending(self, data=None):
        # FIXME: This is not working right.
        def songs_available_cb(available):
            view_count = len(self.views)
            if (available
                    and view_count == 1):
                self._switch_to_player_view()
            elif (not available
                    and not self.headerbar.props.selection_mode
                    and view_count != 1):
                self._stack.disconnect(self._on_notify_model_id)
                self.disconnect(self._key_press_event_id)

                for i in range(View.ALBUM, view_count):
                    view = self.views.pop()
                    view.destroy()

                self._switch_to_empty_view()

        grilo.songs_available(songs_available_cb)

    @log
    def _on_configure_event(self, widget, event):
        if self.window_size_update_timeout is None:
            self.window_size_update_timeout = GLib.timeout_add(500, self.store_window_size_and_position, widget)

    @log
    def store_window_size_and_position(self, widget):
        size = widget.get_size()
        self.settings.set_value('window-size', GLib.Variant('ai', [size[0], size[1]]))

        position = widget.get_position()
        self.settings.set_value('window-position', GLib.Variant('ai', [position[0], position[1]]))
        GLib.source_remove(self.window_size_update_timeout)
        self.window_size_update_timeout = None
        return False

    @log
    def _on_maximized(self, klass, value, data=None):
        self.settings.set_boolean('window-maximized', self.is_maximized())

    @log
    def _setup_view(self):
        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.headerbar = HeaderBar()
        self.player = Player(self)
        self.player_toolbar = PlayerToolbar(self.player, self.headerbar)
        self.selection_toolbar = SelectionToolbar()
        self.views = [None] * len(View)
        self._stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE,
            transition_duration=100,
            homogeneous=False,
            visible=True,
            can_focus=False)

        # Create only the empty view at startup
        # if no music, switch to empty view and hide stack
        # if some music is available, populate stack with mainviews,
        # show stack and set empty_view to empty_search_view
        self.views[View.EMPTY] = EmptyView()
        self._stack.add_named(self.views[View.EMPTY], "emptyview")

        # Add the 'background' styleclass so it properly hides the
        # bottom line of the searchbar
        self._stack.get_style_context().add_class('background')

        self._overlay = Gtk.Overlay()
        self._overlay.add(self._stack)
        # FIXME: Need to find a proper way to do this.
        self._overlay.add_overlay(self.headerbar.searchbar._dropdown)
        self.set_titlebar(self.headerbar)
        self._box.pack_start(self.headerbar.searchbar, False, False, 0)
        self._box.pack_start(self._overlay, True, True, 0)
        self._box.pack_start(self.player_toolbar, False, False, 0)
        self._box.pack_start(self.selection_toolbar, False, False, 0)
        self.add(self._box)

        def songs_available_cb(available):
            if available:
                self._switch_to_player_view()
            else:
                self._switch_to_empty_view()

        Query()
        if Query.music_folder:
            grilo.songs_available(songs_available_cb)
        else:
            self._switch_to_empty_view()

        self.headerbar._search_button.connect(
            'toggled', self._on_search_toggled)
        self.headerbar.connect(
            'notify::selection-mode', self._on_selection_mode_changed)
        self.selection_toolbar.connect(
            'add-to-playlist', self._on_add_to_playlist)

        self.headerbar.props.state = HeaderBar.State.MAIN
        self.headerbar.show()
        self._overlay.show()
        self.player_toolbar.show_all()
        self._box.show()
        self.show()

    @log
    def _switch_to_empty_view(self):
        did_initial_state = self.settings.get_boolean('did-initial-state')

        if did_initial_state:
            self.views[View.EMPTY].props.state = EmptyView.State.EMPTY
        else:
            self.views[View.EMPTY].props.state = EmptyView.State.INITIAL

        self.headerbar.props.state = HeaderBar.State.EMPTY

    @log
    def _switch_to_player_view(self):
        self.settings.set_boolean('did-initial-state', True)
        self._on_notify_model_id = self._stack.connect(
            'notify::visible-child', self._on_notify_mode)
        self.connect('destroy', self._notify_mode_disconnect)
        self._key_press_event_id = self.connect(
            'key_press_event', self._on_key_press)

        self.views[View.ALBUM] = AlbumsView(self, self.player)
        self.views[View.ARTIST] = ArtistsView(self, self.player)
        self.views[View.SONG] = SongsView(self, self.player)
        self.views[View.PLAYLIST] = PlaylistView(self, self.player)
        self.views[View.SEARCH] = SearchView(self, self.player)

        # empty view has already been created in self._setup_view starting at
        # View.ALBUM
        # empty view state is changed once album view is visible to prevent it
        # from being displayed during startup
        for i in self.views[View.ALBUM:]:
            if i.title:
                self._stack.add_titled(i, i.name, i.title)
            else:
                self._stack.add_named(i, i.name)

        self._stack.set_visible_child(self.views[View.ALBUM])
        self.views[View.EMPTY].props.state = EmptyView.State.SEARCH
        self.headerbar.props.state = HeaderBar.State.MAIN
        self.headerbar.props.stack = self._stack
        self.headerbar.searchbar.show()

    @log
    def _select_all(self, action=None, param=None):
        if not self.headerbar.props.selection_mode:
            return
        if self.headerbar.props.state == HeaderBar.State.MAIN:
            view = self._stack.get_visible_child()
        else:
            view = self._stack.get_visible_child().get_visible_child()

        view.select_all()

    @log
    def _select_none(self, action=None, param=None):
        if not self.headerbar.props.selection_mode:
            return
        if self.headerbar.props.state == HeaderBar.State.MAIN:
            view = self._stack.get_visible_child()
            view.unselect_all()
        else:
            view = self._stack.get_visible_child().get_visible_child()
            view.select_none()

    @log
    def _on_key_press(self, widget, event):
        modifiers = event.get_state()
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
                    and self.headerbar.props.state != HeaderBar.State.SEARCH):
                self.headerbar.searchbar.toggle()
            # Play / Pause on Ctrl + SPACE
            if keyval == Gdk.KEY_space:
                self.player.play_pause()
            # Play previous on Ctrl + B
            if keyval == Gdk.KEY_b:
                self.player.previous()
            # Play next on Ctrl + N
            if keyval == Gdk.KEY_n:
                self.player.next()
            # Toggle repeat on Ctrl + R
            if keyval == Gdk.KEY_r:
                if self.player.props.repeat_mode == RepeatMode.SONG:
                    self.player.props.repeat_mode = RepeatMode.NONE
                else:
                    self.player.props.repeat_mode = RepeatMode.SONG
            # Toggle shuffle on Ctrl + S
            if keyval == Gdk.KEY_s:
                if self.player.props.repeat_mode == RepeatMode.SHUFFLE:
                    self.player.props.repeat_mode = RepeatMode.NONE
                else:
                    self.player.props.repeat_mode = RepeatMode.SHUFFLE
            # Headerbar switching
            if keyval in [Gdk.KEY_1, Gdk.KEY_KP_1]:
                self._toggle_view(View.ALBUM)
            if keyval in [Gdk.KEY_2, Gdk.KEY_KP_2]:
                self._toggle_view(View.ARTIST)
            if keyval in [Gdk.KEY_3, Gdk.KEY_KP_3]:
                self._toggle_view(View.SONG)
            if keyval in [Gdk.KEY_4, Gdk.KEY_KP_4]:
                self._toggle_view(View.PLAYLIST)
        # Ctrl+Shift+<KEY>
        elif modifiers == shift_ctrl_mask:
            if keyval == Gdk.KEY_A:
                self._select_none()
        # Alt+<KEY>
        elif modifiers == mod1_mask:
            # Go back from Album view on Alt + Left
            if keyval == Gdk.KEY_Left:
                self.headerbar._on_back_button_clicked()
        # No modifier
        else:
            if (keyval == Gdk.KEY_AudioPlay
                    or keyval == Gdk.KEY_AudioPause):
                self.player.play_pause()

            if keyval == Gdk.KEY_AudioStop:
                self.player.stop()

            if keyval == Gdk.KEY_AudioPrev:
                self.player.previous()

            if keyval == Gdk.KEY_AudioNext:
                self.player.next()

            child = self._stack.get_visible_child()
            if (keyval == Gdk.KEY_Delete
                    and child == self.views[View.PLAYLIST]):
                self.views[View.PLAYLIST].remove_playlist()
            # Close selection mode or search bar after Esc is pressed
            if keyval == Gdk.KEY_Escape:
                if self.headerbar.props.selection_mode:
                    self.headerbar.props.selection_mode = False
                else:
                    self.headerbar.searchbar.reveal(False)

        # Open the search bar when typing printable chars.
        key_unic = Gdk.keyval_to_unicode(keyval)
        if ((not self.headerbar.searchbar.get_search_mode()
                and not keyval == Gdk.KEY_space)
                and GLib.unichar_isprint(chr(key_unic))
                and (modifiers == shift_mask
                     or modifiers == 0)
                and not self.views[View.PLAYLIST].rename_active
                and self.headerbar.props.state != HeaderBar.State.SEARCH):
            self.headerbar.searchbar.reveal(True)

    @log
    def do_button_release_event(self, event):
        """Override default button release event

        :param Gdk.EventButton event: Button event
        """
        __, code = event.get_button()
        # Mouse button 8 is the navigation button
        if code == 8:
            self.headerbar._on_back_button_clicked()

    @log
    def _notify_mode_disconnect(self, data=None):
        self.player.stop()
        self.notifications_popup.terminate_pending()
        self._stack.disconnect(self._on_notify_model_id)

    @log
    def _on_notify_mode(self, stack, param):
        self.prev_view = self.curr_view
        self.curr_view = stack.get_visible_child()

        # Switch to all albums view when we're clicking Albums
        if (self.curr_view == self.views[View.ALBUM]
                and not (self.prev_view == self.views[View.SEARCH]
                    or self.prev_view == self.views[View.EMPTY])):
            self.curr_view.set_visible_child(self.curr_view._grid)

        # Slide out sidebar on switching to Artists or Playlists view
        if self.curr_view == self.views[View.ARTIST] or \
           self.curr_view == self.views[View.PLAYLIST]:
            self.curr_view.stack.set_visible_child_name('dummy')
            self.curr_view.stack.set_visible_child_name('sidebar')
        if (self.curr_view != self.views[View.SEARCH]
                and self.curr_view != self.views[View.EMPTY]):
            self.headerbar.searchbar.reveal(False)

        # Disable the selection button for the EmptySearch and Playlist
        # view
        no_selection_mode = [
            self.views[View.EMPTY],
            self.views[View.PLAYLIST]
        ]
        allowed = self.curr_view not in no_selection_mode
        self.headerbar.props.selection_mode_allowed = allowed

        # Disable renaming playlist if it was active when leaving
        # Playlist view
        if (self.prev_view == self.views[View.PLAYLIST]
                and self.views[View.PLAYLIST].rename_active):
            self.views[View.PLAYLIST].disable_rename_playlist()

    @log
    def _toggle_view(self, view_enum):
        self._stack.set_visible_child(self.views[view_enum])

    @log
    def _on_search_toggled(self, button, data=None):
        self.headerbar.searchbar.reveal(
            button.get_active(), self.curr_view != self.views[View.SEARCH])
        if (not button.get_active()
                and (self.curr_view == self.views[View.SEARCH]
                    or self.curr_view == self.views[View.EMPTY])):
            child = self.curr_view.get_visible_child()
            if self.headerbar.props.state == HeaderBar.State.MAIN:
                # We should get back to the view before the search
                self._stack.set_visible_child(
                    self.views[View.SEARCH].previous_view)
            elif (self.views[View.SEARCH].previous_view == self.views[View.ALBUM]
                    and child != self.curr_view._album_widget
                    and child != self.curr_view._artist_albums_widget):
                self._stack.set_visible_child(self.views[View.ALBUM])

            if self.headerbar.props.selection_mode:
                self.headerbar.props.selection_mode = False

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        if self.headerbar.props.selection_mode == False:
            self._on_changes_pending()

    @log
    def _on_add_to_playlist(self, widget):
        if self._stack.get_visible_child() == self.views[View.PLAYLIST]:
            return

        def callback(selected_songs):
            if len(selected_songs) < 1:
                return

            playlist_dialog = PlaylistDialog(
                self, self.views[View.PLAYLIST].pls_todelete)
            if playlist_dialog.run() == Gtk.ResponseType.ACCEPT:
                playlists.add_to_playlist(
                    playlist_dialog.get_selected(), selected_songs)
            self.headerbar.props.selection_mode = False
            playlist_dialog.destroy()

        self._stack.get_visible_child().get_selected_songs(callback)

    @log
    def set_player_visible(self, visible):
        """Set PlayWidget action visibility

        :param bool visible: actionbar visibility
        """
        self.player_toolbar.set_visible(visible)
