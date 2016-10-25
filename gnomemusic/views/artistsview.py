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

from gettext import gettext as _
from gi.repository import Gd, GLib, Gtk, Pango

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.views.baseview import BaseView
from gnomemusic.widgets.artistalbumswidget import ArtistAlbumsWidget
import gnomemusic.utils as utils


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
        BaseView.__init__(self, 'artists', _("Artists"), window,
                          Gd.MainViewType.LIST, True)

        self.player = player
        self._artists = {}
        self._albums_selected = []
        self._items_selected = []
        self._items_selected_callback = None
        self._artist_albums_stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE)
        self._artist_albums_widget = Gtk.Frame(shadow_type=Gtk.ShadowType.NONE,
                                               hexpand=True)
        self._artist_albums_stack.add_named(self._artist_albums_widget,
                                            "sidebar")
        self._artist_albums_stack.set_visible_child_name("sidebar")
        self.view.set_shadow_type(Gtk.ShadowType.IN)
        self.view.get_style_context().add_class('side-panel')
        self.view.set_hexpand(False)
        self.view.get_generic_view().get_selection().set_mode(
            Gtk.SelectionMode.SINGLE)
        self._grid.attach(self._artist_albums_stack, 2, 0, 2, 2)
        self._add_list_renderers()
        self.view.get_generic_view().get_style_context().remove_class(
            'content-view')
        self.show_all()
        self.view.hide()

    @log
    def _on_changes_pending(self, data=None):
        if (self._init
                and not self.header_bar._selectionMode):
            self.model.clear()
            self._artists.clear()
            self._offset = 0
            GLib.idle_add(self._populate)
            grilo.changes_pending['Artists'] = False

    @log
    def _add_list_renderers(self):
        list_widget = self.view.get_generic_view()
        cols = list_widget.get_columns()
        cells = cols[0].get_cells()
        cells[1].set_visible(False)
        cells[2].set_visible(False)
        self.text_renderer = Gd.StyledTextRenderer(
            xpad=16, ypad=16, ellipsize=Pango.EllipsizeMode.END, xalign=0.0,
            width=220)
        list_widget.add_renderer(self.text_renderer, lambda *args: None, None)
        cols[0].clear_attributes(self.text_renderer)
        cols[0].add_attribute(self.text_renderer, 'text', 2)

    @log
    def _on_item_activated(self, widget, item_id, path):
        """Initializes new artist album widgets"""
        try:
            itr = self.model.get_iter(path)
        except ValueError as err:
            logger.warn("Error: %s, %s", err.__class__, err)
            return

        self._last_selection = itr
        artist = self.model[itr][2]
        albums = self._artists[artist.casefold()]['albums']
        widget = self._artists[artist.casefold()]['widget']

        if widget:
            artist_widget_model = self.player.running_playlist('Artist',
                                                                widget.artist)
            artist_stack = self._artist_albums_stack
            # FIXME: calling to private model
            if widget._model == artist_widget_model:
                self._artist_albums_widget = widget.get_parent()
                GLib.idle_add(self._artist_albums_stack.set_visible_child,
                              self._artist_albums_widget)
                return
            elif widget.get_parent() == artist_stack:
                return
            else:
                widget.get_parent().destroy()

        # Prepare a new artist_albums_widget here
        new_artist_albums_widget = Gtk.Frame(shadow_type=Gtk.ShadowType.NONE,
                                             hexpand=True)
        self._artist_albums_stack.add(new_artist_albums_widget)

        artist_albums = ArtistAlbumsWidget(artist, albums, self.player,
                                           self.header_bar,
                                           self.selection_toolbar, self.window)
        self._artists[artist.casefold()]['widget'] = artist_albums
        new_artist_albums_widget.add(artist_albums)
        new_artist_albums_widget.show()

        # Replace previous widget
        self._artist_albums_widget = new_artist_albums_widget
        GLib.idle_add(self._artist_albums_stack.set_visible_child,
                      new_artist_albums_widget)

    @log
    def _add_item(self, source, param, item, remaining=0, data=None):
        self.window.notification.set_timeout(0)

        if (not item and remaining == 0):
            self.view.set_model(self.model)
            self.window.notification.dismiss()
            self.view.show()
            return
        self._offset += 1
        artist = utils.get_artist_name(item)
        if not artist.casefold() in self._artists:
            itr = self.model.insert_with_valuesv(-1, [2], [artist])
            self._artists[artist.casefold()] = {
                'iter': itr,
                'albums': [],
                'widget': None
            }
        self._artists[artist.casefold()]['albums'].append(item)

    @log
    def populate(self):
        """Populates the view"""
        self.window._init_loading_notification()
        grilo.populate_artists(self._offset, self._add_item)

    @log
    def _on_header_bar_toggled(self, button):
        BaseView._on_header_bar_toggled(self, button)

        view_selection = self.view.get_generic_view().get_selection()
        if button.get_active():
            self.text_renderer.set_fixed_size(178, -1)
            self._last_selection = view_selection.get_selected()[1]
            view_selection.set_mode(Gtk.SelectionMode.NONE)
        else:
            self.text_renderer.set_fixed_size(220, -1)
            view_selection.set_mode(Gtk.SelectionMode.SINGLE)
            if self._last_selection is not None:
                view_selection.select_iter(self._last_selection)

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        self._artist_albums_stack.set_sensitive(
            not self.header_bar._selectionMode)
        if (not self.header_bar._selectionMode
                and grilo.changes_pending['Artists']):
            self._on_changes_pending()

    @log
    def get_selected_tracks(self, callback):
        """Returns a list of tracks selected

        In this view this will be all albums of the selected artists.
        :returns: All selected songs
        :rtype: A list of tracks
        """
        self._items_selected = []
        self._items_selected_callback = callback
        self._albums_index = 0
        self._albums_selected = []

        for path in self.view.get_selection():
            itr = self.model.get_iter(path)
            artist = self.model[itr][2]
            albums = self._artists[artist.casefold()]['albums']
            self._albums_selected.extend(albums)

        if len(self._albums_selected):
            self._get_selected_album_songs()

    @log
    def _get_selected_album_songs(self):
        grilo.populate_album_songs(self._albums_selected[self._albums_index],
                                   self._add_selected_item)
        self._albums_index += 1

    @log
    def _add_selected_item(self, source, param, item, remaining=0, data=None):
        if item:
            self._items_selected.append(item)
        if remaining == 0:
            if self._albums_index < len(self._albums_selected):
                self._get_selected_album_songs()
            else:
                self._items_selected_callback(self._items_selected)
