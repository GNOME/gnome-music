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

from __future__ import annotations
import typing

from gi.repository import GObject, Gtk, Handy

from gnomemusic.widgets.albumwidget import AlbumWidget
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.coreartist import CoreArtist


@Gtk.Template(resource_path="/org/gnome/Music/ui/ArtistAlbumsWidget.ui")
class ArtistAlbumsWidget(Handy.Clamp):
    """Widget containing all albums by an artist

    A vertical list of AlbumWidget, containing all the albums
    by one artist. Contains the model for all the song widgets of
    the album(s).
    """

    __gtype_name__ = 'ArtistAlbumsWidget'

    _listbox = Gtk.Template.Child()

    selection_mode = GObject.Property(type=bool, default=False)

    def __init__(
            self, coreartist: CoreArtist, application: Application) -> None:
        """Initialize the ArtistAlbumsWidget

        :param CoreArtist coreartist: The CoreArtist object
        :param Aplication application: The Application object
        """
        super().__init__()

        self._application = application
        self._artist = coreartist
        self._model = coreartist.props.model
        self._player = self._application.props.player

        self._listbox.bind_model(self._model, self._add_album)

    def _add_album(self, corealbum):
        row = Gtk.ListBoxRow()
        row.props.selectable = False
        row.props.activatable = False
        row.props.can_focus = False

        widget = AlbumWidget(self._application)
        widget.props.corealbum = corealbum
        widget.props.active_coreobject = self._artist
        widget.props.show_artist_label = False

        self._artist.bind_property(
            "selected", corealbum, "selected",
            GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            'selection-mode', widget, 'selection-mode',
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        row.add(widget)

        return row

    def select_all(self) -> None:
        """Select all items"""
        for corealbum in self._model:
            corealbum.props.selected = True

    def deselect_all(self) -> None:
        """Deselect all items"""
        for corealbum in self._model:
            corealbum.props.selected = False

    @GObject.Property(type=str, flags=GObject.ParamFlags.READABLE)
    def artist(self) -> str:
        """Artist name"""
        return self._artist.props.artist
