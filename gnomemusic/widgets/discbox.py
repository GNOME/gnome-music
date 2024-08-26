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

    _list_box = Gtk.Template.Child()

    __gsignals__ = {
        'song-activated': (GObject.SignalFlags.RUN_FIRST, None, (Gtk.Widget,))
    }

    disc_nr = GObject.Property(type=int, default=1)

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

        self._coredisc.bind_property(
            "disc-nr", self, "disc-nr",
            GObject.BindingFlags.SYNC_CREATE)

        self._list_box.bind_model(self._model, self._create_widget)

    def _create_widget(self, coresong):
        song_widget = SongWidget(coresong)
        song_widget.props.menu = SongWidgetMenu(
            self._application, song_widget, self._corealbum)

        return song_widget

    @Gtk.Template.Callback()
    def _song_activated(
            self, list_box: Gtk.ListBox, song_widget: SongWidget) -> bool:
        self.emit("song-activated", song_widget)

        return Gdk.EVENT_STOP
