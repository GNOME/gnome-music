# Copyright (c) 2016 The GNOME Music Developers
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

import logging
from gettext import gettext as _
from gi.repository import Gdk, Gtk

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.player import PlayerPlaylist
from gnomemusic.views.baseview import BaseView
from gnomemusic.widgets.artistalbumswidget import ArtistAlbumsWidget
from gnomemusic.widgets.sidebarrow import SidebarRow
import gnomemusic.utils as utils

logger = logging.getLogger(__name__)


class ArtistsView(BaseView):
    """Main view of all available artists

    Consists of a list of artists on the left side and an overview of
    all albums by this artist on the right side.
    """

    def __repr__(self):
        return '<ArtistsView>'

    @log
    def __init__(self, window, player):
        """Initialize

        :param GtkWidget window: The main window
        :param player: The main player object
        """
        self._sidebar = Gtk.ListBox()
        sidebar_container = Gtk.ScrolledWindow()
        sidebar_container.add(self._sidebar)

        super().__init__('artists', _("Artists"), window, sidebar_container)

        self.player = player
        self._artists = {}

        sidebar_container.props.width_request = 220
        sidebar_container.get_style_context().add_class('sidebar')
        self._sidebar.props.selection_mode = Gtk.SelectionMode.SINGLE
        self._sidebar.connect('row-activated', self._on_artist_activated)
        self._sidebar.connect('button-release-event', self._on_sidebar_clicked)

        self.show_all()
        self._sidebar.hide()

    @log
    def _setup_view(self):
        view_container = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self._box.pack_start(view_container, True, True, 0)

        self._view = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE)
        view_container.add(self._view)

        self._artist_albums_widget = Gtk.Frame(
            shadow_type=Gtk.ShadowType.NONE, hexpand=True)
        self._view.add_named(self._artist_albums_widget, "artist-albums")
        self._view.props.visible_child_name = "artist-albums"

    @log
    def _on_changes_pending(self, data=None):
        if (self._init
                and not self.props.selection_mode):
            self._artists.clear()
            self._offset = 0
            self._populate()
            grilo.changes_pending['Artists'] = False

    @log
    def _on_artist_activated(self, sidebar, row, data=None):
        """Initializes new artist album widgets"""
        if self.props.selection_mode:
            row.props.selected = not row.props.selected
            return

        self._last_selected_row = row
        artist = row.props.text
        albums = self._artists[artist.casefold()]['albums']
        widget = self._artists[artist.casefold()]['widget']

        if widget:
            if self.player.playing_playlist(
                    PlayerPlaylist.Type.ARTIST, widget.artist):
                self._artist_albums_widget = widget.get_parent()
                self._view.set_visible_child(self._artist_albums_widget)
                return
            elif widget.get_parent() == self._view:
                return
            else:
                widget.get_parent().destroy()

        # Prepare a new artist_albums_widget here
        new_artist_albums_widget = Gtk.Frame(
            shadow_type=Gtk.ShadowType.NONE, hexpand=True)
        self._view.add(new_artist_albums_widget)

        artist_albums = ArtistAlbumsWidget(
            artist, albums, self.player, self._window)
        self._artists[artist.casefold()]['widget'] = artist_albums
        new_artist_albums_widget.add(artist_albums)
        new_artist_albums_widget.show()

        # Replace previous widget
        self._artist_albums_widget = new_artist_albums_widget
        self._view.set_visible_child(new_artist_albums_widget)

    @log
    def _add_item(self, source, param, item, remaining=0, data=None):
        if (not item and remaining == 0):
            self._window.notifications_popup.pop_loading()
            self._sidebar.show()
            return
        self._offset += 1
        artist = utils.get_artist_name(item)
        row = None
        if not artist.casefold() in self._artists:
            # populate sidebar
            row = SidebarRow()
            row.props.text = artist
            row.connect('notify::selected', self._on_selection_changed)
            self.bind_property('selection-mode', row, 'selection-mode')
            self._sidebar.add(row)

            self._artists[artist.casefold()] = {
                'albums': [],
                'widget': None
            }

        self._artists[artist.casefold()]['albums'].append(item)

        if (row is not None
                and len(self._sidebar) == 1):
            self._sidebar.select_row(row)
            self._sidebar.emit('row-activated', row)

    @log
    def populate(self):
        """Populates the view"""
        self._window.notifications_popup.push_loading()
        grilo.populate_artists(self._offset, self._add_item)
        self._init = True

    @log
    def _on_sidebar_clicked(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        if ((event.get_state() & modifiers) == Gdk.ModifierType.CONTROL_MASK
                and not self.props.selection_mode):
            self._on_selection_mode_request()

    @log
    def _on_selection_changed(self, widget, value, data=None):
        selected_artists = 0
        for row in self._sidebar:
            if row.props.selected:
                selected_artists += 1

        self.props.selected_items_count = selected_artists

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        super()._on_selection_mode_changed(widget, data)

        self._view.props.sensitive = not self.props.selection_mode
        if self.props.selection_mode:
            self._sidebar.props.selection_mode = Gtk.SelectionMode.NONE
        else:
            self._sidebar.props.selection_mode = Gtk.SelectionMode.SINGLE

        if (not self.props.selection_mode
                and grilo.changes_pending['Artists']):
            self._on_changes_pending()

    @log
    def _toggle_all_selection(self, selected):
        for row in self._sidebar:
            row.props.selected = selected

    @log
    def select_all(self):
        self._toggle_all_selection(True)

    @log
    def unselect_all(self):
        self._toggle_all_selection(False)

    @log
    def get_selected_songs(self, callback):
        """Returns a list of songs selected

        In this view this will be all albums of the selected artists.
        :returns: All selected songs
        :rtype: A list of songs
        """
        selected_albums = []
        for row in self._sidebar:
            if row.props.selected:
                artist = row.props.text
                albums = self._artists[artist.casefold()]['albums']
                selected_albums.extend(albums)

        if len(selected_albums) > 0:
            self._get_selected_albums_songs(selected_albums, callback)

    @log
    def _get_selected_albums_songs(self, albums, callback):
        selected_songs = []
        self._album_index = 0

        def add_songs(source, param, item, remaining, data=None):
            if item:
                selected_songs.append(item)
            if remaining == 0:
                self._album_index += 1
                if self._album_index < len(albums):
                    grilo.populate_album_songs(
                        albums[self._album_index], add_songs)
                else:
                    callback(selected_songs)

        grilo.populate_album_songs(albums[self._album_index], add_songs)
