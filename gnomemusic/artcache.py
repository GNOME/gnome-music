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

from gi.repository import Gdk, GdkPixbuf, Gio, Gtk, GLib, GObject

from gnomemusic.coreartist import CoreArtist
from gnomemusic.coverpaintable import CoverPaintable
from gnomemusic.defaulticon import DefaultIcon
from gnomemusic.musiclogger import MusicLogger
from gnomemusic.utils import ArtSize, DefaultIconType


class ArtCache(GObject.GObject):
    """Handles retrieval of MediaArt cache art

    Uses signals to indicate success or failure and always returns a
    CoverPaintable.
    """

    __gtype_name__ = "ArtCache"

    __gsignals__ = {
        "finished": (GObject.SignalFlags.RUN_FIRST, None, (object, ))
    }

    _log = MusicLogger()

    def __init__(self, widget: Gtk.Widget) -> None:
        """Intialize ArtCache

        :param Gtk.Widget widget: The widget of this cache
        """
        super().__init__()

        self._size = ArtSize.SMALL
        self._widget = widget

        self._coreobject = None
        self._icon_type = DefaultIconType.ALBUM
        self._paintable = None

    def start(self, coreobject, size):
        """Start the cache query

        :param coreobject: The object to search art for
        :param ArtSize size: The desired size
        """
        self._coreobject = coreobject
        self._size = size

        if isinstance(coreobject, CoreArtist):
            self._icon_type = DefaultIconType.ARTIST

        self._paintable = DefaultIcon(self._widget).get(
            self._icon_type, self._size)

        thumbnail_uri = coreobject.props.thumbnail
        if thumbnail_uri == "generic":
            self.emit("finished", self._paintable)
            return

        thumb_file = Gio.File.new_for_uri(thumbnail_uri)
        if thumb_file:
            thumb_file.read_async(
                GLib.PRIORITY_DEFAULT_IDLE, None, self._open_stream, None)
            return

        self.emit("finished", self._paintable)

    def _open_stream(self, thumb_file, result, arguments):
        try:
            stream = thumb_file.read_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self.emit("finished", self._paintable)
            return

        GdkPixbuf.Pixbuf.new_from_stream_async(
            stream, None, self._pixbuf_loaded, None)

    def _pixbuf_loaded(self, stream, result, data):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))
            self.emit("finished", self._paintable)
            return

        texture = Gdk.Texture.new_for_pixbuf(pixbuf)
        if texture:
            self._paintable = CoverPaintable(
                self._size, self._widget, icon_type=self._icon_type,
                texture=texture)

        stream.close_async(
            GLib.PRIORITY_DEFAULT_IDLE, None, self._close_stream, None)

    def _close_stream(self, stream, result, data):
        try:
            stream.close_finish(result)
        except GLib.Error as error:
            self._log.warning(
                "Error: {}, {}".format(error.domain, error.message))

        self.emit("finished", self._paintable)
