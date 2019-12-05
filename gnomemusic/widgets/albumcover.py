# Copyright 2018 The GNOME Music developers
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

import gi
gi.require_version('Grl', '0.3')
from gi.repository import GObject, Gtk

from gnomemusic.albumartcache import Art
from gnomemusic.corealbum import CoreAlbum
from gnomemusic.widgets.twolinetip import TwoLineTip


@Gtk.Template(resource_path='/org/gnome/Music/ui/AlbumCover.ui')
class AlbumCover(Gtk.FlowBoxChild):
    """Cover tile as used in AlbumsView

    Includes cover, album title, artist & selection mode checkmark.
    """

    __gtype_name__ = 'AlbumCover'

    _cover_stack = Gtk.Template.Child()
    _check = Gtk.Template.Child()
    _title_label = Gtk.Template.Child()
    _artist_label = Gtk.Template.Child()

    selected = GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READWRITE)
    selection_mode = GObject.Property(
        type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, corealbum):
        """Initialize the AlbumCover

        :param Grl.Media media: The media object to use
        """
        super().__init__()

        self._corealbum = corealbum
        self._retrieved = False

        self._tooltip = TwoLineTip()

        artist = self._corealbum.props.artist
        title = self._corealbum.props.title

        self._tooltip.props.title = artist
        self._tooltip.props.subtitle = title

        self._artist_label.props.label = artist
        self._title_label.props.label = title

        self.bind_property(
            'selected', self._check, 'active',
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            'selection-mode', self._check, 'visible',
            GObject.BindingFlags.BIDIRECTIONAL)

        self.connect('query-tooltip', self._on_tooltip_query)

        self._cover_stack.props.size = Art.Size.MEDIUM

        self.show()

    def retrieve(self):
        """Start retrieving the actual album cover

        Cover retrieval is an expensive operation, so use this call to
        start the retrieval process when needed.
        """
        if self._retrieved:
            return

        self._retrieved = True
        self._cover_stack.update(self._corealbum)

    @GObject.Property(type=CoreAlbum, flags=GObject.ParamFlags.READABLE)
    def corealbum(self):
        """CoreAlbum object used in AlbumCover

        :returns: The album used
        :rtype: CoreAlbum
        """
        return self._corealbum

    @Gtk.Template.Callback()
    def _on_tooltip_query(self, widget, x, y, kb, tooltip, data=None):
        tooltip.set_custom(self._tooltip)

        return True
