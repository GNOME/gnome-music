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
from gi.repository import GObject, Gtk

from gnomemusic import log
from gnomemusic.grilo import grilo
from gnomemusic.views.baseview import BaseView
from gnomemusic.widgets.headerbar import HeaderBar
from gnomemusic.widgets.albumcover import AlbumCover
from gnomemusic.widgets.albumwidget import AlbumWidget
import gnomemusic.utils as utils


class AlbumsView(BaseView):

    def __repr__(self):
        return '<AlbumsView>'

    @log
    def __init__(self, window, player):
        super().__init__('albums', _("Albums"), window)

        self.player = player
        self._album_widget = AlbumWidget(
            player, self, self._header_bar, self._selection_toolbar)
        self.add(self._album_widget)
        self.albums_selected = []
        self.all_items = []
        self.items_selected = []
        self.items_selected_callback = None

    @log
    def _on_changes_pending(self, data=None):
        if (self._init and not self._header_bar.selection_mode):
            self._offset = 0
            self.populate()
            grilo.changes_pending['Albums'] = False

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        super()._on_selection_mode_changed(widget, data)

        if (not self._header_bar.selection_mode
                and grilo.changes_pending['Albums']):
            self._on_changes_pending()

    @log
    def _setup_view(self):
        self._view = Gtk.FlowBox(
            homogeneous=True, hexpand=True, halign=Gtk.Align.FILL,
            valign=Gtk.Align.START, selection_mode=Gtk.SelectionMode.NONE,
            margin=18, row_spacing=12, column_spacing=6,
            min_children_per_line=1, max_children_per_line=20)

        self._view.get_style_context().add_class('content-view')
        self._view.connect('child-activated', self._on_child_activated)

        scrolledwin = Gtk.ScrolledWindow()
        scrolledwin.add(self._view)
        scrolledwin.show()

        self._box.add(scrolledwin)

    @log
    def _back_button_clicked(self, widget, data=None):
        self._header_bar.state = HeaderBar.State.MAIN
        self.set_visible_child(self._grid)

    @log
    def _on_child_activated(self, widget, child, user_data=None):
        if self.props.selection_mode:
            return

        item = child.props.media
        # Update and display the album widget if not in selection mode
        self._album_widget.update(item)

        self._header_bar.props.state = HeaderBar.State.CHILD
        self._header_bar.props.title = utils.get_album_title(item)
        self._header_bar.props.subtitle = utils.get_artist_name(item)
        self.set_visible_child(self._album_widget)

    @log
    def populate(self):
        self._window.notifications_popup.push_loading()
        grilo.populate_albums(self._offset, self._add_item)
        self._init = True

    @log
    def get_selected_songs(self, callback):
        # FIXME: we call into private objects with full knowledge of
        # what is there
        if self._header_bar.props.state == HeaderBar.State.CHILD:
            callback(self._album_widget._disc_listbox.get_selected_items())
        else:
            self.items_selected = []
            self.items_selected_callback = callback
            self.albums_index = 0
            if len(self.albums_selected):
                self._get_selected_album_songs()

    @log
    def _add_item(self, source, param, item, remaining=0, data=None):
        if item:
            # Store all items to optimize 'Select All' action
            self.all_items.append(item)

            # Add to the flowbox
            child = self._create_album_item(item)
            self._view.add(child)
            self._offset += 1
        elif remaining == 0:
            self._view.show()
            self._window.notifications_popup.pop_loading()
            self._init = False

    def _create_album_item(self, item):
        child = AlbumCover(item)

        child.connect('notify::selected', self._on_selection_changed)

        self.bind_property(
            'selection-mode', child, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL)

        return child

    @log
    def _on_selection_changed(self, child, data=None):
        if (child.props.selected
                and child.props.media not in self.albums_selected):
            self.albums_selected.append(child.props.media)
        elif (not child.props.selected
                and child.props.media in self.albums_selected):
            self.albums_selected.remove(child.props.media)

        self._update_header_from_selection(len(self.albums_selected))

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

    def _toggle_all_selection(self, selected):
        """
        Selects or unselects all items without sending the notify::active
        signal for performance purposes.
        """
        for child in self._view.get_children():
            child.props.selected = selected

    @log
    def select_all(self):
        self.albums_selected = list(self.all_items)
        self._toggle_all_selection(True)

    @log
    def unselect_all(self):
        self.albums_selected = []
        self._toggle_all_selection(False)
