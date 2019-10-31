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

from gnomemusic.widgets.songwidget import SongWidget


@Gtk.Template(resource_path='/org/gnome/Music/ui/DiscBox.ui')
class DiscBox(Gtk.ListBoxRow):
    """A widget which compromises one disc

    DiscBox contains a disc label for the disc number on top
    with a DiscSongsFlowBox beneath.
    """
    __gtype_name__ = 'DiscBox'

    _disc_label = Gtk.Template.Child()
    _list_box = Gtk.Template.Child()

    __gsignals__ = {
        'song-activated': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.Widget,))
    }

    selection_mode = GObject.Property(type=bool, default=False)
    show_disc_label = GObject.Property(type=bool, default=False)

    def __init__(self, coredisc):
        """Initialize

        :param CoreDisc coredisc: The CoreDisc object to use
        """
        super().__init__()

        self._model = coredisc.props.model

        disc_nr = coredisc.props.disc_nr
        self._disc_label.props.label = _("Disc {}").format(disc_nr)

        self.bind_property(
            'show-disc-label', self._disc_label, 'visible',
            GObject.BindingFlags.SYNC_CREATE)

        self._list_box.bind_model(self._model, self._create_widget)

    def select_all(self):
        """Select all songs"""
        def child_select_all(child):
            song_widget = child.get_child()
            song_widget.props.coresong.props.selected = True

        self._list_box.foreach(child_select_all)

    def deselect_all(self):
        """Deselect all songs"""
        def child_deselect_all(child):
            song_widget = child.get_child()
            song_widget.props.coresong.props.selected = False

        self._list_box.foreach(child_deselect_all)

    def _create_widget(self, coresong):
        song_widget = SongWidget(coresong)

        self.bind_property(
            "selection-mode", song_widget, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        # song_widget.connect('button-release-event', self._song_activated)

        row = Gtk.ListBoxRow()
        row.props.activatable = False
        row.props.selectable = False
        row.add(song_widget)

        return row

    def _song_activated(self, widget, event):
        if widget.props.select_click:
            widget.props.select_click = False
            return

        mod_mask = Gtk.accelerator_get_default_mod_mask()
        if ((event.get_state() & mod_mask) == Gdk.ModifierType.CONTROL_MASK
                and not self.props.selection_mode):
            self.props.selection_mode = True
            widget.props.select_click = True
            widget.props.coresong.props.selected = True
            return

        (_, button) = event.get_button()
        if (button == Gdk.BUTTON_PRIMARY
                and not self.props.selection_mode):
            self.emit('song-activated', widget)

        if self.props.selection_mode:
            widget.props.select_click = True
            selection_state = widget.props.coresong.props.selected
            widget.props.coresong.props.selected = not selection_state

        return True


class DiscListBox(Gtk.ListBox):
    """A ListBox widget containing all discs of a particular
    album
    """
    __gtype_name__ = 'DiscListBox'

    selection_mode = GObject.Property(type=bool, default=False)

    def __init__(self):
        """Initialize"""
        super().__init__()

        self.props.valign = Gtk.Align.START
        self.get_style_context().add_class("disc-list-box")

    def select_all(self):
        """Select all songs"""
        def child_select_all(child):
            child.select_all()

        self.foreach(child_select_all)

    def deselect_all(self):
        """Deselect all songs"""
        def child_deselect_all(child):
            child.deselect_all()

        self.foreach(child_deselect_all)
