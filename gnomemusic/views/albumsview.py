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
from gi.repository import GLib, GObject, Gtk, Gdk

from gnomemusic import log
from gnomemusic.albumartcache import Art
from gnomemusic.grilo import grilo
from gnomemusic.toolbar import ToolbarState
from gnomemusic.views.baseview import BaseView
from gnomemusic.widgets.albumwidget import AlbumWidget
from gnomemusic.widgets.coverstack import CoverStack
import gnomemusic.utils as utils


class AlbumsView(BaseView):

    def __repr__(self):
        return '<AlbumsView>'

    @log
    def __init__(self, window, player):
        super().__init__('albums', _("Albums"), window, None)
        self._album_widget = AlbumWidget(player, self)
        self.player = player
        self.add(self._album_widget)
        self.albums_selected = []
        self.all_items = []
        self.items_selected = []
        self.items_selected_callback = None
        self._add_list_renderers()

    @log
    def _on_changes_pending(self, data=None):
        if (self._init and not self._header_bar._selectionMode):
            self._offset = 0
            self._init = True
            GLib.idle_add(self.populate)
            grilo.changes_pending['Albums'] = False

    @log
    def _on_selection_mode_changed(self, widget, data=None):
        if (not self._header_bar._selectionMode
                and grilo.changes_pending['Albums']):
            self._on_changes_pending()

    @log
    def _setup_view(self, view_type):
        self._view = Gtk.FlowBox(
            homogeneous=True, hexpand=True, halign=Gtk.Align.FILL,
            valign=Gtk.Align.START, selection_mode=Gtk.SelectionMode.NONE,
            margin=18, row_spacing=12, column_spacing=6,
            min_children_per_line=1, max_children_per_line=25)

        self._view.connect('child-activated', self._on_child_activated)

        scrolledwin = Gtk.ScrolledWindow()
        scrolledwin.add(self._view)
        scrolledwin.show()

        self._box.add(scrolledwin)

    @log
    def _back_button_clicked(self, widget, data=None):
        self._header_bar.reset_header_title()
        self.set_visible_child(self._grid)

    @log
    def _on_child_activated(self, widget, child, user_data=None):
        item = child.media_item

        if self._star_handler.star_renderer_click:
            self._star_handler.star_renderer_click = False
            return

        # Toggle the selection when in selection mode
        if self.selection_mode:
            child.check.set_active(not child.check.get_active())
            return

        title = utils.get_media_title(item)
        self._escaped_title = title
        self._artist = utils.get_artist_name(item)

        self._album_widget.update(
            self._artist, title, item, self._header_bar,
            self._selection_toolbar)

        self._header_bar.set_state(ToolbarState.CHILD_VIEW)
        self._header_bar.header_bar.set_title(self._escaped_title)
        self._header_bar.header_bar.sub_title = self._artist
        self.set_visible_child(self._album_widget)

    @log
    def update_title(self):
        self._header_bar.header_bar.set_title(self._escaped_title)
        self._header_bar.header_bar.sub_title = self._artist

    @log
    def populate(self):
        self._window.push_loading_notification()
        grilo.populate_albums(self._offset, self._add_item)

    @log
    def get_selected_songs(self, callback):
        # FIXME: we call into private objects with full knowledge of
        # what is there
        if self._header_bar._state == ToolbarState.CHILD_VIEW:
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
        elif remaining == 0:
                self._window.pop_loading_notification()
                self._view.show()

    def _create_album_item(self, item):
        artist = utils.get_artist_name(item)
        title = utils.get_media_title(item)

        builder = Gtk.Builder.new_from_resource(
            '/org/gnome/Music/AlbumCover.ui')

        child = Gtk.FlowBoxChild()
        child.stack = builder.get_object('stack')
        child.check = builder.get_object('check')
        child.title = builder.get_object('title')
        child.subtitle = builder.get_object('subtitle')
        child.events = builder.get_object('events')
        child.media_item = item

        child.title.set_label(title)
        child.subtitle.set_label(artist)

        child.events.add_events(Gdk.EventMask.TOUCH_MASK)

        child.events.connect('button-release-event',
                             self._on_album_event_triggered,
                             child)

        child.check_handler_id = child.check.connect('notify::active',
                                                     self._on_child_toggled,
                                                     child)

        child.check.bind_property('visible', self, 'selection_mode',
                                  GObject.BindingFlags.BIDIRECTIONAL)

        child.add(builder.get_object('main_box'))
        child.show()

        cover_stack = CoverStack(child.stack, Art.Size.MEDIUM)
        cover_stack.update(item)

        return child

    @log
    def _on_album_event_triggered(self, evbox, event, child):
        if event.button is 3:
            self._on_selection_mode_request()
            if self.selection_mode:
                child.check.set_active(True)

    @log
    def _on_child_toggled(self, check, pspec, child):
        if (check.get_active()
                and child.media_item not in self.albums_selected):
            self.albums_selected.append(child.media_item)
        elif (not check.get_active()
                and child.media_item in self.albums_selected):
            self.albums_selected.remove(child.media_item)

        self.update_header_from_selection(len(self.albums_selected))

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
            GObject.signal_handler_block(child.check, child.check_handler_id)

            # Set the checkbutton state without emiting the signal
            child.check.set_active(selected)

            GObject.signal_handler_unblock(child.check, child.check_handler_id)

        self.update_header_from_selection(len(self.albums_selected))

    @log
    def select_all(self):
        self.albums_selected = list(self.all_items)
        self._toggle_all_selection(True)

    @log
    def unselect_all(self):
        self.albums_selected = []
        self._toggle_all_selection(False)
