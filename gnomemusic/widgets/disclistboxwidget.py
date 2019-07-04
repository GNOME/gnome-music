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


class DiscSongsFlowBox(Gtk.ListBox):
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
        super().__init__(selection_mode=Gtk.SelectionMode.NONE)

        self._columns = 1
        self.props.columns = columns

        self.get_style_context().add_class('discsongsflowbox')

    @GObject.Property(type=int, minimum=1, default=1)
    def columns(self):
        """Number of columns for the song list

        :returns: The number of columns
        :rtype: int
        """
        return self._columns

    @columns.setter
    def columns(self, columns):
        """Set the number of columns to use

        :param int columns: The number of columns the widget uses
        """
        self._columns = columns

        children_n = max(len(self.get_children()), 1)

        if children_n % self._columns == 0:
            max_per_line = children_n / self._columns
        else:
            max_per_line = int(children_n / self._columns) + 1

        # self.props.max_children_per_line = max_per_line
        # self.props.min_children_per_line = max_per_line


@Gtk.Template(resource_path='/org/gnome/Music/ui/DiscBox.ui')
class DiscBox(Gtk.Box):
    """A widget which compromises one disc

    DiscBox contains a disc label for the disc number on top
    with a DiscSongsFlowBox beneath.
    """
    __gtype_name__ = 'DiscBox'

    _disc_label = Gtk.Template.Child()
    #_disc_songs_flowbox = Gtk.Template.Child()
    _list_box = Gtk.Template.Child()

    __gsignals__ = {
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'song-activated': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.Widget,))
    }

    columns = GObject.Property(type=int, minimum=1, default=1)
    selection_mode = GObject.Property(type=bool, default=False)
    selection_mode_allowed = GObject.Property(type=bool, default=True)
    show_disc_label = GObject.Property(type=bool, default=False)
    show_durations = GObject.Property(type=bool, default=False)
    show_favorites = GObject.Property(type=bool, default=False)
    show_song_numbers = GObject.Property(type=bool, default=False)

    def __repr__(self):
        return '<DiscBox>'

    @log
    def __init__(self, model=None, listmodel=None):
        """Initialize

        :param model: The TreeStore to use
        """
        super().__init__()

        self._model = model
        if self._model is not None:
            self._model.connect('row-changed', self._model_row_changed)

        # self.bind_property(
        #     'columns', self._list_box, 'columns',
        #     GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            'show-disc-label', self._disc_label, 'visible',
            GObject.BindingFlags.SYNC_CREATE)

        self._selection_mode_allowed = True
        self._selected_items = []
        self._songs = []

        if listmodel is not None:
            self._listmodel = listmodel
            self._list_box.bind_model(
                self._listmodel, self._create_widget)

    @log
    def set_disc_number(self, disc_number):
        """Set the dics number to display

        :param int disc_number: Disc number to display
        """
        self._disc_label.props.label = _("Disc {}").format(disc_number)
        self._disc_label.props.visible = True

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

    def _create_widget(self, song):
        song_widget = SongWidget(song.props.media)
        self._songs.append(song_widget)

        song.bind_property(
            "favorite", song_widget, "favorite",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        song.bind_property(
            "selected", song_widget, "selected",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        song.bind_property(
            "state", song_widget, "state",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        song_widget.connect('button-release-event', self._song_activated)

        song_widget.show_all()

        return song_widget

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

        self.bind_property(
            'selection-mode', song_widget, 'selection-mode',
            GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            'show-durations', song_widget, 'show-duration',
            GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            'show-favorites', song_widget, 'show-favorite',
            GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            'show-song-numbers', song_widget, 'show-song-number',
            GObject.BindingFlags.SYNC_CREATE)

        return song_widget

    @log
    def _on_selection_changed(self, widget):
        self.emit('selection-changed')

        return True

    @log
    def _toggle_widget_selection(self, child):
        song_widget = child.get_child()
        song_widget.props.selection_mode = self.props.selection_mode

    @log
    def _song_activated(self, widget, event):
        mod_mask = Gtk.accelerator_get_default_mod_mask()
        if ((event.get_state() & mod_mask) == Gdk.ModifierType.CONTROL_MASK
                and not self.props.selection_mode
                and self.props.selection_mode_allowed):
            self.props.selection_mode = True

        (_, button) = event.get_button()
        if (button == Gdk.BUTTON_PRIMARY
                and not self.props.selection_mode):
            self.emit('song-activated', widget)

        if self.props.selection_mode:
            itr = widget.itr
            self._model[itr][6] = not self._model[itr][6]

        return True

    @log
    def _model_row_changed(self, model, path, itr):
        if (not self.props.selection_mode
                or not model[itr][5]):
            return

        song_widget = model[itr][5].song_widget
        selected = model[itr][6]
        if selected != song_widget.props.selected:
            song_widget.props.selected = selected

        return True


class DiscListBox(Gtk.ListBox):
    """A ListBox widget containing all discs of a particular
    album
    """
    __gtype_name__ = 'DiscListBox'

    __gsignals__ = {
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    selection_mode_allowed = GObject.Property(type=bool, default=False)

    def __repr__(self):
        return '<DiscListBox>'

    @log
    def __init__(self):
        """Initialize"""
        super().__init__() # orientation=Gtk.Orientation.VERTICAL)

        self._selection_mode = False
        self._selected_items = []

    @log
    def add(self, widget):
        """Insert a DiscBox widget"""
        super().add(widget)
        widget.connect('selection-changed', self._on_selection_changed)

        self.bind_property(
            'selection-mode', widget, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            'selection-mode-allowed', widget, 'selection-mode-allowed',
            GObject.BindingFlags.SYNC_CREATE)

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

    @GObject.Property(type=bool, default=False)
    def selection_mode(self):
        """selection mode getter

        :returns: If selection mode is active
        :rtype: bool
        """
        return self._selection_mode

    @selection_mode.setter
    def selection_mode(self, value):
        """selection-mode setter

        :param bool value: Activate selection mode
        """
        if not self.props.selection_mode_allowed:
            return

        self._selection_mode = value
