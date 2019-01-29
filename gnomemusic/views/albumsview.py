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
from gi.repository import GLib, GObject, Grl, Gtk

from gnomemusic import log
from gnomemusic.albumartcache import ArtLoader
from gnomemusic.grilo import grilo
from gnomemusic.views.baseview import BaseView
from gnomemusic.widgets.headerbar import HeaderBar
from gnomemusic.widgets.albumcover import AlbumCover
from gnomemusic.widgets.albumwidget import AlbumWidget
import gnomemusic.utils as utils

logger = logging.getLogger(__name__)


class AlbumsView(BaseView):

    def __repr__(self):
        return '<AlbumsView>'

    @log
    def __init__(self, window, player):
        super().__init__('albums', _("Albums"), window)

        self.player = player
        self._album_widget = AlbumWidget(player, self)
        self.add(self._album_widget)
        self.children_selected = []
        self.all_children = []
        self.items_selected = []
        self.items_selected_callback = None

    @log
    def _on_changes_pending(self, data=None):
        if (self._init and not self.props.selection_mode):
            self._offset = 0
            self.populate()
            grilo.changes_pending['Albums'] = False

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        super()._on_selection_mode_changed(widget, data)

        if (not self.props.selection_mode
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
        self._headerbar.state = HeaderBar.State.MAIN
        self.set_visible_child(self._grid)

    @log
    def _on_child_activated(self, widget, child, user_data=None):
        if self.props.selection_mode:
            return

        item = child.props.media
        # Update and display the album widget if not in selection mode
        self._album_widget.update(item)

        self._headerbar.props.state = HeaderBar.State.CHILD
        self._headerbar.props.title = utils.get_album_title(item)
        self._headerbar.props.subtitle = utils.get_artist_name(item)
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
        if self._headerbar.props.state == HeaderBar.State.CHILD:
            callback(self._album_widget._disc_listbox.get_selected_items())
        else:
            self.items_selected = []
            self.items_selected_callback = callback
            self.albums_index = 0
            if len(self.children_selected):
                self._get_selected_album_songs()

    @log
    def _add_item(self, source, param, item, remaining=0, data=None):
        if item:
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

        # Store all covers to optimize 'Select All' action
        self.all_children.append(child)

        child.connect('notify::selected', self._on_selection_changed)

        self.bind_property(
            'selection-mode', child, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL)

        return child

    @log
    def _on_selection_changed(self, child, data=None):
        if (child.props.selected
                and child not in self.children_selected):
            self.children_selected.append(child)
        elif (not child.props.selected
                and child in self.children_selected):
            self.children_selected.remove(child)

        self.props.selected_items_count = len(self.children_selected)

    @log
    def _get_selected_album_songs(self):
        child = self.children_selected[self.albums_index]
        grilo.populate_album_songs(child.props.media, self._add_selected_item)
        self.albums_index += 1

    @log
    def _add_selected_item(self, source, param, item, remaining=0, data=None):
        if item:
            self.items_selected.append(item)
        if remaining == 0:
            if self.albums_index < self.props.selected_items_count:
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
        self.children_selected = self.all_children
        self._toggle_all_selection(True)

    @log
    def unselect_all(self):
        self.children_selected = []
        self._toggle_all_selection(False)

    @log
    def update_cover_from_selection(self, new_cover):
        """Update cover of the selected album

        :param str new_cover: cover path
        """
        if (not new_cover
                or len(self.children_selected) != 1):
            return

        child = self.children_selected[0]
        child_index = child.get_index()
        album = child.props.media
        tmp_media = Grl.Media.audio_new()
        tmp_media.set_album(utils.get_album_title(album))
        tmp_media.set_artist(utils.get_artist_name(album))
        tmp_media.set_thumbnail(GLib.filename_to_uri(new_cover, None))

        art_loader = ArtLoader()
        art_loader.connect(
            'failed', self._on_loading_new_cover_failed, new_cover)
        art_loader.connect(
            'succeeded', self._on_loading_new_cover_succeeded,
            (new_cover, child_index))
        art_loader.load(tmp_media)

    @log
    def _on_loading_new_cover_succeeded(self, klass, data):
        new_cover, child_index = data
        child = self._view.get_child_at_index(child_index)
        media = child.props.media
        media.set_thumbnail(GLib.filename_to_uri(new_cover, None))
        child.props.media = media

    @log
    def _on_loading_new_cover_failed(self, klass, cover):
        logger.warning(
            "Unable to load new cover from file {}".format(cover))
