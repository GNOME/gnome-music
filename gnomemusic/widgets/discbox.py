# Copyright (c) 2021 The GNOME Music Developers
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

from __future__ import annotations
from gettext import gettext as _
import typing

from gi.repository import Gdk, Gio, GObject, Gtk

from gnomemusic.widgets.songwidget import SongWidget
from gnomemusic.widgets.songwidgetmenu import SongWidgetMenu
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.corealbum import CoreAlbum
    from gnomemusic.coredisc import CoreDisc


@Gtk.Template(resource_path='/org/gnome/Music/ui/DiscBox.ui')
class DiscBox(Gtk.ListBoxRow):
    """A widget which compromises one disc

    DiscBox contains a disc label for the disc number on top
    with a GtkListBox beneath.
    """
    __gtype_name__ = 'DiscBox'

    _disc_label = Gtk.Template.Child()
    _list_box = Gtk.Template.Child()
    _list_box_ctrlr = Gtk.Template.Child()

    __gsignals__ = {
        'song-activated': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.Widget,))
    }

    selection_mode = GObject.Property(type=bool, default=False)
    show_disc_label = GObject.Property(type=bool, default=False)

    def __init__(
            self, application: Application, corealbum: CoreAlbum,
            coredisc: CoreDisc) -> None:
        """Initialize

        :param Application coredisc: The Application object
        :param CoreAlbum corealbum: The corealbum of the coredisc
        :param CoreDisc coredisc: The CoreDisc object to use
        """
        super().__init__()

        self._application = application
        self._corealbum = corealbum
        self._coredisc = coredisc
        self._model: Gio.ListModel = coredisc.props.model

        disc_nr: int = coredisc.props.disc_nr
        self._disc_label.props.label = _("Disc {}").format(disc_nr)

        self.bind_property(
            'show-disc-label', self._disc_label, 'visible',
            GObject.BindingFlags.SYNC_CREATE)

        self._list_box.bind_model(self._model, self._create_widget)

    def select_all(self):
        """Select all songs"""
        for coresong in self._model:
            coresong.props.selected = True

    def deselect_all(self):
        """Deselect all songs"""
        for coresong in self._model:
            coresong.props.selected = False

    def _create_widget(self, coresong):
        song_widget = SongWidget(coresong)
        song_widget.props.menu = SongWidgetMenu(
            self._application, song_widget, self._corealbum)

        self._coredisc.bind_property(
            "selected", coresong, "selected", GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "selection-mode", song_widget, "selection-mode",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        return song_widget

    @Gtk.Template.Callback()
    def _song_activated(
            self, list_box: Gtk.ListBox, song_widget: SongWidget) -> bool:
        if song_widget.props.select_click:
            song_widget.props.select_click = False
            return True

        event = Gtk.get_current_event()
        (_, state) = event.get_state()
        mod_mask = Gtk.accelerator_get_default_mod_mask()
        if ((state & mod_mask) == Gdk.ModifierType.CONTROL_MASK
                and not self.props.selection_mode):
            self.props.selection_mode = True
            song_widget.props.select_click = True
            song_widget.props.coresong.props.selected = True
            return True

        (_, button) = event.get_button()
        if (button == Gdk.BUTTON_PRIMARY
                and not self.props.selection_mode):
            self.emit("song-activated", song_widget)

        if self.props.selection_mode:
            song_widget.props.select_click = True
            selection_state = song_widget.props.coresong.props.selected
            song_widget.props.coresong.props.selected = not selection_state

        return True

    @Gtk.Template.Callback()
    def _list_box_right_click(
            self, gesture: Gtk.GestureMultiPress, n_press: int, x: int,
            y: int) -> None:
        song_widget = self._list_box.get_row_at_y(y)

        _, y0 = song_widget.translate_coordinates(self._list_box, 0, 0)
        row_height = song_widget.get_allocated_height()
        rect = Gdk.Rectangle()
        rect.x = x
        rect.y = y0 + 0.5 * row_height

        song_context_menu = SongWidgetMenu(
            self._application, song_widget, self._corealbum)
        song_context_menu.props.relative_to = self._list_box
        song_context_menu.props.pointing_to = rect
        song_context_menu.popup()
