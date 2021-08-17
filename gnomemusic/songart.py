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

import gi
gi.require_version("MediaArt", "2.0")
from gi.repository import GObject, MediaArt

from gnomemusic.asyncqueue import AsyncQueue
from gnomemusic.embeddedart import EmbeddedArt
from gnomemusic.fileexistsasync import FileExistsAsync


class SongArt(GObject.GObject):
    """SongArt retrieval object
    """

    _async_queue = AsyncQueue("SongArt")

    def __init__(self, application, coresong):
        """Initialize SongArt

        :param Application application: The application object
        :param CoreSong coresong: The coresong to use
        """
        super().__init__()

        self._coresong = coresong
        self._coregrilo = application.props.coregrilo
        self._album = self._coresong.props.album
        self._artist = self._coresong.props.artist

        self._in_cache()

    def _on_embedded_art_found(self, embeddedart, found):
        if found:
            self._in_cache()
        else:
            self._coregrilo.get_song_art(self._coresong)

    def _in_cache(self):
        success, thumb_file = MediaArt.get_file(
            self._artist, self._album, "album")
        if not success:
            self._coresong.props.thumbnail = "generic"
            return

        def on_file_exists_async_finished(obj, result):
            if result:
                self._coresong.props.thumbnail = thumb_file.get_uri()
            else:
                embedded = EmbeddedArt()
                embedded.connect("art-found", self._on_embedded_art_found)
                embedded.query(self._coresong, self._album)

        file_exists_async = FileExistsAsync()
        file_exists_async.connect(
            "finished", on_file_exists_async_finished)
        self._async_queue.queue(file_exists_async, thumb_file)
