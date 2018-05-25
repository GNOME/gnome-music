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
from gi.repository import Gdk, GObject, GLib, Gtk, Pango

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.views.baseview import BaseView
from gnomemusic.widgets.artistalbumswidget import ArtistAlbumsWidget
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

        super().__init__(
            'artists', _("Artists"), window, True, sidebar_container)

        self.player = player
        self._artists = {}

        sidebar_container.props.width_request = 220
        sidebar_container.get_style_context().add_class('side-panel')
        self._sidebar.get_style_context().add_class('view')
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
                and not self._header_bar.selection_mode):
            self._artists.clear()
            self._offset = 0
            GLib.idle_add(self._populate)
            grilo.changes_pending['Artists'] = False

    @log
    def _on_artist_activated(self, sidebar, row, data=None):
        """Initializes new artist album widgets"""
        if self.selection_mode:
            return

        self._last_selected_row = row
        artist = row.artist
        albums = self._artists[artist.casefold()]['albums']
        widget = self._artists[artist.casefold()]['widget']

        if widget:
            if self.player.running_playlist('Artist', widget.artist):
                self._artist_albums_widget = widget.get_parent()
                GLib.idle_add(
                    self._view.set_visible_child, self._artist_albums_widget)
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
            artist, albums, self.player, self, self._header_bar,
            self._selection_toolbar, self._window)
        self._artists[artist.casefold()]['widget'] = artist_albums
        new_artist_albums_widget.add(artist_albums)
        new_artist_albums_widget.show()

        # Replace previous widget
        self._artist_albums_widget = new_artist_albums_widget
        GLib.idle_add(self._view.set_visible_child, new_artist_albums_widget)

    @log
    def _add_item(self, source, param, item, remaining=0, data=None):
        if (not item and remaining == 0):
            self._window.notifications_popup.pop_loading()
            self._sidebar.show()
            return
        self._offset += 1
        artist = utils.get_artist_name(item)
        if not artist.casefold() in self._artists:
            # populate sidebar
            row = Gtk.ListBoxRow()
            row.artist = artist
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            row.add(box)
            row.check = Gtk.CheckButton()
            row.check.connect('toggled', self._on_selection_toggled)
            artist_label = Gtk.Label(
                label=artist, xalign=0, xpad=16, ypad=16,
                ellipsize=Pango.EllipsizeMode.END)
            box.pack_start(row.check, False, True, 0)
            box.pack_start(artist_label, True, True, 0)
            self._sidebar.add(row)
            row.show_all()
            row.check.hide()
            row.check.bind_property(
                'visible', self, 'selection_mode',
                GObject.BindingFlags.BIDIRECTIONAL)

            self._artists[artist.casefold()] = {
                'albums': [],
                'widget': None
            }
        self._artists[artist.casefold()]['albums'].append(item)

    @log
    def populate(self):
        """Populates the view"""
        self._window.notifications_popup.push_loading()
        grilo.populate_artists(self._offset, self._add_item)

    @log
    def _on_sidebar_clicked(self, widget, event):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        if ((event.state & modifiers) == Gdk.ModifierType.CONTROL_MASK
                and not self.selection_mode):
            self._on_selection_mode_request()

        if self.selection_mode:
            row = self._sidebar.get_row_at_y(event.y)
            row.check.props.active = not row.check.props.active

    @log
    def _on_selection_toggled(self, widget, data=None):
        selected_artists = 0
        for row in self._sidebar:
            if row.check.props.active:
                selected_artists += 1

        self.update_header_from_selection(selected_artists)

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        self._view.props.sensitive = not self._header_bar.selection_mode
        if self.selection_mode:
            self._sidebar.props.selection_mode = Gtk.SelectionMode.NONE
        else:
            self._sidebar.props.selection_mode = Gtk.SelectionMode.SINGLE

        if (not self._header_bar.selection_mode
                and grilo.changes_pending['Artists']):
            self._on_changes_pending()

    @log
    def _toggle_all_selection(self, selected):
        for row in self._sidebar:
            row.check.props.active = selected

    @log
    def select_all(self):
        self._toggle_all_selection(True)
        self.update_header_from_selection(len(self._sidebar))

    @log
    def unselect_all(self):
        self._toggle_all_selection(False)
        self.update_header_from_selection(0)

    @log
    def get_selected_songs(self, callback):
        """Returns a list of songs selected

        In this view this will be all albums of the selected artists.
        :returns: All selected songs
        :rtype: A list of songs
        """
        selected_albums = []
        for row in self._sidebar:
            if row.check.props.active:
                artist = row.artist
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
