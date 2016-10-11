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

    def __repr__(self):
        return '<ArtistsView>'

    @log
    def __init__(self, window, player):
        BaseView.__init__(self, 'artists', _("Artists"), window,
                          Gd.MainViewType.LIST, True)
        self.artists_counter = 0
        self.player = player
        self._artists = {}
        self.albums_selected = []
        self.items_selected = []
        self.items_selected_callback = None
        self.artistAlbumsStack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE,
        )
        self._artistAlbumsWidget = Gtk.Frame(
            shadow_type=Gtk.ShadowType.NONE,
            hexpand=True
        )
        self.artistAlbumsStack.add_named(self._artistAlbumsWidget, "sidebar")
        self.artistAlbumsStack.set_visible_child_name("sidebar")
        self.view.set_shadow_type(Gtk.ShadowType.IN)
        self.view.get_style_context().add_class('side-panel')
        self.view.set_hexpand(False)
        self.view.get_generic_view().get_selection().set_mode(
            Gtk.SelectionMode.SINGLE)
        self._grid.attach(self.artistAlbumsStack, 2, 0, 2, 2)
        self._add_list_renderers()
        self.view.get_generic_view().get_style_context().remove_class('content-view')
        self.show_all()
        self.view.hide()

    @log
    def _on_changes_pending(self, data=None):
        if (self._init and self.header_bar._selectionMode is False):
            self.model.clear()
            self._artists.clear()
            self._offset = 0
            GLib.idle_add(self._populate)
            grilo.changes_pending['Artists'] = False

    @log
    def _populate(self, data=None):
        self._init = True
        self.populate()

    @log
    def _add_list_renderers(self):
        list_widget = self.view.get_generic_view()

        cols = list_widget.get_columns()
        cells = cols[0].get_cells()
        cells[1].set_visible(False)
        cells[2].set_visible(False)
        self.text_renderer = Gd.StyledTextRenderer(
            xpad=16,
            ypad=16,
            ellipsize=Pango.EllipsizeMode.END,
            xalign=0.0,
            width=220
        )
        list_widget.add_renderer(self.text_renderer, lambda *args: None, None)
        cols[0].clear_attributes(self.text_renderer)
        cols[0].add_attribute(self.text_renderer, 'text', 2)

    @log
    def _on_item_activated(self, widget, item_id, path):
        if self.star_handler.star_renderer_click:
            self.star_handler.star_renderer_click = False
            return

        try:
            _iter = self.model.get_iter(path)
        except TypeError:
            return
        self._last_selection = _iter
        artist = self.model.get_value(_iter, 2)
        albums = self._artists[artist.casefold()]['albums']

        widget = self._artists[artist.casefold()]['widget']
        if widget:
            # FIXME: internal call
            if widget._model == self.player.running_playlist('Artist', widget.artist):
                self._artistAlbumsWidget = widget.get_parent()
                GLib.idle_add(self.artistAlbumsStack.set_visible_child,
                              self._artistAlbumsWidget)
                return
            elif widget.get_parent() == self._artistAlbumsWidget:
                return
            else:
                widget.get_parent().destroy()

        # Prepare a new artistAlbumsWidget here
        new_artistAlbumsWidget = Gtk.Frame(
            shadow_type=Gtk.ShadowType.NONE,
            hexpand=True
        )
        self.artistAlbumsStack.add(new_artistAlbumsWidget)

        artistAlbums = None

        artistAlbums = ArtistAlbumsWidget(
            artist, albums, self.player,
            self.header_bar, self.selection_toolbar, self.window
        )
        self._artists[artist.casefold()]['widget'] = artistAlbums
        new_artistAlbumsWidget.add(artistAlbums)
        new_artistAlbumsWidget.show()

        # Replace previous widget
        self._artistAlbumsWidget = new_artistAlbumsWidget
        GLib.idle_add(self.artistAlbumsStack.set_visible_child, new_artistAlbumsWidget)

    @log
    def _add_item(self, source, param, item, remaining=0, data=None):
        self.window.notification.set_timeout(0)
        if item is None:
            if remaining == 0:
                self.view.set_model(self.model)
                self.window.notification.dismiss()
                self.view.show()
            return
        self._offset += 1
        artist = utils.get_artist_name(item)
        if not artist.casefold() in self._artists:
            _iter = self.model.insert_with_valuesv(-1, [2], [artist])
            self._artists[artist.casefold()] = {'iter': _iter, 'albums': [], 'widget': None}

        self._artists[artist.casefold()]['albums'].append(item)

    @log
    def populate(self):
        self.window._init_loading_notification()
        GLib.idle_add(grilo.populate_artists, self._offset, self._add_item)

    @log
    def _on_header_bar_toggled(self, button):
        BaseView._on_header_bar_toggled(self, button)

        if button.get_active():
            self.text_renderer.set_fixed_size(178, -1)
            self._last_selection =\
                self.view.get_generic_view().get_selection().get_selected()[1]
            self.view.get_generic_view().get_selection().set_mode(
                Gtk.SelectionMode.NONE)
        else:
            self.text_renderer.set_fixed_size(220, -1)
            self.view.get_generic_view().get_selection().set_mode(
                Gtk.SelectionMode.SINGLE)
            if self._last_selection is not None:
                self.view.get_generic_view().get_selection().select_iter(
                    self._last_selection)

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        self.artistAlbumsStack.set_sensitive(not self.header_bar._selectionMode)
        if self.header_bar._selectionMode is False and grilo.changes_pending['Artists'] is True:
            self._on_changes_pending()

    @log
    def get_selected_tracks(self, callback):
        self.items_selected = []
        self.items_selected_callback = callback
        self.albums_index = 0
        self.albums_selected = []

        for path in self.view.get_selection():
            _iter = self.model.get_iter(path)
            artist = self.model.get_value(_iter, 2)
            albums = self._artists[artist.casefold()]['albums']
            self.albums_selected.extend(albums)

        if len(self.albums_selected):
            self._get_selected_album_songs()

    @log
    def _get_selected_album_songs(self):
        grilo.populate_album_songs(
            self.albums_selected[self.albums_index],
            self._add_selected_item)
        self.albums_index += 1

    @log
    def _add_selected_item(self, source, param, item, remaining=0, data=None):
        if item:
            self.items_selected.append(item)
        if remaining == 0:
            if self.albums_index < len(self.albums_selected):
                self._get_selected_album_songs()
            else:
                self.items_selected_callback(self.items_selected)
