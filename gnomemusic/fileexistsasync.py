# Copyright 2021 The GNOME Music developers
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

from gi.repository import GLib, GObject, Gio


class FileExistsAsync(GObject.GObject):
    """Gio.File.file_exists async variant
    """

    __gtype_name__ = "FileExistsAsync"

    __gsignals__ = {
        "finished": (GObject.SignalFlags.RUN_FIRST, None, (bool, ))
    }

    def __init__(self) -> None:
        """Initialize FileExistsAsync
        """
        super().__init__()

    def start(self, thumb_file: Gio.File) -> None:
        """Start async file_exists lookup

        :param Gio.File thumb_file: File to check
        """
        thumb_file.query_info_async(
            Gio.FILE_ATTRIBUTE_STANDARD_TYPE, Gio.FileQueryInfoFlags.NONE,
            GLib.PRIORITY_DEFAULT, None, self._on_query_info_finished)

    def _on_query_info_finished(
            self, thumb_file: Gio.File, res: Gio.AsyncResult) -> None:
        exists = True
        try:
            thumb_file.query_info_finish(res)
        except GLib.Error:
            # This indicates that the file has not been created, so
            # there is no art in the MediaArt cache.
            exists = False

        self.emit("finished", exists)
