# Copyright 2019 The GNOME Music developers
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


class ArtistArt(GObject.GObject):
    """Artist art retrieval object
    """

    def __init__(self, application, coreartist):
        """Initialize.

        :param Application application: The application object
        :param CoreArtist coreartist: The coreartist to use
        """
        super().__init__()

        self._coreartist = coreartist
        self._artist = self._coreartist.props.artist

        if self._in_cache():
            return

        application.props.coregrilo.get_artist_art(self._coreartist)

    def _in_cache(self):
        success, thumb_file = MediaArt.get_file(
            self._artist, None, "artist")
        if (not success
                or not thumb_file.query_exists()):
            self._coreartist.props.thumbnail = "loading"
            return False

        self._coreartist.props.thumbnail = thumb_file.get_uri()

        return True
