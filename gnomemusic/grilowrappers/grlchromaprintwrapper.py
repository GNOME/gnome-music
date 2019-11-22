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
gi.require_version("Grl", "0.3")
from gi.repository import Grl, GObject


class GrlChromaprintWrapper(GObject.GObject):
    """Wrapper for the Grilo Chromaprint source.
    """

    _acoustid_api_key = "Nb8SVVtH1C"

    _ACOUSTID_METADATA_KEYS = [
        Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_ALBUM_DISC_NUMBER,
        Grl.METADATA_KEY_ARTIST,
        Grl.METADATA_KEY_CREATION_DATE,
        Grl.METADATA_KEY_MB_ARTIST_ID,
        Grl.METADATA_KEY_MB_RECORDING_ID,
        Grl.METADATA_KEY_MB_RELEASE_GROUP_ID,
        Grl.METADATA_KEY_MB_RELEASE_ID,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_TRACK_NUMBER
    ]

    def __init__(self, source, grilo):
        """Initialize the Chromaprint wrapper

        :param Grl.TrackerSource source: The Tracker source to wrap
        :param CoreGrilo grilo: The CoreGrilo instance
        """
        super().__init__()

        self._source = source
        self._grilo = grilo

        self._fingerprint_key = self._grilo._registry.lookup_metadata_key(
            "chromaprint")

        self._METADATA_KEYS = [
            self._fingerprint_key,
            Grl.METADATA_KEY_DURATION
        ]

    def get_chromaprint(self, coresong, callback):
        """Retrieve Chromaprint value

        :param CoreSong coresong: The song to chromaprint
        :param callback: Metadata retrieval callback
        """
        if self._fingerprint_key == Grl.METADATA_KEY_INVALID:
            callback(None)
            return

        chromaprint = coresong.props.media.get_string(self._fingerprint_key)
        if chromaprint is not None:
            callback(media)
            return

        options = Grl.OperationOptions()
        options.set_resolution_flags(
            Grl.ResolutionFlags.FAST_ONLY
            | Grl.ResolutionFlags.IDLE_RELAY)

        def chromaprint_resolved(source, op_id, media, callback, error):
            if error:
                print("Error {}: {}".format(error.domain, error.message))
                callback(None)
                return

            callback(media)

        self._source.resolve(
            coresong.props.media, self._METADATA_KEYS, options,
            chromaprint_resolved, callback)
