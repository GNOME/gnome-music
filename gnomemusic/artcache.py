# Copyright 2020 The GNOME Music developers
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

from gi.repository import Gdk, GdkPixbuf, Gio, GLib, GObject

from gnomemusic.corealbum import CoreAlbum
from gnomemusic.coreartist import CoreArtist
from gnomemusic.coresong import CoreSong
from gnomemusic.defaulticon import DefaultIcon, make_icon_frame
from gnomemusic.musiclogger import MusicLogger
from gnomemusic.utils import ArtSize


class ArtCache(GObject.GObject):
    """Handles retrieval of MediaArt cache art

    Uses signals to indicate success or failure and always returns a
    Cairo.Surface.
    """

    __gtype_name__ = "ArtCache"

    __gsignals__ = {
        "finished": (GObject.SignalFlags.RUN_FIRST, None, (object, ))
    }

    _log = MusicLogger()

    def __init__(self):
        super().__init__()

        self._size = ArtSize.SMALL
        self._scale = 1

        self._coreobject = None
        self._default_icon = None
        self._surface = None

    def start(self, coreobject, size, scale):
        """Start the cache query

        :param coreobject: The object to search art for
        :param ArtSize size: The desired size
        :param int scale: The scaling factor
        """
        self._coreobject = coreobject
        self._scale = scale
        self._size = size

        if isinstance(coreobject, CoreArtist):
            self._default_icon = DefaultIcon().get(
                DefaultIcon.Type.ARTIST, self._size, self._scale)
        elif (isinstance(coreobject, CoreAlbum)
                or isinstance(coreobject, CoreSong)):
            self._default_icon = DefaultIcon().get(
                DefaultIcon.Type.ALBUM, self._size, self._scale)

        thumbnail_uri = coreobject.props.thumbnail
        if thumbnail_uri == "generic":
            self.emit("finished", self._default_icon)
            return

        thumb_file = Gio.File.new_for_uri(thumbnail_uri)
        if thumb_file:
            thumb_file.read_async(
                GLib.PRIORITY_DEFAULT_IDLE, None, self._open_stream, None)
            return

        self.emit("finished", self._default_icon)

    def _open_stream(self, thumb_file, result, arguments):
        try:
            stream = thumb_file.read_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self.emit("finished", self._default_icon)
            return

        GdkPixbuf.Pixbuf.new_from_stream_async(
            stream, None, self._pixbuf_loaded, None)

    def _pixbuf_loaded(self, stream, result, data):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self.emit("finished", self._default_icon)
            return

        stream.close_async(
            GLib.PRIORITY_DEFAULT_IDLE, None, self._close_stream, None)

        surface = Gdk.cairo_surface_create_from_pixbuf(
            pixbuf, self._scale, None)
        if isinstance(self._coreobject, CoreArtist):
            surface = make_icon_frame(
                surface, self._size, self._scale, round_shape=True)
        elif (isinstance(self._coreobject, CoreAlbum)
                or isinstance(self._coreobject, CoreSong)):
            surface = make_icon_frame(surface, self._size, self._scale)

        self._surface = surface

    def _close_stream(self, stream, result, data):
        try:
            stream.close_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))

        self.emit("finished", self._surface)
