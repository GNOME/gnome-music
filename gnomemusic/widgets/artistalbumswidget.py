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
from typing import Optional
import typing

from gi.repository import GObject, Gtk

from gnomemusic.coreartist import CoreArtist
from gnomemusic.widgets.albumwidget import AlbumWidget
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


@Gtk.Template(resource_path="/org/gnome/Music/ui/ArtistAlbumsWidget.ui")
class ArtistAlbumsWidget(Gtk.Box):
    """Widget containing all albums by an artist

    A vertical list of AlbumWidget, containing all the albums
    by one artist. Contains the model for all the song widgets of
    the album(s).
    """

    __gtype_name__ = 'ArtistAlbumsWidget'

    _listbox = Gtk.Template.Child()

    def __init__(self, application: Application) -> None:
        """Initialize the ArtistAlbumsWidget

        :param Aplication application: The Application object
        """
        super().__init__()

        self._application = application
        self._coreartist: Optional[CoreArtist] = None

    def _update_model(self) -> None:
        if self._coreartist is not None:
            self._listbox.bind_model(
                self._coreartist.props.model, self._add_album)

    def _add_album(self, corealbum):
        row = Gtk.ListBoxRow()
        row.props.selectable = False
        row.props.activatable = False
        row.props.focusable = False

        widget = AlbumWidget(self._application)
        widget.props.corealbum = corealbum
        widget.props.active_coreobject = self._coreartist
        widget.props.show_artist_label = False

        row.set_child(widget)

        return row

    @GObject.Property(
        type=CoreArtist, flags=GObject.ParamFlags.READWRITE, default=None)
    def coreartist(self) -> CoreArtist:
        """Current CoreArtist object

        :param CoreArtist coreartist: The CoreArtist object
        :rtype: CoreArtist
        """
        return self._coreartist

    @coreartist.setter  # type: ignore
    def coreartist(self, coreartist: CoreArtist) -> None:
        """Sets the CoreArtist for the widget

        :param CoreArtist coreartist: The CoreArtist to use
        """
        if self._coreartist is not coreartist:
            self._coreartist = coreartist

            self._update_model()
