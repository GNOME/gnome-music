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
from gi.repository import Gdk, GObject, Gtk

from gnomemusic import log
from gnomemusic.widgets.songwidget import SongWidget
import gnomemusic.utils as utils


class DiscSongsFlowBox(Gtk.FlowBox):
    """FlowBox containing the songs on one disc

    DiscSongsFlowBox allows setting the number of columns to
    use.
    """
    __gtype_name__ = 'DiscSongsFlowBox'

    def __repr__(self):
        return '<DiscSongsFlowBox>'

    @log
    def __init__(self, columns=1):
        """Initialize

        :param int columns: The number of columns the widget uses
        """
        super().__init__()
        super().set_selection_mode(Gtk.SelectionMode.NONE)

        self._columns = columns
        self.get_style_context().add_class('discsongsflowbox')

    @log
    def set_columns(self, columns):
        """Set the number of columns to use

        :param int columns: The number of columns the widget uses
        """
        self._columns = columns

        children_n = len(self.get_children())

        if children_n % self._columns == 0:
            max_per_line = children_n / self._columns
        else:
            max_per_line = int(children_n / self._columns) + 1

        self.set_max_children_per_line(max_per_line)
        self.set_min_children_per_line(max_per_line)


class DiscBox(Gtk.Box):
    """A widget which compromises one disc

    DiscBox contains a disc label for the disc number on top
    with a DiscSongsFlowBox beneath.
    """
    __gtype_name__ = 'DiscBox'

    __gsignals__ = {
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'selection-toggle': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'song-activated': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.Widget,))

    }

    def __repr__(self):
        return '<DiscBox>'

    @log
    def __init__(self, model=None):
        """Initialize

        :param model: The TreeStore to use
        """
        super().__init__()

        self._model = model
        self._model.connect('row-changed', self._model_row_changed)

        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Music/ArtistAlbumWidget.ui')

        self._label = builder.get_object('disclabel')
        self._label.set_no_show_all(True)
        self._disc_songs_flowbox = builder.get_object('discsongsflowbox')

        self._selection_mode = False
        self._selection_mode_allowed = True
        self._selected_items = []
        self._songs = []

        self.pack_start(builder.get_object('disc'), True, True, 0)

    @log
    def set_columns(self, columns):
        """Set the number of columns used by the songs list

        :param int columns: Number of columns to display
        """
        self._disc_songs_flowbox.set_columns(columns)

    @log
    def set_disc_number(self, disc_number):
        """Set the dics number to display

        :param int disc_number: Disc number to display
        """
        self._label.set_label(_("Disc {}").format(disc_number))
        self._label.set_visible(True)

    @log
    def show_disc_label(self, show_header):
        """Wheter to show the disc number label

        :param bool show_header: Display the disc number label
        """
        self._label.set_visible(False)
        self._label.hide()

    @log
    def show_duration(self, show_duration):
        """Wheter to show the song durations

        :param bool show_duration: Display the song durations
        """
        def child_show_duration(child):
            child.get_child().show_duration = show_duration

        self._disc_songs_flowbox.foreach(child_show_duration)

    @log
    def show_favorites(self, show_favorites):
        """Where to show the favorite switches

        :param bool show_favorites: Display the favorite
        switches
        """
        def child_show_favorites(child):
            child.get_child().show_favorite = show_favorites

        self._disc_songs_flowbox.foreach(child_show_favorites)

    @log
    def show_song_numbers(self, show_song_number):
        """Whether to show the song numbers

        :param bool show_song_number: Display the song number
        """
        def child_show_song_number(child):
            child.get_child().show_song_number = show_song_number

        self._disc_songs_flowbox.foreach(child_show_song_number)

    @log
    def set_songs(self, songs):
        """Songs to display

        :param list songs: A list of Grilo media items to
        add to the widget
        """
        for song in songs:
            song_widget = self._create_song_widget(song)
            self._disc_songs_flowbox.insert(song_widget, -1)
            song.song_widget = song_widget

    @log
    def set_selection_mode(self, selection_mode):
        """Set selection mode

        :param bool selection_mode: Allow selection mode
        """
        self._selection_mode = selection_mode
        self._disc_songs_flowbox.foreach(self._toggle_widget_selection)

    @log
    def get_selected_items(self):
        """Return all selected items

        :returns: The selected items:
        :rtype: A list if Grilo media items
        """
        self._selected_items = []
        self._disc_songs_flowbox.foreach(self._get_selected)

        return self._selected_items

    @log
    def _get_selected(self, child):
        song_widget = child.get_child()

        if song_widget.selected:
            itr = song_widget.itr
            self._selected_items.append(self._model[itr][5])

    # FIXME: select all/none slow probably b/c of the row changes
    # invocations, maybe workaround?
    @log
    def select_all(self):
        """Select all songs"""
        def child_select_all(child):
            song_widget = child.get_child()
            self._model[song_widget.itr][6] = True

        self._disc_songs_flowbox.foreach(child_select_all)

    @log
    def select_none(self):
        """Deselect all songs"""
        def child_select_none(child):
            song_widget = child.get_child()
            self._model[song_widget.itr][6] = False

        self._disc_songs_flowbox.foreach(child_select_none)

    @log
    def _create_song_widget(self, song):
        """Helper function to create a song widget for a
        single song

        :param song: A Grilo media item
        :returns: A complete song widget
        :rtype: Gtk.EventBox
        """
        song_widget = SongWidget(song)
        self._songs.append(song_widget)

        title = utils.get_media_title(song)

        itr = self._model.append(None)

        self._model[itr][0, 1, 2, 5, 6] = [title, '', '', song, False]

        song_widget.itr = itr
        song_widget.model = self._model
        song_widget.connect('button-release-event', self._song_activated)
        song_widget.connect('selection-changed', self._on_selection_changed)

        return song_widget

    @log
    def _on_selection_changed(self, widget):
        self.emit('selection-changed')

        return True

    @log
    def _toggle_widget_selection(self, child):
        song_widget = child.get_child()
        song_widget.selection_mode = self._selection_mode

    @log
    def _song_activated(self, widget, event):
        # FIXME: don't think keys work correctly, if they did ever
        # even.
        if (not event.button == Gdk.BUTTON_SECONDARY
                or (event.button == Gdk.BUTTON_PRIMARY
                    and event.state & Gdk.ModifierType.CONTROL_MASK)):
            self.emit('song-activated', widget)
            if self._selection_mode:
                itr = widget.itr
                self._model[itr][6] = not self._model[itr][6]
        else:
            self.emit('selection-toggle')
            if self._selection_mode:
                itr = widget.itr
                self._model[itr][6] = True

        return True

    @log
    def _model_row_changed(self, model, path, itr):
        if (not self._selection_mode
                or not model[itr][5]):
            return

        song_widget = model[itr][5].song_widget
        selected = model[itr][6]
        if selected != song_widget.selected:
            song_widget.selected = selected

        return True


class DiscListBox(Gtk.Box):
    """A ListBox widget containing all discs of a particular
    album
    """
    __gtype_name__ = 'DiscListBox'

    __gsignals__ = {
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __repr__(self):
        return '<DiscListBox>'

    @log
    def __init__(self):
        """Initialize"""
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self._selection_mode = False
        self._selection_mode_allowed = False
        self._selected_items = []

    @log
    def add(self, widget):
        """Insert a DiscBox widget"""
        super().add(widget)
        widget.connect('selection-changed', self._on_selection_changed)

    @log
    def _on_selection_changed(self, widget):
        self.emit('selection-changed')

    @log
    def get_selected_items(self):
        """Returns all selected items for all discs

        :returns: All selected items
        :rtype: A list if Grilo media items
        """
        self._selected_items = []

        def get_child_selected_items(child):
            self._selected_items += child.get_selected_items()

        self.foreach(get_child_selected_items)

        return self._selected_items

    @log
    def select_all(self):
        """Select all songs"""
        def child_select_all(child):
            child.select_all()

        self.foreach(child_select_all)

    @log
    def select_none(self):
        """Deselect all songs"""
        def child_select_none(child):
            child.select_none()

        self.foreach(child_select_none)

    @log
    def set_selection_mode(self, selection_mode):
        """Set selection mode

        :param bool selection_mode: Allow selection mode
        """
        if not self._selection_mode_allowed:
            return

        self._selection_mode = selection_mode

        def set_child_selection_mode(child):
            child.set_selection_mode(self._selection_mode)

        self.foreach(set_child_selection_mode)

    @log
    def set_selection_mode_allowed(self, allowed):
        """Set if selection mode is allowed

        :param bool allowed: Allow selection mode
        """
        self._selection_mode_allowed = allowed
