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

from gettext import gettext as _, ngettext
from gi.repository import GdkPixbuf, GLib, GObject, Gtk

from gnomemusic import log
from gnomemusic.utils import Model
from gnomemusic.widgets.artistalbumwidget import ArtistAlbumWidget
import gnomemusic.utils as utils

logger = logging.getLogger(__name__)


class ArtistAlbumsWidget(Gtk.Box):
    """Widget containing all albums by an artist

    A vertical list of ArtistAlbumWidget, containing all the albums
    by one artist. Contains the model for all the song widgets of
    the album(s).
    """

    def __repr__(self):
        return '<ArtistAlbumsWidget>'

    @log
    def __init__(self, artist, albums, player, header_bar, selection_toolbar,
                 window, selection_mode_allowed=False):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._player = player
        self.artist = artist
        self._window = window
        self._selection_mode = False
        self._selection_mode_allowed = selection_mode_allowed
        self._selection_toolbar = selection_toolbar
        self._header_bar = header_bar

        ui = Gtk.Builder()
        ui.add_from_resource('/org/gnome/Music/ArtistAlbumsWidget.ui')
        ui.get_object('artist').set_label(self.artist)

        self._widgets = []

        self._create_model()

        self._row_changed_source_id = None

        hbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox.pack_start(ui.get_object('ArtistAlbumsWidget'), False, False, 0)
        self._album_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                  spacing=48)
        hbox.pack_start(self._album_box, False, False, 16)

        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_policy(Gtk.PolicyType.NEVER,
                                         Gtk.PolicyType.AUTOMATIC)
        self._scrolled_window.add(hbox)
        self.pack_start(self._scrolled_window, True, True, 0)

        self._cover_size_group = Gtk.SizeGroup.new(
            Gtk.SizeGroupMode.HORIZONTAL)
        self._songs_grid_size_group = Gtk.SizeGroup.new(
            Gtk.SizeGroupMode.HORIZONTAL)

        self._window.notifications_popup.push_loading()

        for album in albums:
            is_last_album = False
            if album == albums[-1]:
                is_last_album = True
            self._add_album(album, is_last_album)

        self._player.connect('playlist-item-changed', self._update_model)

    @log
    def _create_model(self):
        """Create the ListStore model for this widget."""
        self._model = Gtk.ListStore(
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,   # title
            GObject.TYPE_STRING,
            GdkPixbuf.Pixbuf,      # placeholder
            GObject.TYPE_OBJECT,   # song object
            GObject.TYPE_BOOLEAN,  # item selected
            GObject.TYPE_INT,
            GObject.TYPE_STRING,   # rendering icon
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT
        )

    @log
    def _on_last_album_displayed(self, data=None):
        self._window.notifications_popup.pop_loading()
        self.show_all()

    @log
    def _add_album(self, album, is_last_album=False):
        widget = ArtistAlbumWidget(album, self._player, self._model,
                                   self._header_bar,
                                   self._selection_mode_allowed,
                                   self._songs_grid_size_group,
                                   self._cover_size_group)
        self._cover_size_group.add_widget(widget.cover_stack._stack)

        self._album_box.pack_start(widget, False, False, 0)
        self._widgets.append(widget)

        if is_last_album:
            widget.connect('songs-loaded', self._on_last_album_displayed)

    @log
    def _update_model(self, player, playlist, current_iter):
        # this is not our playlist, return
        if playlist != self._model:
            # TODO, only clean once, but that can wait util we have clean
            # the code a bit, and until the playlist refactoring.
            # the overhead is acceptable for now
            self._clean_model()
            return False

        current_song = playlist[current_iter][Model.ITEM]
        song_passed = False
        itr = playlist.get_iter_first()

        while itr:
            song = playlist[itr][Model.ITEM]
            song_widget = song.song_widget

            if not song_widget.can_be_played:
                itr = playlist.iter_next(itr)
                continue

            escaped_title = GLib.markup_escape_text(
                utils.get_media_title(song))

            if (song == current_song):
                song_widget.now_playing_sign.show()
                song_widget.title.set_markup('<b>%s</b>' % escaped_title)
                song_passed = True
            elif (song_passed):
                song_widget.now_playing_sign.hide()
                song_widget.title.set_markup('<span>%s</span>' % escaped_title)
            else:
                song_widget.now_playing_sign.hide()
                song_widget.title.set_markup(
                    '<span color=\'grey\'>%s</span>' % escaped_title)
            itr = playlist.iter_next(itr)

        return False

    @log
    def _clean_model(self):
        itr = self._model.get_iter_first()

        while itr:
            song = self._model[itr][Model.ITEM]
            song_widget = song.song_widget
            escaped_title = GLib.markup_escape_text(
                utils.get_media_title(song))
            if song_widget.can_be_played:
                song_widget.now_playing_sign.hide()
            song_widget.title.set_markup('<span>%s</span>' % escaped_title)
            itr = self._model.iter_next(itr)

        return False

    @log
    def set_selection_mode(self, selection_mode):
        """Set selection mode for the widget

        :param bool selection_mode: Allow selection mode
        """
        if self._selection_mode == selection_mode:
            return

        self._selection_mode = selection_mode

        try:
            if self._row_changed_source_id:
                self._model.disconnect(self._row_changed_source_id)
            self._row_changed_source_id = self._model.connect(
                'row-changed', self._model_row_changed)
        except Exception as e:
            logger.warning("Exception while tracking row-changed: %s", e)

        for widget in self._widgets:
            widget.set_selection_mode(selection_mode)

    @log
    def _model_row_changed(self, model, path, itr):
        if not self._selection_mode:
            return

        selected_items = 0
        for row in model:
            if row[Model.SELECTED]:
                selected_items += 1

        add_button = self._selection_toolbar._add_to_playlist_button
        add_button.set_sensitive(selected_items > 0)

        menu_label = self._header_bar._selection_menu_label
        if selected_items > 0:
            menu_label.set_text(ngettext("Selected %d item",
                                         "Selected %d items",
                                         selected_items) % selected_items)
        else:
            menu_label.set_text(_("Click on items to select them"))

    @log
    def select_all(self):
        """Select all items"""
        for widget in self._widgets:
            widget._disc_listbox.select_all()

    @log
    def select_none(self):
        """Deselect all items"""
        for widget in self._widgets:
            widget._disc_listbox.select_none()
