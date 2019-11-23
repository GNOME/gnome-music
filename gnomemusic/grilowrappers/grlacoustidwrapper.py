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

from __future__ import annotations
from typing import List, Optional
import typing
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application
    from gnomemusic.coregrilo import CoreGrilo
    from gnomemusic.coresong import CoreSong
    from gnomemusic.musiclogger import MusicLogger

import gi
gi.require_version("Grl", "0.3")
from gi.repository import GLib, GObject, Grl


class GrlAcoustIDWrapper(GObject.GObject):
    """Wrapper for the Grilo AcoustID source.

    This source is used by SongEditorDialog to retrieve the tags of a song.
    It defines the publication date as the date of an album release and
    creation date as the first release date of an album.
    For example, an album released for the first time in 2003 and
    published again in 2009 can have 2003 as creation date and 2009 as
    publication date.

    For the SongEditorDialog usage, the creation date needs to be retrieved
    but Music only deals with publication date. That's why, the
    creation_date is converted to publication_date in the callback of the
    query operation.
    """

    _ACOUSTID_METADATA_KEYS: List[int] = [
        Grl.METADATA_KEY_ALBUM,
        Grl.METADATA_KEY_ALBUM_ARTIST,
        Grl.METADATA_KEY_ALBUM_DISC_NUMBER,
        Grl.METADATA_KEY_ARTIST,
        Grl.METADATA_KEY_CREATION_DATE,
        Grl.METADATA_KEY_MB_ARTIST_ID,
        Grl.METADATA_KEY_MB_RECORDING_ID,
        Grl.METADATA_KEY_MB_RELEASE_GROUP_ID,
        Grl.METADATA_KEY_MB_RELEASE_ID,
        Grl.METADATA_KEY_MB_TRACK_ID,
        Grl.METADATA_KEY_TITLE,
        Grl.METADATA_KEY_TRACK_NUMBER
    ]

    def __init__(self, source: Grl.Source, application: Application) -> None:
        """Initialize the AcoustID wrapper

        :param Grl.Source source: The AcoustID source to wrap
        :param Application application: Application object
        """
        super().__init__()

        self._source: Grl.Source = source
        self._log: MusicLogger = application.props.log

        coregrilo: CoreGrilo = application.props.coregrilo
        registry: Grl.Registry = coregrilo.props.registry
        self._fingerprint_key: int = registry.lookup_metadata_key(
            "chromaprint")

    def get_tags(
            self, coresong: CoreSong,
            callback: CoreGrilo.QUERY_CB_TYPE) -> None:
        """Retrieve Musicbrainz tag set for the given song

        :param CoreSong coresong: The song to retrieve tags for
        :param callback: Metadata retrieval callback
        """
        options: Grl.OperationOptions = Grl.OperationOptions()
        options.set_resolution_flags(Grl.ResolutionFlags.NORMAL)

        query: str = "duration={}&fingerprint={}".format(
            str(coresong.props.media.get_duration()),
            coresong.props.media.get_string(self._fingerprint_key))

        def _acoustid_queried(
                source: Grl.Source, op_id: int, media: Optional[Grl.Media],
                count: int, callback: CoreGrilo.QUERY_CB_TYPE,
                error: Optional[GLib.Error]) -> None:
            if error:
                self._log.warning(
                    "Error {}: {}".format(error.domain, error.message))
                callback(None, 0)
                return

            if (media is not None
                    and media.get_creation_date() is not None):
                media.set_publication_date(media.get_creation_date())

            callback(media, count)

        self._source.query(
            query, self._ACOUSTID_METADATA_KEYS, options, _acoustid_queried,
            callback)
