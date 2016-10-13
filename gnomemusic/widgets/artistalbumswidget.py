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
from gi.repository import GLib, GObject, Gtk

from gnomemusic import log
from gnomemusic.widgets.artistalbumwidget import ArtistAlbumWidget
import gnomemusic.utils as utils

logger = logging.getLogger(__name__)


class ArtistAlbumsWidget(Gtk.Box):

    def __repr__(self):
        return '<ArtistAlbumsWidget>'

    @log
    def __init__(self, artist, albums, player,
                 header_bar, selection_toolbar, window, selectionModeAllowed=False):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.player = player
        self.artist = artist
        self.albums = albums
        self.window = window
        self.selectionMode = False
        self.selectionModeAllowed = selectionModeAllowed
        self.selection_toolbar = selection_toolbar
        self.header_bar = header_bar
        self.ui = Gtk.Builder()
        self.ui.add_from_resource('/org/gnome/Music/ArtistAlbumsWidget.ui')
        self.set_border_width(0)
        self.ui.get_object('artist').set_label(self.artist)
        self.widgets = []

        self._create_model()

        self.row_changed_source_id = None

        self._hbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._albumBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                 spacing=48)
        self._scrolledWindow = Gtk.ScrolledWindow()
        self._scrolledWindow.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC)
        self._scrolledWindow.add(self._hbox)
        self._hbox.pack_start(self.ui.get_object('ArtistAlbumsWidget'),
                              False, False, 0)
        self._hbox.pack_start(self._albumBox, False, False, 16)
        self._coverSizeGroup = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)
        self._songsGridSizeGroup = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)
        self.pack_start(self._scrolledWindow, True, True, 0)

        self.hide()
        self.window._init_loading_notification()

        for album in albums:
            is_last_album = False
            if album == albums[-1]:
                is_last_album = True
            self.add_album(album, is_last_album)

        self.player.connect('playlist-item-changed', self.update_model)

    @log
    def _create_model(self):
        """Create the ListStore model for this widget."""
        self._model = Gtk.ListStore(
            GObject.TYPE_STRING,  # title
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,
            GObject.TYPE_STRING,    # placeholder
            GObject.TYPE_OBJECT,  # song object
            GObject.TYPE_BOOLEAN,  # item selected
            GObject.TYPE_STRING,
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT,  # icon shown
            GObject.TYPE_BOOLEAN,
            GObject.TYPE_INT
        )

    def _on_last_album_displayed(self, data=None):
        self.window.notification.dismiss()
        self.show_all()

    @log
    def add_album(self, album, is_last_album=False):
        self.window.notification.set_timeout(0)
        widget = ArtistAlbumWidget(
            album, self.player, self._model,
            self.header_bar, self.selectionModeAllowed,
            self._songsGridSizeGroup, self.header_bar
        )
        self._coverSizeGroup.add_widget(widget.cover)

        self._albumBox.pack_start(widget, False, False, 0)
        self.widgets.append(widget)

        if is_last_album:
            widget.connect('tracks-loaded', self._on_last_album_displayed)

    @log
    def update_model(self, player, playlist, currentIter):
        # this is not our playlist, return
        if playlist != self._model:
            # TODO, only clean once, but that can wait util we have clean
            # the code a bit, and until the playlist refactoring.
            # the overhead is acceptable for now
            self.clean_model()
            return False

        currentSong = playlist.get_value(currentIter, 5)
        song_passed = False
        itr = playlist.get_iter_first()

        while itr:
            song = playlist.get_value(itr, 5)
            song_widget = song.song_widget

            if not song_widget.can_be_played:
                itr = playlist.iter_next(itr)
                continue

            escaped_title = GLib.markup_escape_text(utils.get_media_title(song))
            if (song == currentSong):
                song_widget.now_playing_sign.show()
                song_widget.title.set_markup('<b>%s</b>' % escaped_title)
                song_passed = True
            elif (song_passed):
                song_widget.now_playing_sign.hide()
                song_widget.title.set_markup('<span>%s</span>' % escaped_title)
            else:
                song_widget.now_playing_sign.hide()
                song_widget.title.set_markup(
                    '<span color=\'grey\'>%s</span>' % escaped_title
                )
            itr = playlist.iter_next(itr)
        return False

    @log
    def clean_model(self):
        itr = self._model.get_iter_first()
        while itr:
            song = self._model.get_value(itr, 5)
            song_widget = song.song_widget
            escaped_title = GLib.markup_escape_text(utils.get_media_title(song))
            if song_widget.can_be_played:
                song_widget.now_playing_sign.hide()
            song_widget.title.set_markup('<span>%s</span>' % escaped_title)
            itr = self._model.iter_next(itr)
        return False

    @log
    def set_selection_mode(self, selectionMode):
        if self.selectionMode == selectionMode:
            return
        self.selectionMode = selectionMode
        try:
            if self.row_changed_source_id:
                self._model.disconnect(self.row_changed_source_id)
            self.row_changed_source_id = self._model.connect(
                'row-changed',
                self._model_row_changed)
        except Exception as e:
            logger.warning("Exception while tracking row-changed: %s", e)

        for widget in self.widgets:
            widget.set_selection_mode(selectionMode)

    @log
    def _model_row_changed(self, model, path, _iter):
        if not self.selectionMode:
            return
        selected_items = 0
        for row in model:
            if row[6]:
                selected_items += 1
        self.selection_toolbar\
            ._add_to_playlist_button.set_sensitive(selected_items > 0)
        if selected_items > 0:
            self.header_bar._selection_menu_label.set_text(
                ngettext("Selected %d item", "Selected %d items", selected_items) % selected_items)
        else:
            self.header_bar._selection_menu_label.set_text(_("Click on items to select them"))

    @log
    def select_all(self):
        for widget in self.widgets:
            widget._disc_listbox.select_all()

    @log
    def select_none(self):
        for widget in self.widgets:
            widget._disc_listbox.select_none()
