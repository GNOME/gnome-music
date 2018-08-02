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

from enum import IntEnum

import gi
gi.require_version('Dazzle', '1.0')
from gi.repository import Gdk, GObject, Gtk
from gi.repository.Dazzle import BoldingLabel  # noqa: F401

from gnomemusic import log
from gnomemusic import utils
from gnomemusic.grilo import grilo
from gnomemusic.playlists import Playlists, StaticPlaylists
from gnomemusic.widgets.starimage import StarImage  # noqa: F401

@Gtk.Template(resource_path='/org/gnome/Music/AlbumCover.ui')
class AlbumCover(Gtk.FlowBoxChild):

    __gtype_name__ = 'AlbumCover'

    _stack = Gtk.Template.Child()
    _check = Gtk.Template.Child()
    _title_label = Gtk.Template.Child()
    _artist_label = Gtk.Template.Child()
    _events = Gtk.Template.Child()

    def __repr__(self):
        return '<DiscBox>'

    @log
    def __init__(self, media):
        super().__init__()

        self._media = media
