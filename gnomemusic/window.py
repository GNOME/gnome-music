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
from gnomemusic import TrackerWrapper
from gnomemusic.toolbar import Toolbar, ToolbarState
from gnomemusic.player import Player, SelectionToolbar, RepeatType
from gnomemusic.query import Query
from gnomemusic.views.albumsview import AlbumsView
from gnomemusic.views.artistsview import ArtistsView
from gnomemusic.views.emptyview import EmptyView
from gnomemusic.views.emptysearchview import EmptySearchView
from gnomemusic.views.initialstateview import InitialStateView
from gnomemusic.views.searchview import SearchView
from gnomemusic.views.songsview import SongsView
from gnomemusic.views.playlistview import PlaylistView
from gnomemusic.widgets.playlistdialog import PlaylistDialog
from gnomemusic.playlists import Playlists
from gnomemusic.grilo import grilo

import logging
logger = logging.getLogger(__name__)

tracker = TrackerWrapper().tracker
playlist = Playlists.get_default()


class Window(Gtk.ApplicationWindow):

    def __repr__(self):
        return '<Window>'

    @log
    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self,
                                       application=app,
                                       title=_("Music"))
        self.connect('focus-in-event', self._windows_focus_cb)
        self.settings = Gio.Settings.new('org.gnome.Music')
        self.add_action(self.settings.create_action('repeat'))
        selectAll = Gio.SimpleAction.new('selectAll', None)
        app.add_accelerator('<Primary>a', 'win.selectAll', None)
        selectAll.connect('activate', self._on_select_all)
        self.add_action(selectAll)
        selectNone = Gio.SimpleAction.new('selectNone', None)
        selectNone.connect('activate', self._on_select_none)
        self.add_action(selectNone)
        self.set_size_request(200, 100)
        self.set_default_icon_name('gnome-music')
        self.notification_handler = None
        self._loading_counter = 0

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
        self._setup_loading_notification()
        self._setup_playlist_notification()

        self.window_size_update_timeout = None
        self.connect("window-state-event", self._on_window_state_event)
        self.connect("configure-event", self._on_configure_event)
        grilo.connect('changes-pending', self._on_changes_pending)

    @log
    def _setup_loading_notification(self):
        self._loading_notification = Gtk.Revealer(
                       halign=Gtk.Align.CENTER, valign=Gtk.Align.START)
        self._loading_notification.set_transition_type(
                                 Gtk.RevealerTransitionType.SLIDE_DOWN)
        self._overlay.add_overlay(self._loading_notification)

        grid = Gtk.Grid(margin_bottom=18, margin_start=18, margin_end=18)
        grid.set_column_spacing(18)
        grid.get_style_context().add_class('app-notification')

        spinner = Gtk.Spinner()
        spinner.start()
        grid.add(spinner)

        label = Gtk.Label.new(_("Loading"))
        grid.add(label)

        self._loading_notification.add(grid)
        self._loading_notification.show_all()

    @log
    def _setup_playlist_notification(self):
        self._playlist_notification_timeout_id = 0
        self._playlist_notification = Gtk.Revealer(halign=Gtk.Align.CENTER,
                                                   valign=Gtk.Align.START)
        self._playlist_notification.set_transition_type(
                       Gtk.RevealerTransitionType.SLIDE_DOWN)
        self._overlay.add_overlay(self._playlist_notification)

        grid = Gtk.Grid(margin_bottom=18, margin_start=18, margin_end=18)
        grid.set_column_spacing(12)
        grid.get_style_context().add_class('app-notification')

        def remove_notification_timeout(self):
            # Remove the timeout if any
            if self._playlist_notification_timeout_id > 0:
                GLib.source_remove(self._playlist_notification_timeout_id)
                self._playlist_notification_timeout_id = 0

        # Undo playlist removal
        def undo_remove_cb(button, self):
            self._playlist_notification.set_reveal_child(False)
            self.views[3].undo_playlist_deletion()

            remove_notification_timeout(self)

        # Playlist name label
        self._playlist_notification.label = Gtk.Label('')
        grid.add(self._playlist_notification.label)

        # Undo button
        undo_button = Gtk.Button.new_with_mnemonic(_("_Undo"))
        undo_button.connect("clicked", undo_remove_cb, self)
        grid.add(undo_button)

        self._playlist_notification.add(grid)
        self._playlist_notification.show_all()

    @log
    def _on_changes_pending(self, data=None):
        def songs_available_cb(available):
            if available:
                if self.views[0] == self.views[-1]:
                    view = self.views.pop()
                    view.destroy()
                    self._switch_to_player_view()
                    self.toolbar._search_button.set_sensitive(True)
                    self.toolbar._select_button.set_sensitive(True)
                    self.toolbar.show_stack()
            elif (self.toolbar._selectionMode is False
                    and len(self.views) != 1):
                self._stack.disconnect(self._on_notify_model_id)
                self.disconnect(self._key_press_event_id)
                view_count = len(self.views)
                for i in range(0, view_count):
                    view = self.views.pop()
                    view.destroy()
                self.toolbar.hide_stack()
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
    def _on_window_state_event(self, widget, event):
        self.settings.set_boolean('window-maximized', 'GDK_WINDOW_STATE_MAXIMIZED' in event.new_window_state.value_names)

    @log
    def _grab_media_player_keys(self):
        self.proxy = Gio.DBusProxy.new_sync(Gio.bus_get_sync(Gio.BusType.SESSION, None),
                                            Gio.DBusProxyFlags.NONE,
                                            None,
                                            'org.gnome.SettingsDaemon.MediaKeys',
                                            '/org/gnome/SettingsDaemon/MediaKeys',
                                            'org.gnome.SettingsDaemon.MediaKeys',
                                            None)
        self.proxy.call_sync('GrabMediaPlayerKeys',
                             GLib.Variant('(su)', ('Music', 0)),
                             Gio.DBusCallFlags.NONE,
                             -1,
                             None)
        self.proxy.connect('g-signal', self._handle_media_keys)

    @log
    def _windows_focus_cb(self, window, event):
        try:
            self._grab_media_player_keys()
        except GLib.GError:
            # We cannot grab media keys if no settings daemon is running
            pass

    @log
    def _handle_media_keys(self, proxy, sender, signal, parameters):
        if signal != 'MediaPlayerKeyPressed':
            print('Received an unexpected signal \'%s\' from media player'.format(signal))
            return
        response = parameters.get_child_value(1).get_string()
        if 'Play' in response:
            self.player.play_pause()
        elif 'Stop' in response:
            self.player.Stop()
        elif 'Next' in response:
            self.player.play_next()
        elif 'Previous' in response:
            self.player.play_previous()

    @log
    def _setup_view(self):
        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.player = Player(self)
        self.selection_toolbar = SelectionToolbar()
        self.toolbar = Toolbar()
        self.views = []
        self._stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE,
            transition_duration=100,
            visible=True,
            can_focus=False)

        # Add the 'background' styleclass so it properly hides the
        # bottom line of the searchbar
        self._stack.get_style_context().add_class('background')

        self._overlay = Gtk.Overlay(child=self._stack)
        self._overlay.add_overlay(self.toolbar.dropdown)
        self.set_titlebar(self.toolbar.header_bar)
        self._box.pack_start(self.toolbar.searchbar, False, False, 0)
        self._box.pack_start(self._overlay, True, True, 0)
        self._box.pack_start(self.player.actionbar, False, False, 0)
        self._box.pack_start(self.selection_toolbar.actionbar, False, False, 0)
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

        self.toolbar._search_button.connect('toggled', self._on_search_toggled)
        self.toolbar.connect('selection-mode-changed', self._on_selection_mode_changed)
        self.selection_toolbar._add_to_playlist_button.connect(
            'clicked', self._on_add_to_playlist_button_clicked)
        self.selection_toolbar._remove_from_playlist_button.connect(
            'clicked', self._on_remove_from_playlist_button_clicked)

        self.toolbar.set_state(ToolbarState.MAIN)
        self.toolbar.header_bar.show()
        self._overlay.show()
        self.player.actionbar.show_all()
        self._box.show()
        self.show()

    @log
    def _switch_to_empty_view(self):
        did_initial_state = self.settings.get_boolean('did-initial-state')
        view_class = None
        if did_initial_state:
            view_class = EmptyView
        else:
            view_class = InitialStateView
        self.views.append(view_class(self, self.player))

        self._stack.add_titled(self.views[0], _("Empty"), _("Empty"))
        self.toolbar._search_button.set_sensitive(False)
        self.toolbar._select_button.set_sensitive(False)

    @log
    def _switch_to_player_view(self):
        self.settings.set_boolean('did-initial-state', True)
        self._on_notify_model_id = self._stack.connect('notify::visible-child', self._on_notify_mode)
        self.connect('destroy', self._notify_mode_disconnect)
        self._key_press_event_id = self.connect('key_press_event', self._on_key_press)

        self.views.append(AlbumsView(self, self.player))
        self.views.append(ArtistsView(self, self.player))
        self.views.append(SongsView(self, self.player))
        self.views.append(PlaylistView(self, self.player))
        self.views.append(SearchView(self, self.player))
        self.views.append(EmptySearchView(self, self.player))

        for i in self.views:
            if i.title:
                self._stack.add_titled(i, i.name, i.title)
            else:
                self._stack.add_named(i, i.name)

        self.toolbar.set_stack(self._stack)
        self.toolbar.searchbar.show()
        self.toolbar.dropdown.show()

        for i in self.views:
            GLib.idle_add(i.populate)

    @log
    def _on_select_all(self, action, param):
        if self.toolbar._selectionMode is False:
            return
        if self.toolbar._state == ToolbarState.MAIN:
            view = self._stack.get_visible_child()
        else:
            view = self._stack.get_visible_child().get_visible_child()

        view.select_all()

    @log
    def _on_select_none(self, action, param):
        if self.toolbar._state == ToolbarState.MAIN:
            view = self._stack.get_visible_child()
            view.unselect_all()
        else:
            view = self._stack.get_visible_child().get_visible_child()
            view.select_none()

    @log
    def show_playlist_notification(self):
        """Show a notification on playlist removal and provide an
        option to undo for 5 seconds.
        """

        # Callback to remove playlists
        def remove_playlist_timeout_cb(self):
            # Remove the playlist
            playlist.delete_playlist(self.views[3].pl_todelete)

            # Hide the notification
            self._playlist_notification.set_reveal_child(False)

            # Stop the timeout
            self._playlist_notification_timeout_id = 0

            return GLib.SOURCE_REMOVE

        # If a notification is already visible, remove that playlist
        if self._playlist_notification_timeout_id > 0:
            GLib.source_remove(self._playlist_notification_timeout_id)
            remove_playlist_timeout_cb(self)

        playlist_title = self.views[3].current_playlist.get_title()
        label = _("Playlist {} removed".format(playlist_title))

        self._playlist_notification.label.set_label(label)
        self._playlist_notification.set_reveal_child(True)

        timeout_id = GLib.timeout_add_seconds(5, remove_playlist_timeout_cb,
                                              self)
        self._playlist_notification_timeout_id = timeout_id

    @log
    def _on_key_press(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        event_and_modifiers = (event.state & modifiers)

        if event_and_modifiers != 0:
            # Open search bar on Ctrl + F
            if (event.keyval == Gdk.KEY_f and
                    event_and_modifiers == Gdk.ModifierType.CONTROL_MASK):
                self.toolbar.searchbar.toggle_bar()
            # Play / Pause on Ctrl + SPACE
            if (event.keyval == Gdk.KEY_space
                    and event_and_modifiers == Gdk.ModifierType.CONTROL_MASK):
                self.player.play_pause()
            # Play previous on Ctrl + B
            if (event.keyval == Gdk.KEY_b
                    and event_and_modifiers == Gdk.ModifierType.CONTROL_MASK):
                self.player.play_previous()
            # Play next on Ctrl + N
            if (event.keyval == Gdk.KEY_n
                    and event_and_modifiers == Gdk.ModifierType.CONTROL_MASK):
                self.player.play_next()
            # Toggle repeat on Ctrl + R
            if (event.keyval == Gdk.KEY_r
                    and event_and_modifiers == Gdk.ModifierType.CONTROL_MASK):
                if self.player.get_repeat_mode() == RepeatType.SONG:
                    self.player.set_repeat_mode(RepeatType.NONE)
                else:
                    self.player.set_repeat_mode(RepeatType.SONG)
            # Toggle shuffle on Ctrl + S
            if (event.keyval == Gdk.KEY_s
                    and event_and_modifiers == Gdk.ModifierType.CONTROL_MASK):
                if self.player.get_repeat_mode() == RepeatType.SHUFFLE:
                    self.player.set_repeat_mode(RepeatType.NONE)
                else:
                    self.player.set_repeat_mode(RepeatType.SHUFFLE)
            # Go back from Album view on Alt + Left
            if (event.keyval == Gdk.KEY_Left and
                    event_and_modifiers == Gdk.ModifierType.MOD1_MASK):
                if (self.toolbar._state != ToolbarState.MAIN):
                    self.curr_view.set_visible_child(self.curr_view._grid)
                    self.toolbar.set_state(ToolbarState.MAIN)
            # Go to Albums view on Ctrl + 1
            if (event.keyval == Gdk.KEY_1
                    and event_and_modifiers == Gdk.ModifierType.CONTROL_MASK):
                self._toggle_view(0, 0)
            # Go to Artists view on Ctrl + 2
            if (event.keyval == Gdk.KEY_2
                    and event_and_modifiers == Gdk.ModifierType.CONTROL_MASK):
                self._toggle_view(0, 1)
            # Go to Songs view on Ctrl + 3
            if (event.keyval == Gdk.KEY_3
                    and event_and_modifiers == Gdk.ModifierType.CONTROL_MASK):
                self._toggle_view(0, 2)
            # Go to Playlists view on Ctrl + 4
            if (event.keyval == Gdk.KEY_4
                    and event_and_modifiers == Gdk.ModifierType.CONTROL_MASK):
                self._toggle_view(0, 3)
        else:
            if (event.keyval == Gdk.KEY_Delete):
                if self._stack.get_visible_child() == self.views[3]:
                    self.views[3].remove_playlist()
            # Close search bar after Esc is pressed
            if event.keyval == Gdk.KEY_Escape:
                self.toolbar.searchbar.show_bar(False)
                # Also disable selection
                if self.toolbar._selectionMode:
                    self.toolbar.set_selection_mode(False)

        # Open the search bar when typing printable chars.
        key_unic = Gdk.keyval_to_unicode(event.keyval)
        if ((not self.toolbar.searchbar.get_search_mode()
                and not event.keyval == Gdk.KEY_space)
                and GLib.unichar_isprint(chr(key_unic))
                and (event_and_modifiers == Gdk.ModifierType.SHIFT_MASK
                    or event_and_modifiers == 0)):
            self.toolbar.searchbar.show_bar(True)

    @log
    def _notify_mode_disconnect(self, data=None):
        self.player.Stop()
        self._stack.disconnect(self._on_notify_model_id)

    @log
    def _on_notify_mode(self, stack, param):
        self.prev_view = self.curr_view
        self.curr_view = stack.get_visible_child()

        # Switch to all albums view when we're clicking Albums
        if self.curr_view == self.views[0] and not (self.prev_view == self.views[4] or self.prev_view == self.views[5]):
            self.curr_view.set_visible_child(self.curr_view._grid)

        # Slide out sidebar on switching to Artists or Playlists view
        if self.curr_view == self.views[1] or \
           self.curr_view == self.views[3]:
            self.curr_view.stack.set_visible_child_name('dummy')
            self.curr_view.stack.set_visible_child_name('sidebar')
        if self.curr_view != self.views[4] and self.curr_view != self.views[5]:
            self.toolbar.searchbar.show_bar(False)

        # Toggle the selection button for the EmptySearch view
        if self.curr_view == self.views[5] or \
           self.prev_view == self.views[5]:
            self.toolbar._select_button.set_sensitive(
                not self.toolbar._select_button.get_sensitive())

    @log
    def _toggle_view(self, btn, i):
        self._stack.set_visible_child(self.views[i])

    @log
    def _on_search_toggled(self, button, data=None):
        self.toolbar.searchbar.show_bar(button.get_active(),
                                        self.curr_view != self.views[4])
        if (not button.get_active() and
                (self.curr_view == self.views[4] or self.curr_view == self.views[5])):
            if self.toolbar._state == ToolbarState.MAIN:
                # We should get back to the view before the search
                self._stack.set_visible_child(self.views[4].previous_view)
            elif (self.views[4].previous_view == self.views[0] and
                 self.curr_view.get_visible_child() != self.curr_view._albumWidget and
                 self.curr_view.get_visible_child() != self.curr_view._artistAlbumsWidget):
                self._stack.set_visible_child(self.views[0])

            if self.toolbar._selectionMode:
                self.toolbar.set_selection_mode(False)

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        if self.toolbar._selectionMode is False:
            self._on_changes_pending()
        else:
            in_playlist = self._stack.get_visible_child() == self.views[3]
            self.selection_toolbar._add_to_playlist_button.set_visible(not in_playlist)
            self.selection_toolbar._remove_from_playlist_button.set_visible(in_playlist)

    @log
    def _on_add_to_playlist_button_clicked(self, widget):
        if self._stack.get_visible_child() == self.views[3]:
            return

        def callback(selected_songs):
            if len(selected_songs) < 1:
                return

            playlist_dialog = PlaylistDialog(self, self.views[3].pl_todelete)
            if playlist_dialog.run() == Gtk.ResponseType.ACCEPT:
                playlist.add_to_playlist(playlist_dialog.get_selected(),
                                         selected_songs)
            self.toolbar.set_selection_mode(False)
            playlist_dialog.destroy()

        self._stack.get_visible_child().get_selected_songs(callback)

    @log
    def _on_remove_from_playlist_button_clicked(self, widget):
        if self._stack.get_visible_child() != self.views[3]:
            return

        def callback(selected_songs):
            if len(selected_songs) < 1:
                return

            playlist.remove_from_playlist(
                self.views[3].current_playlist,
                selected_songs)
            self.toolbar.set_selection_mode(False)

        self._stack.get_visible_child().get_selected_songs(callback)

    @log
    def push_loading_notification(self):
        """ Increases the counter of loading notification triggers
        running. If there is no notification is visible, the loading
        notification is started.
        """
        def show_notification_cb(self):
            self._loading_notification.set_reveal_child(True)
            self._show_notification_timeout_id = 0
            return GLib.SOURCE_REMOVE

        if self._loading_counter == 0:
            # Only show the notification after a small delay, thus
            # add a timeout. 500ms feels good enough.
            self._show_notification_timeout_id = GLib.timeout_add(
                    500, show_notification_cb, self)

        self._loading_counter = self._loading_counter + 1

    @log
    def pop_loading_notification(self):
        """ Decreases the counter of loading notification triggers
        running. If it reaches zero, the notification is withdrawn.
        """
        self._loading_counter = self._loading_counter - 1

        if self._loading_counter == 0:
            # Remove the previously set timeout, if any
            if self._show_notification_timeout_id > 0:
                GLib.source_remove(self._show_notification_timeout_id)
                self._show_notification_timeout_id = 0

            self._loading_notification.set_reveal_child(False)
